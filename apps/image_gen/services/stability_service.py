import requests
from django.conf import settings
import mimetypes
import json
import io
from PIL import Image, ImageChops, ImageStat, ImageDraw


STABILITY_API_URLS = {
    "core": "https://api.stability.ai/v2beta/stable-image/generate/core",
    "ultra": "https://api.stability.ai/v2beta/stable-image/generate/ultra",
    "sd3": "https://api.stability.ai/v2beta/stable-image/generate/sd3",
}
STABILITY_UPSCALE_FAST_API_URL = "https://api.stability.ai/v2beta/stable-image/upscale/fast"
STABILITY_EDIT_SEARCH_REPLACE_API_URL = "https://api.stability.ai/v2beta/stable-image/edit/search-and-replace"
STABILITY_EDIT_INPAINT_API_URL = "https://api.stability.ai/v2beta/stable-image/edit/inpaint"
STABILITY_CONTROL_STRUCTURE_API_URL = "https://api.stability.ai/v2beta/stable-image/control/structure"
STABILITY_EDIT_MAX_PIXELS = 9_437_184


class ContentModerationError(Exception):
    """
    Raised when content is flagged by Stability AI's content moderation system.
    No credits are charged by the API when this occurs.
    """
    pass


class StabilityService:
    IDENTITY_NEGATIVE_PROMPT = (
        "different person, different face, changed identity, swapped subject, altered hairstyle, "
        "altered skin tone, changed background, changed camera angle, new person"
    )

    @staticmethod
    def _infer_search_prompt(prompt):
        text = (prompt or "").lower()

        if any(word in text for word in ["sunglass", "glasses", "spectacles", "goggles", "eyewear"]):
            return "eyes"
        if any(word in text for word in ["lipstick", "lips"]):
            return "lips"
        if any(word in text for word in ["hair", "hairstyle", "beard", "mustache", "moustache"]):
            return "hair"
        if any(word in text for word in ["shirt", "dress", "jacket", "hoodie", "clothes", "outfit"]):
            return "clothes"
        if any(word in text for word in ["shoes", "sneakers", "heels", "boots"]):
            return "feet"
        if any(word in text for word in ["background", "sky", "wall", "room", "scene"]):
            return "background"

        return "main subject"

    @staticmethod
    def _normalize_edit_prompt(prompt):
        raw_prompt = (prompt or "").strip()
        marker = ". Preserve the same person identity"
        if marker in raw_prompt:
            raw_prompt = raw_prompt.split(marker, 1)[0].strip()

        if raw_prompt:
            return raw_prompt

        return "Apply only the requested edit while keeping the same person and scene"

    @staticmethod
    def _build_local_mask(image_size, target="main subject", grow=1.0):
        """
        Build a conservative mask focused on a local region to avoid full-image changes.
        White = editable area, black = preserved area.
        Uses generous default sizing to handle various face positions and framing.
        """
        width, height = image_size
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)

        t = (target or "main subject").lower()
        grow = max(0.8, min(1.8, float(grow)))

        if t in {"eyes", "eye", "glasses", "sunglasses", "face"}:
            # More generous eye region (vertical center ±22% to handle various framing)
            eye_center_y = int(height * 0.40)  # Slightly lower from before
            band_h = int(height * 0.22 * grow)  # Increased from 0.14 to 0.22
            left_x = int(width * 0.15)  # Wider left boundary
            right_x = int(width * 0.85)  # Wider right boundary
            draw.rounded_rectangle(
                [left_x, max(0, eye_center_y - band_h // 2), right_x, min(height, eye_center_y + band_h // 2)],
                radius=max(8, int(min(width, height) * 0.03)),
                fill=255,
            )
        elif t in {"lips", "mouth"}:
            cx = width // 2
            cy = int(height * 0.58)
            # Larger lip region
            rx = int(width * 0.22 * grow)  # Increased from 0.15
            ry = int(height * 0.08 * grow)  # Increased from 0.06
            draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
        elif t in {"hair", "hairstyle"}:
            # Larger hair region
            draw.ellipse(
                [
                    int(width * 0.15),  # Wider left
                    int(height * 0.02),  # Higher top
                    int(width * 0.85),  # Wider right
                    int(height * 0.50),  # Lower bottom
                ],
                fill=255,
            )
        elif t in {"clothes", "shirt", "dress", "jacket", "hoodie", "outfit"}:
            draw.rounded_rectangle(
                [
                    int(width * 0.15),
                    int(height * 0.45),
                    int(width * 0.85),
                    int(height * 0.98),
                ],
                radius=max(10, int(min(width, height) * 0.04)),
                fill=255,
            )
        elif t in {"shoes", "feet", "footwear", "sneakers", "heels", "boots"}:
            # Bottom region for shoes/feet
            draw.rounded_rectangle(
                [
                    int(width * 0.20),
                    int(height * 0.75),
                    int(width * 0.80),
                    int(height * 1.0),
                ],
                radius=max(8, int(min(width, height) * 0.03)),
                fill=255,
            )
        elif t in {"background", "sky", "wall", "scene"}:
            # Background edits are inherently global; keep this explicit.
            draw.rectangle([0, 0, width, height], fill=255)
        else:
            # Conservative center area for unknown targets (slightly larger)
            draw.rounded_rectangle(
                [
                    int(width * 0.25),
                    int(height * 0.20),
                    int(width * 0.75),
                    int(height * 0.75),
                ],
                radius=max(10, int(min(width, height) * 0.04)),
                fill=255,
            )

        return mask

    @classmethod
    def _inpaint_local_edit(cls, prompt, source_image, search_prompt="", grow=1.0):
        headers = {
            "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
            "Accept": "image/*",
        }

        source_name, content_type, image_bytes = cls._ensure_open_image(source_image)
        source_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        target = (search_prompt or "").strip() or cls._infer_search_prompt(prompt)
        mask_img = cls._build_local_mask(source_img.size, target=target, grow=grow)

        mask_buffer = io.BytesIO()
        mask_img.save(mask_buffer, format="PNG")
        mask_bytes = mask_buffer.getvalue()

        files = {
            "image": (source_name, image_bytes, content_type),
            "mask": ("mask.png", mask_bytes, "image/png"),
            "prompt": (None, cls._normalize_edit_prompt(prompt)),
            "negative_prompt": (None, cls.IDENTITY_NEGATIVE_PROMPT),
            "grow_mask": (None, "1"),
            "output_format": (None, "png"),
        }
        response = requests.post(STABILITY_EDIT_INPAINT_API_URL, headers=headers, files=files, timeout=90)
        if response.status_code != 200:
            cls._raise_for_error(response)

        return response.content

    @staticmethod
    def _is_noop_edit(source_bytes, result_bytes):
        """Detect exact or near-identical image output to trigger stronger edit fallback."""
        if not source_bytes or not result_bytes:
            return False
        if source_bytes == result_bytes:
            return True

        try:
            source_img = Image.open(io.BytesIO(source_bytes)).convert("RGB")
            result_img = Image.open(io.BytesIO(result_bytes)).convert("RGB")

            if source_img.size != result_img.size:
                result_img = result_img.resize(source_img.size)

            diff = ImageChops.difference(source_img, result_img)
            mean = sum(ImageStat.Stat(diff).mean) / 3.0
            return mean < 1.5
        except Exception:
            return False

    @staticmethod
    def _ensure_open_image(source_image):
        source_name = getattr(source_image, "name", "source.png")
        content_type = mimetypes.guess_type(source_name)[0] or "application/octet-stream"

        if hasattr(source_image, "open"):
            source_image.open("rb")
        source_image.seek(0)
        image_bytes = source_image.read()
        return source_name, content_type, image_bytes

    @staticmethod
    def _prepare_image_for_edit(source_image):
        """Resize oversized source image to Stability's max pixel limit while preserving aspect ratio."""
        source_name, content_type, image_bytes = StabilityService._ensure_open_image(source_image)

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception:
            return source_name, content_type, image_bytes, None, None

        original_size = image.size
        total_pixels = image.size[0] * image.size[1]
        if total_pixels <= STABILITY_EDIT_MAX_PIXELS:
            return source_name, content_type, image_bytes, original_size, original_size

        scale = (STABILITY_EDIT_MAX_PIXELS / float(total_pixels)) ** 0.5
        resized_width = max(64, int(image.size[0] * scale))
        resized_height = max(64, int(image.size[1] * scale))
        resized = image.resize((resized_width, resized_height), Image.LANCZOS)

        buffer = io.BytesIO()
        resized.save(buffer, format="PNG")
        resized_bytes = buffer.getvalue()

        return "resized_source.png", "image/png", resized_bytes, original_size, (resized_width, resized_height)

    @staticmethod
    def _restore_original_size(image_bytes, original_size, processed_size):
        if not original_size or not processed_size or original_size == processed_size:
            return image_bytes

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            restored = image.resize(original_size, Image.LANCZOS)
            buffer = io.BytesIO()
            restored.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception:
            return image_bytes

    @staticmethod
    def _raise_for_error(response):
        try:
            error_data = response.json()
            if error_data.get("name") == "content_moderation":
                raise ContentModerationError(
                    error_data.get("errors", ["Content flagged by moderation system"])[0]
                )
        except (json.JSONDecodeError, AttributeError):
            pass

        raise ValueError(response.text)

    @classmethod
    def _search_and_replace_edit(cls, prompt, source_image, search_prompt="", style_prompt="", allow_fallback=True):
        headers = {
            "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
            "Accept": "image/*",
        }

        source_name, content_type, image_bytes = cls._ensure_open_image(source_image)
        resolved_search_prompt = (search_prompt or "").strip() or cls._infer_search_prompt(prompt)
        full_prompt = cls._normalize_edit_prompt(prompt)
        if style_prompt:
            full_prompt = f"{full_prompt}. Style: {style_prompt}"

        files = {
            "image": (source_name, image_bytes, content_type),
            "prompt": (None, full_prompt),
            "search_prompt": (None, resolved_search_prompt),
            "negative_prompt": (None, cls.IDENTITY_NEGATIVE_PROMPT),
            "grow_mask": (None, "2"),
            "output_format": (None, "png"),
        }
        response = requests.post(STABILITY_EDIT_SEARCH_REPLACE_API_URL, headers=headers, files=files, timeout=90)
        if response.status_code == 200:
            result_bytes = response.content
            if cls._is_noop_edit(image_bytes, result_bytes):
                if not allow_fallback:
                    return result_bytes
                return cls._structure_edit(
                    prompt=full_prompt,
                    source_image=source_image,
                    control_strength=0.75,
                    search_prompt=resolved_search_prompt,
                    allow_fallback=True,
                )
            return result_bytes

        if response.status_code == 403:
            cls._raise_for_error(response)

        if not allow_fallback:
            cls._raise_for_error(response)

        return cls._structure_edit(
            prompt=full_prompt,
            source_image=source_image,
            control_strength=0.75,
            search_prompt=resolved_search_prompt,
            allow_fallback=True,
        )

    @classmethod
    def _structure_edit(cls, prompt, source_image, control_strength=0.75, search_prompt="", allow_fallback=True):
        headers = {
            "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
            "Accept": "image/*",
        }

        source_name, content_type, image_bytes = cls._ensure_open_image(source_image)
        files = {
            "image": (source_name, image_bytes, content_type),
            "prompt": (None, prompt),
            "control_strength": (None, str(max(0.0, min(1.0, control_strength)))),
            "negative_prompt": (None, cls.IDENTITY_NEGATIVE_PROMPT),
            "output_format": (None, "png"),
        }

        response = requests.post(STABILITY_CONTROL_STRUCTURE_API_URL, headers=headers, files=files, timeout=90)
        if response.status_code != 200:
            if not allow_fallback:
                cls._raise_for_error(response)
            return cls._sd3_image_to_image(prompt=prompt, source_image=source_image, strength=0.3)

        result_bytes = response.content
        if cls._is_noop_edit(image_bytes, result_bytes):
            if not allow_fallback:
                return result_bytes

            if search_prompt:
                try:
                    second_pass = cls._search_and_replace_edit(
                        prompt=prompt,
                        source_image=source_image,
                        search_prompt=search_prompt,
                        allow_fallback=False,
                    )
                    if not cls._is_noop_edit(image_bytes, second_pass):
                        return second_pass
                except Exception:
                    pass

            return cls._sd3_image_to_image(prompt=prompt, source_image=source_image, strength=0.3)

        return result_bytes

    @classmethod
    def _sd3_image_to_image(cls, prompt, source_image, strength=0.3):
        headers = {
            "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
            "Accept": "image/*",
        }

        source_name, content_type, image_bytes = cls._ensure_open_image(source_image)
        files = {
            "image": (source_name, image_bytes, content_type),
            "prompt": (None, prompt),
            "mode": (None, "image-to-image"),
            "model": (None, "sd3.5-large"),
            "strength": (None, str(max(0.0, min(1.0, strength)))),
            "cfg_scale": (None, "6"),
            "negative_prompt": (None, cls.IDENTITY_NEGATIVE_PROMPT),
            "output_format": (None, "png"),
        }

        response = requests.post(STABILITY_API_URLS["sd3"], headers=headers, files=files, timeout=90)
        if response.status_code != 200:
            cls._raise_for_error(response)

        return response.content

    @classmethod
    def _precision_edit(cls, prompt, source_image, search_prompt=""):
        """
        High-accuracy local edit pipeline for uploaded images:
        1) targeted search-and-replace (text-based region detection - most reliable)
        2) structure edit (composition-preserving, identity-safe)
        3) inpaint with mask as fallback (only if above fail)
        """
        normalized_prompt = cls._normalize_edit_prompt(prompt)
        target = (search_prompt or "").strip() or cls._infer_search_prompt(normalized_prompt)
        source_name, content_type, source_bytes = cls._ensure_open_image(source_image)
        _ = source_name, content_type

        # PRIMARY: Text-based search-and-replace (Stability's algorithm handles region detection)
        try:
            replaced = cls._search_and_replace_edit(
                prompt=normalized_prompt,
                source_image=source_image,
                search_prompt=target,
                allow_fallback=False,
            )
            if not cls._is_noop_edit(source_bytes, replaced):
                return replaced
        except Exception:
            pass

        # SECONDARY: Structure edit (preserves composition and identity)
        try:
            structured = cls._structure_edit(
                prompt=normalized_prompt,
                source_image=source_image,
                control_strength=0.75,
                search_prompt=target,
                allow_fallback=False,
            )
            if not cls._is_noop_edit(source_bytes, structured):
                return structured
        except Exception:
            pass

        # TERTIARY: Inpaint with mask (fallback - only if text-based methods fail)
        try:
            inpainted = cls._inpaint_local_edit(
                prompt=normalized_prompt,
                source_image=source_image,
                search_prompt=target,
                grow=1.0,
            )
            if not cls._is_noop_edit(source_bytes, inpainted):
                return inpainted
        except Exception:
            pass

        # FINAL: Wider inpaint pass
        try:
            inpainted_wider = cls._inpaint_local_edit(
                prompt=normalized_prompt,
                source_image=source_image,
                search_prompt=target,
                grow=1.35,
            )
            if not cls._is_noop_edit(source_bytes, inpainted_wider):
                return inpainted_wider
        except Exception:
            pass

        # Last resort: return structure edit result even if no-op detected
        return cls._structure_edit(
            prompt=normalized_prompt,
            source_image=source_image,
            control_strength=0.85,
            search_prompt=target,
            allow_fallback=False,
        )

    @staticmethod
    def generate(prompt, size="1:1", source_image=None, safety_enabled=False, strength=None, model="core", search_prompt=""):
        """
        Generate an image using Stability AI.
        
        Supports two modes:
        1. Text-to-Image: Provide only prompt → Generates new image
        2. Selective Edit (img2img): Provide source_image + prompt → Makes minimal edits while preserving original
        
        Args:
            prompt: The image description or desired edits
            size: Aspect ratio (e.g., "1:1", "16:9", etc.)
            source_image: Optional source image for selective editing
                        When provided, only minimal changes are applied (strength=0.01)
            safety_enabled: Whether to enable safety filters (default False for nudity support)
            strength: Edit intensity when source_image provided (0.01 = max preservation)
                     Only used when source_image is provided. Defaults to 0.01.
            model: Stability model endpoint to use ("core" or "ultra")
        
        Returns:
            Image bytes (PNG format)
        
        Raises:
            ContentModerationError: If content is flagged by moderation system
            ValueError: For other API errors
        """
        headers = {
            "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
            "Accept": "image/*",
        }

        if source_image and model == "precision-edit":
            return StabilityService._precision_edit(
                prompt=prompt,
                source_image=source_image,
                search_prompt=search_prompt,
            )

        if source_image and model == "search-and-replace":
            return StabilityService._search_and_replace_edit(
                prompt=prompt,
                source_image=source_image,
                search_prompt=search_prompt,
            )

        resolved_model = model
        if source_image and model == "ultra":
            # Ultra endpoint is best for text-to-image; core handles image edits reliably.
            resolved_model = "core"

        api_url = STABILITY_API_URLS.get(resolved_model, STABILITY_API_URLS["core"])
        files = {
            "prompt": (None, prompt),
            "aspect_ratio": (None, size),
            "output_format": (None, "png"),
            "safety_enabled": (None, str(safety_enabled).lower()),
        }

        if source_image:
            source_name, content_type, image_bytes = StabilityService._ensure_open_image(source_image)
            files["image"] = (source_name, image_bytes, content_type)
            # Add strength for selective img2img edits (maximum preservation at 0.01)
            if strength is None:
                strength = 0.01  # Default: maximum preservation
            files["strength"] = (None, str(max(0.0, min(1.0, strength))))

        response = requests.post(api_url, headers=headers, files=files, timeout=90)
        
        if response.status_code != 200:
            StabilityService._raise_for_error(response)
        
        return response.content

    @staticmethod
    def upscale(image_bytes):
        """Upscale an already-generated image using Stability fast upscaler."""
        headers = {
            "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
            "Accept": "image/*",
        }
        files = {
            "image": ("generated.png", image_bytes, "image/png"),
            "output_format": (None, "png"),
        }

        response = requests.post(STABILITY_UPSCALE_FAST_API_URL, headers=headers, files=files, timeout=90)
        if response.status_code != 200:
            raise ValueError(response.text)

        return response.content



