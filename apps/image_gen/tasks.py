from django.core.files.base import ContentFile

from apps.image_gen.agents.metadata_agent import MetadataAgent
from apps.image_gen.models import GeneratedImage, ImageGenerationJob
from apps.image_gen.services.stability_service import StabilityService


def process_image_generation_job(job_id, model="core", upscale_uploaded=False, search_prompt=""):
    """
    Process an image generation job.
    
    Supports both modes:
    - Text-to-Image: Generate new image from prompt
    - Image-to-Image (Edit): Transform/edit an image based on prompt + source_image
    
    The source_image (if provided) is preserved in the GeneratedImage.source_image field.
    The result (new or edited image) is stored in GeneratedImage.image field.
    """
    job = ImageGenerationJob.objects.select_related("user", "size").get(id=job_id)
    job.status = ImageGenerationJob.Status.PROCESSING
    job.save(update_fields=["status", "updated_at"])

    try:
        # Slightly higher edit strength avoids no-op outputs while still preserving identity.
        strength = 0.24 if job.source_image else None
        
        image_bytes = StabilityService.generate(
            prompt=job.prompt,
            size=job.size.size,
            source_image=job.source_image,  # If provided, only minimal edits applied
            safety_enabled=False,
            strength=strength,
            model=model,
            search_prompt=search_prompt,
        )

        if job.source_image and upscale_uploaded:
            image_bytes = StabilityService.upscale(image_bytes)

        generated_image = GeneratedImage.objects.create(
            user=job.user,
            prompt=job.prompt,
            user_prompt=job.user_prompt,
            style=job.style,
            size=job.size,
            source_image=job.source_image,  # Original image is preserved here
            image=ContentFile(image_bytes, name=f"generated_{job.id}.png"),  # Result is here
        )

        metadata = MetadataAgent.build(job.prompt)
        generated_image.title = metadata["title"]
        generated_image.tags = metadata["tags"]
        generated_image.description = metadata["description"]
        generated_image.save(update_fields=["title", "tags", "description", "updated_at"])

        job.generated_image = generated_image
        job.status = ImageGenerationJob.Status.SUCCEEDED
        job.error_message = ""
        job.save(update_fields=["generated_image", "status", "error_message", "updated_at"])
    except Exception as exc:
        job.status = ImageGenerationJob.Status.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise
