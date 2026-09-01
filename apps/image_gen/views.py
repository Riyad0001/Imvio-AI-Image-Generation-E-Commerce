from collections import defaultdict
import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.core.models import CreditTransaction
from apps.core.services.credits import deduct_credits, get_or_create_wallet
from apps.image_gen.agents.image_generation_agent import ImageGenerationAgent
from apps.image_gen.models import GeneratedImage, ImageGenerationJob, ImageSize, ImageCreditSettings, ImageStyle
from apps.image_gen.serializers import (
    GenerateImageRequestSerializer,
    GenerationJobSerializer,
    GeneratedImageSerializer,
    ImageSizeSerializer,
    ImageStyleSerializer,
    RegenerateImageRequestSerializer,
    SaveCreationSerializer,
)
from apps.image_gen.services.stability_service import ContentModerationError
from apps.image_gen.services.openai_image_service import OpenAIImageEditService
from django.core.files.base import ContentFile


def get_default_size():
    default_size, _ = ImageSize.objects.get_or_create(size="1:1")
    return default_size


class GenerateImageAPIView(APIView):
    """
    Generate new images or edit existing ones.
    
    POST /api/v1/images/generate/
    
    Request body:
    {
        "prompt": "description or edit instructions",
        "style_id": 1,                             # optional, ID from /api/v1/images/styles/
        "size_id": 1,                              # optional, defaults to 1:1
        "source_image": <image file>               # optional - for editing existing images
    }
    
    Modes:
    - Text-to-Image: Send prompt only → generates new image from text
    - Image-to-Image (Edit): Send prompt + source_image → transforms/edits the image
    
    The original image (if provided) is always preserved in response.source_image_url
    The result is persisted in response.image_url
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerateImageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        prompt = (validated.get("prompt") or "").strip()
        style_obj = validated.get("style")  # This is now an ImageStyle instance or None
        style = style_obj.style_text if style_obj else ""

        # Style is first priority; prompt is supplementary. At least one must be provided.
        if not prompt and not style:
            return Response(
                {
                    "status": False,
                    "message": "Either a style or a prompt must be provided",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        source_image = validated.get("source_image")
        search_prompt = (validated.get("search_prompt") or "").strip()
        credit_settings = ImageCreditSettings.get_solo()
        generation_credit_cost = credit_settings.generation_credit_cost
        
        # For image editing, use default size (size doesn't matter for edits, only for generation)
        # For text-to-image generation, use user-provided or default size
        if source_image:
            size = get_default_size()  # Use default for edits
        else:
            size = validated.get("size") or get_default_size()  # Use user's or default for generation
        
        # Route to OpenAI gpt-image-2 for image editing (when photo is uploaded)
        if source_image:
            try:
                composed_prompt = ImageGenerationAgent._compose_prompt(
                    prompt=prompt,
                    style=style,
                    source_image=True,
                    preserve_identity=True,
                )

                openai_service = OpenAIImageEditService()
                edited_image_bytes = openai_service.edit_image(
                    source_image=source_image,
                    prompt=composed_prompt,
                    style="",
                )
                
                # Create job record with size and style
                job = ImageGenerationJob.objects.create(
                    user=request.user,
                    prompt=composed_prompt,
                    style=style,
                    size=size,
                    status=ImageGenerationJob.Status.SUCCEEDED,
                )
                
                # Save edited image (don't pass 'job' - relationship is on the job)
                image_file_name = f"edited_{job.id}.png"
                generated_image = GeneratedImage.objects.create(
                    user=request.user,
                    prompt=composed_prompt,
                    user_prompt=prompt,
                    style=style,
                    size=size,
                    source_image=source_image,
                    image=ContentFile(edited_image_bytes, name=image_file_name),
                    title=f"Edited Image - {prompt[:50]}",
                )
                
                job.generated_image = generated_image
                job.save()
                
                # Deduct credits
                deduct_credits(
                    user=request.user,
                    amount=generation_credit_cost,
                    source=CreditTransaction.Source.IMAGE_GENERATION,
                    reference=f"edit_openai:{job.prompt[:30]}",
                    metadata={
                        "size_id": size.id,
                        "size": size.size,
                        "style": style,
                        "job_id": job.id,
                        "model": "gpt-image-2",
                        "credit_cost": generation_credit_cost,
                    },
                )
                
                return Response(
                    {
                        "status": True,
                        "message": "Image edited successfully",
                        "data": GeneratedImageSerializer(generated_image, context={"request": request}).data,
                    },
                    status=status.HTTP_200_OK,
                )
                
            except Exception as e:
                return Response(
                    {
                        "status": False,
                        "message": f"Image edit failed: {str(e)}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        
        # Route to Stability for text-to-image generation (when no photo uploaded)
        # Use 'core' model for fastest output time
        selected_model = "core"
        
        try:
            job = ImageGenerationAgent.execute(
                user=request.user,
                prompt=prompt,
                style=style,
                size=size,
                source_image=None,
                deduct_on_success=False,
                credit_cost=generation_credit_cost,
                model=selected_model,
                upscale_uploaded=False,
                search_prompt=search_prompt,
                user_prompt=prompt,
            )
        except ContentModerationError as e:
            # Content flagged by moderation - no credits charged by API
            return Response(
                {
                    "status": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as e:
            return Response(
                {
                    "status": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generation now runs synchronously; refresh job to return final result in one call.
        job.refresh_from_db()

        if job.status == ImageGenerationJob.Status.SUCCEEDED and job.generated_image:
            # Deduct credits only on successful generation
            deduct_credits(
                user=request.user,
                amount=generation_credit_cost,
                source=CreditTransaction.Source.IMAGE_GENERATION,
                reference=f"generation:{job.prompt[:30]}",
                metadata={"size_id": size.id, "size": size.size, "style": style, "job_id": job.id, "credit_cost": generation_credit_cost, "model": selected_model, "upscaled": False},
            )
            return Response(
                {
                    "status": True,
                    "message": "Image generated successfully",
                    "data": GeneratedImageSerializer(job.generated_image, context={"request": request}).data,
                },
                status=status.HTTP_200_OK,
            )

        if job.status == ImageGenerationJob.Status.FAILED:
            return Response(
                {
                    "status": False,
                    "message": job.error_message or "Image generation failed",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "status": True,
                "message": "Image generation is processing",
                "data": GenerationJobSerializer(job, context={"request": request}).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class GenerationJobDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_object_or_404(ImageGenerationJob, id=job_id, user=request.user)
        return Response(
            {
                "status": True,
                "message": "Generation job fetched successfully",
                "data": GenerationJobSerializer(job, context={"request": request}).data,
            }
        )


class ImageHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        images = GeneratedImage.objects.filter(user=request.user, is_deleted=False).order_by("-created_at")
        grouped = defaultdict(list)

        for image in images:
            key = timezone.localtime(image.created_at).date().isoformat()
            grouped[key].append(GeneratedImageSerializer(image, context={"request": request}).data)

        return Response(
            {
                "status": True,
                "message": "Image history fetched successfully",
                "data": grouped,
            }
        )


class ImageDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, image_id):
        image = get_object_or_404(GeneratedImage, id=image_id, user=request.user, is_deleted=False)
        return Response(
            {
                "status": True,
                "message": "Image detail fetched successfully",
                "data": GeneratedImageSerializer(image, context={"request": request}).data,
            }
        )

    def delete(self, request, image_id):
        image = get_object_or_404(GeneratedImage, id=image_id, user=request.user, is_deleted=False)
        image.is_deleted = True
        image.deleted_at = timezone.now()
        image.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
        return Response({"status": True, "message": "Image deleted successfully"})


class SaveCreationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SaveCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_id = serializer.validated_data.get("image_id")
        if image_id:
            image = get_object_or_404(
                GeneratedImage,
                id=image_id,
                user=request.user,
                is_deleted=False,
            )
            image.custom_name = serializer.validated_data["resolved_name"]
            image.is_saved_creation = True
            image.save(update_fields=["custom_name", "is_saved_creation", "updated_at"])
        else:
            size = serializer.validated_data.get("size") or get_default_size()
            image = GeneratedImage.objects.create(
                user=request.user,
                prompt=serializer.validated_data.get("prompt", ""),
                style=serializer.validated_data.get("style", ""),
                size=size,
                image=serializer.validated_data["image"],
                custom_name=serializer.validated_data["resolved_name"],
                is_saved_creation=True,
            )

        return Response(
            {
                "status": True,
                "message": "Creation saved successfully",
                "data": GeneratedImageSerializer(image, context={"request": request}).data,
            }
        )


class CreationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filter_type = request.query_params.get("filter", "all")
        queryset = GeneratedImage.objects.filter(user=request.user,is_saved_creation=True, is_deleted=False).order_by("-created_at")

        if filter_type == "recent":
            queryset = queryset.filter(is_saved_creation=False)
        elif filter_type == "saved":
            queryset = queryset.filter(is_saved_creation=True)

        serializer = GeneratedImageSerializer(queryset, many=True, context={"request": request})
        return Response(
            {
                "status": True,
                "message": "Creations fetched successfully",
                "data": serializer.data,
            }
        )


class RegenerateImageAPIView(APIView):
    """
    Regenerate an image based on an existing generated image using a new prompt and/or style.

    POST /api/v1/images/{image_id}/regenerate/

    Request body:
    {
        "prompt": "edit instructions",   # optional if style_id is provided
        "style_id": 2                     # optional — falls back to the existing image's style
    }

    Priority: Style is first. Prompt is supplementary.
    At least one of prompt or style (new or existing) must produce content.
    Takes the existing image as source, applies edits via OpenAI gpt-image-2,
    and updates the image in-place. The original source image is always preserved.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, image_id):
        existing = get_object_or_404(GeneratedImage, id=image_id, user=request.user, is_deleted=False)
        serializer = RegenerateImageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        prompt = (validated.get("prompt") or "").strip()

        if not existing.image:
            return Response(
                {
                    "status": False,
                    "message": "Image file not found for regeneration",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Style is first priority; prompt is supplementary. Resolve style from request or existing image.
        style_obj = validated.get("style")  # ImageStyle instance or None
        if style_obj is not None:
            style = style_obj.style_text
        else:
            style = existing.style or ""

        # At least one of prompt or style must produce content
        if not prompt and not style:
            return Response(
                {
                    "status": False,
                    "message": "Either a prompt or a style must be provided",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        size = existing.size or get_default_size()
        credit_settings = ImageCreditSettings.get_solo()
        regeneration_credit_cost = credit_settings.regeneration_credit_cost

        try:
            # Open the existing image file so the service can read its bytes
            source_file = existing.image.open("rb")

            composed_prompt = ImageGenerationAgent._compose_prompt(
                prompt=prompt,
                style=style,
                source_image=True,
                preserve_identity=True,
            )

            openai_service = OpenAIImageEditService()
            regenerated_image_bytes = openai_service.edit_image(
                source_image=source_file,
                prompt=composed_prompt,
                style="",
            )

            # Create job record
            job = ImageGenerationJob.objects.create(
                user=request.user,
                prompt=composed_prompt,
                style=style,
                size=size,
                status=ImageGenerationJob.Status.SUCCEEDED,
            )

            # Replace the existing image in-place (old image destroyed)
            existing.prompt = composed_prompt
            existing.user_prompt = prompt
            existing.style = style
            existing.size = size
            existing.image = ContentFile(regenerated_image_bytes, name=f"regenerated_{existing.id}_{job.id}.png")
            existing.title = f"Regenerated Image - {prompt[:50]}"
            existing.save(
                update_fields=[
                    "prompt",
                    "user_prompt",
                    "style",
                    "size",
                    "image",
                    "title",
                    "updated_at",
                ]
            )

            job.generated_image = existing
            job.save(update_fields=["generated_image", "updated_at"])

            # Deduct credits
            deduct_credits(
                user=request.user,
                amount=regeneration_credit_cost,
                source=CreditTransaction.Source.IMAGE_GENERATION,
                reference=f"regeneration_openai:{job.prompt[:30]}",
                metadata={
                    "image_id": existing.id,
                    "size_id": size.id,
                    "size": size.size,
                    "style": style,
                    "job_id": job.id,
                    "model": "gpt-image-2",
                    "credit_cost": regeneration_credit_cost,
                },
            )

            return Response(
                {
                    "status": True,
                    "message": "Image regenerated successfully",
                    "data": GeneratedImageSerializer(existing, context={"request": request}).data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": f"Image regeneration failed: {str(e)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class SharedImageAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, image_id, share_id):
        image = get_object_or_404(GeneratedImage, id=image_id, share_id=share_id, is_deleted=False)
        return Response(
            {
                "status": True,
                "message": "Shared image fetched successfully",
                "data": GeneratedImageSerializer(image, context={"request": request}).data,
            }
        )


class ImageDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, image_id):
        image = get_object_or_404(GeneratedImage, id=image_id, user=request.user, is_deleted=False)
        if not image.image:
            raise Http404("Image file not found")

        credit_settings = ImageCreditSettings.get_solo()
        download_credit_cost = credit_settings.download_credit_cost
        wallet = get_or_create_wallet(request.user)

        # Check if user has enough credits in wallet
        if wallet.balance < download_credit_cost:
            return Response(
                {
                    "status": False,
                    "message": f"Insufficient credits. You need {download_credit_cost} credits to download this image.",
                    "required_credits": download_credit_cost,
                    "available_credits": wallet.balance,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        # Deduct credits from user account
        try:
            deduct_credits(
                user=request.user,
                amount=download_credit_cost,
                source=CreditTransaction.Source.IMAGE_DOWNLOAD,
                reference=f"download:{image.id}",
                metadata={"image_id": image.id, "image_name": image.custom_name or image.title, "credit_cost": download_credit_cost},
            )
        except ValidationError as e:
            return Response(
                {
                    "status": False,
                    "message": str(e.detail[0]) if hasattr(e, "detail") and e.detail else str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": f"Failed to deduct credits: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = image.custom_name or os.path.basename(image.image.name) or f"image_{image.id}.png"
        if not os.path.splitext(filename)[1]:
            filename = f"{filename}.png"

        return FileResponse(image.image.open("rb"), as_attachment=True, filename=filename)


class ImageSizeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sizes = ImageSize.objects.all().order_by("id")
        return Response(
            {
                "status": True,
                "message": "Image sizes fetched successfully",
                "data": ImageSizeSerializer(sizes, many=True).data,
            }
        )


class ImageStyleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        styles = ImageStyle.objects.filter(is_active=True)
        return Response(
            {
                "status": True,
                "message": "Image styles fetched successfully",
                "data": ImageStyleSerializer(styles, many=True, context={"request": request}).data,
            }
        )


class ImageCreditConfigAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        credit_settings = ImageCreditSettings.get_solo()
        return Response(
            {
                "status": True,
                "message": "Image credit configuration fetched successfully",
                "data": {
                    "generation_credit_cost": credit_settings.generation_credit_cost,
                    "regeneration_credit_cost": credit_settings.regeneration_credit_cost,
                    "download_credit_cost": credit_settings.download_credit_cost,
                },
            },
            status=status.HTTP_200_OK,
        )


class SaveImageAPIView(APIView):
    """
    Save a generated image by marking it as a saved creation.
    
    POST /api/v1/images/{image_id}/save/
    
    Request body:
    {
        "custom_name": "My Favorite Image" (optional)
    }
    
    Saves the generated image and optionally renames it.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, image_id):
        image = get_object_or_404(GeneratedImage, id=image_id, user=request.user, is_deleted=False)
        
        # Get optional custom name from request
        custom_name = request.data.get("custom_name") or request.data.get("name")
        
        # Mark as saved creation
        image.is_saved_creation = True
        if custom_name:
            image.custom_name = custom_name
        image.save(update_fields=["is_saved_creation", "custom_name", "updated_at"])
        
        return Response(
            {
                "status": True,
                "message": "Image saved successfully",
                "data": GeneratedImageSerializer(image, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )
