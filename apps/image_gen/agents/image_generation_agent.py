from apps.core.models import CreditTransaction
from apps.core.services.credits import deduct_credits
from apps.image_gen.models import ImageGenerationJob
from apps.image_gen.tasks import process_image_generation_job


class ImageGenerationAgent:
    CREDIT_COST = 5

    @classmethod
    def _compose_prompt(cls, prompt, style, source_image=False, preserve_identity=True):
        cleaned_prompt = (prompt or "").strip()
        cleaned_style = (style or "").strip()
        if source_image and preserve_identity:
            cleaned_prompt = (
                f"{cleaned_prompt}. Preserve the same person identity, face, hairstyle, skin tone, pose, background, and framing. "
                "Only apply the requested edit in place."
            )
        if not cleaned_style:
            return cleaned_prompt
        # Style is the primary directive; prompt is supplementary context
        return f"{cleaned_style}. {cleaned_prompt}"

    @classmethod
    def execute(
        cls,
        user,
        prompt,
        size,
        style="",
        source_image=None,
        deduct_on_success=False,
        credit_cost=None,
        model="core",
        upscale_uploaded=False,
        search_prompt="",
        user_prompt="",
    ):
        """
        Execute image generation or editing.
        
        Args:
            user: The user making the request
            prompt: The image generation prompt or full scene description for editing
            size: The ImageSize object
            style: The style modifier
            source_image: Optional source image for selective img2img editing
            deduct_on_success: If True, deduct credits after successful generation
            credit_cost: Optional credit cost override for this generation
        
        Returns:
            ImageGenerationJob instance
        """
        preserve_identity = not (bool(source_image) and model == "search-and-replace")
        composed_prompt = cls._compose_prompt(
            prompt,
            style,
            source_image=bool(source_image),
            preserve_identity=preserve_identity,
        )
        resolved_credit_cost = credit_cost if credit_cost is not None else cls.CREDIT_COST

        job = ImageGenerationJob.objects.create(
            user=user,
            prompt=composed_prompt,
            user_prompt=user_prompt or prompt,
            size=size,
            style=style,
            source_image=source_image,
            credit_cost=resolved_credit_cost,
        )
        
        resolved_model = model
        if source_image and model == "core":
            resolved_model = "precision-edit"

        process_image_generation_job(
            job.id,
            model=resolved_model,
            upscale_uploaded=upscale_uploaded,
            search_prompt=search_prompt,
        )
        
        # Only deduct credits if generation succeeded and flag is set
        if deduct_on_success and job.status == ImageGenerationJob.Status.SUCCEEDED:
            deduct_credits(
                user=user,
                amount=resolved_credit_cost,
                source=CreditTransaction.Source.IMAGE_GENERATION,
                reference=f"generation:{composed_prompt[:30]}",
                metadata={"size_id": size.id, "size": size.size, "style": style, "job_id": job.id},
            )
        
        return job
