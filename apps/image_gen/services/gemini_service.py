import io
import base64
from django.conf import settings
import google.generativeai as genai


class GeminiImageEditService:
    """
    Image editing service using Google Gemini API.
    Handles photo edits based on user prompts.
    """

    # Available models - use the latest stable version
    AVAILABLE_MODELS = [
        "gemini-2.0-flash",  # Latest Flash model
        "gemini-1.5-pro",    # Fallback to Pro
        "gemini-pro",        # Older version
    ]

    def __init__(self):
        """Initialize Gemini API with API key from settings."""
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured in settings")
        genai.configure(api_key=api_key)

    @staticmethod
    def _ensure_image_bytes(image_file):
        """Convert Django file or bytes to bytes."""
        if hasattr(image_file, "read"):
            return image_file.read()
        if isinstance(image_file, bytes):
            return image_file
        raise ValueError("Invalid image format")

    @staticmethod
    def _image_to_base64(image_bytes):
        """Convert image bytes to base64 string."""
        return base64.standard_b64encode(image_bytes).decode("utf-8")

    @classmethod
    def list_available_models(cls):
        """List all available Gemini models (for debugging)."""
        instance = cls()
        try:
            models = genai.list_models()
            model_names = [m.name for m in models if "generateContent" in m.supported_generation_methods]
            return model_names
        except Exception as e:
            print(f"Error listing models: {str(e)}")
            return cls.AVAILABLE_MODELS

    @classmethod
    def _get_available_model(cls):
        """Get the first available model from the list."""
        instance = cls()
        try:
            available = cls.list_available_models()
            for model in cls.AVAILABLE_MODELS:
                if model in available:
                    return model
        except Exception:
            pass
        # Default to latest
        return cls.AVAILABLE_MODELS[0]

    @classmethod
    def edit_image(cls, source_image, prompt, style=""):
        """
        Edit an image using Gemini based on text prompt.

        Args:
            source_image: Django ImageField or file-like object
            prompt: Edit instructions (e.g., "add black sunglasses on her eyes")
            style: Optional style description (e.g., "realistic, photorealistic")

        Returns:
            bytes: Edited image in PNG format

        Raises:
            ValueError: If image processing fails
            Exception: If Gemini API call fails
        """
        instance = cls()

        # Get image bytes
        image_bytes = cls._ensure_image_bytes(source_image)
        image_b64 = cls._image_to_base64(image_bytes)

        # Build the edit instruction
        full_instruction = prompt
        if style:
            full_instruction = f"{prompt}. Style: {style}"

        # Add identity preservation directive
        full_instruction += (
            "\n\nIMPORTANT: Keep the same person, same background, and same overall composition. "
            "Only apply the specific edit requested. Do NOT change the person's identity or facial features beyond what's requested."
        )

        try:
            # Get the available model
            model_name = cls._get_available_model()
            model = genai.GenerativeModel(model_name)

            # Prepare image part with mime type
            image_part = {
                "mime_type": "image/jpeg",
                "data": image_b64,
            }

            # Send request to Gemini
            response = model.generate_content(
                [
                    image_part,
                    f"Edit this image according to these instructions: {full_instruction}\n\nReturn ONLY the edited image. Do not include any text in the response.",
                ]
            )

            # Extract image from response
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # Check if part contains image data
                        if hasattr(part, "inline_data") and part.inline_data:
                            return part.inline_data.data
                        # Fallback: check for blob data
                        if hasattr(part, "data"):
                            return part.data

            raise ValueError(
                "Gemini API did not return an image in the response. "
                "The model may have rejected the edit request."
            )

        except ValueError as e:
            raise ValueError(f"Image edit failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    @classmethod
    def edit_image_vision_only(cls, source_image, prompt, style=""):
        """
        Alternative implementation using Gemini's vision capabilities.
        Analyzes image and returns edit instructions as structured output.
        (Falls back to original image if actual image editing isn't available)

        Args:
            source_image: Django ImageField or file-like object
            prompt: Edit instructions
            style: Optional style description

        Returns:
            bytes: Original image (as Gemini may not support direct image editing in all tiers)
        """
        instance = cls()

        # Get image bytes
        image_bytes = cls._ensure_image_bytes(source_image)
        image_b64 = cls._image_to_base64(image_bytes)

        try:
            # Initialize model
            model = genai.GenerativeModel("gemini-1.5-flash")

            # Prepare image part
            image_part = {
                "mime_type": "image/jpeg",
                "data": image_b64,
            }

            # Send vision analysis request
            response = model.generate_content(
                [
                    image_part,
                    f"Analyze this image and confirm you can apply this edit: {prompt}. "
                    f"If style is specified: {style}. Return 'CONFIRMED' if you can edit it.",
                ]
            )

            # Log the analysis result
            if response.text:
                print(f"Gemini analysis: {response.text}")

            # Return original image as fallback
            return image_bytes

        except Exception as e:
            print(f"Gemini vision analysis error: {str(e)}")
            # Return original on error
            return image_bytes
