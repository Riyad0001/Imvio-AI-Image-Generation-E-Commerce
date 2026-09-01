from apps.image_gen.agents.image_generation_agent import ImageGenerationAgent


class RegenerationAgent:
    @staticmethod
    def execute(
        user,
        existing_image,
        prompt=None,
        style=None,
        size=None,
        source_image=None,
        deduct_on_success=False,
        credit_cost=None,
        model="core",
        upscale_uploaded=False,
        search_prompt="",
    ):
        final_prompt = prompt if prompt is not None and prompt != "" else existing_image.prompt
        final_style = style if style is not None else existing_image.style
        final_size = size or existing_image.size
        image_for_generation = source_image or existing_image.source_image
        job = ImageGenerationAgent.execute(
            user=user,
            prompt=final_prompt,
            style=final_style,
            size=final_size,
            source_image=image_for_generation,
            deduct_on_success=deduct_on_success,
            credit_cost=credit_cost,
            model=model,
            upscale_uploaded=upscale_uploaded,
            search_prompt=search_prompt,
        )
        return job
