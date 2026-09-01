import base64
import io
from django.conf import settings
import httpx
import requests
from openai import OpenAI
from PIL import Image


class OpenAIImageEditService:
    """
    Image editing service using OpenAI gpt-image-2.
    """

    def __init__(self):
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")
        base_url = getattr(settings, "OPENAI_BASE_URL", "") or None
        project_id = getattr(settings, "OPENAI_PROJECT_ID", "") or None
        organization = getattr(settings, "OPENAI_ORG_ID", "") or None
        # Use an explicit httpx client to avoid proxy-related initialization issues.
        http_client = httpx.Client(timeout=60.0)
        self.client = OpenAI(
            api_key=api_key,
            http_client=http_client,
            base_url=base_url,
            project=project_id,
            organization=organization,
        )
        self._base_url = base_url
        self._project_id = project_id
        self._organization = organization

    @staticmethod
    def _ensure_image_bytes(image_file):
        if hasattr(image_file, "read"):
            return image_file.read()
        if isinstance(image_file, bytes):
            return image_file
        raise ValueError("Invalid image format")

    @staticmethod
    def _build_prompt(prompt, style=""):
        prompt_text = (prompt or "").strip()
        if style:
            # Style is the primary directive; prompt is supplementary context
            return f"{style}. {prompt_text}".strip(". ")
        return prompt_text

    def edit_image(self, source_image, prompt, style=""):
        image_bytes = self._ensure_image_bytes(source_image)

        try:
            source_img = Image.open(io.BytesIO(image_bytes))
            if source_img.mode != "RGB":
                source_img = source_img.convert("RGB")
            normalized_image = io.BytesIO()
            source_img.save(normalized_image, format="PNG")
            normalized_image.seek(0)
            image_bytes = normalized_image.getvalue()
        except Exception as e:
            raise ValueError(f"Failed to load image: {str(e)}")

        edit_prompt = self._build_prompt(prompt, style=style)

        file_name = getattr(source_image, "name", "image.png")
        if not file_name.lower().endswith(".png"):
            file_name = f"{file_name.rsplit('.', 1)[0] if '.' in file_name else file_name}.png"
        content_type = "image/png"

        base_url = self._base_url or "https://api.openai.com"
        if base_url.endswith("/v1"):
            url = f"{base_url}/images/edits"
        else:
            url = f"{base_url}/v1/images/edits"

        headers = {
            "Authorization": f"Bearer {getattr(settings, 'OPENAI_API_KEY', '')}",
        }
        if self._project_id:
            headers["OpenAI-Project"] = self._project_id
        if self._organization:
            headers["OpenAI-Organization"] = self._organization

        files = {
            "image": (file_name, image_bytes, content_type),
        }
        data = {
            "model": "gpt-image-2",
            "prompt": edit_prompt,
            "size": "1024x1024",
        }

        try:
            response = requests.post(url, headers=headers, files=files, data=data, timeout=180)
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_detail = error_data.get("error", {})
                code = error_detail.get("code")
                message = error_detail.get("message", "")
                if code == "moderation_blocked":
                    raise ValueError("The request was flagged by OpenAI's safety/moderation system. Please revise your prompt or select a different style.")
                elif message:
                    raise ValueError(message)
            except Exception as parse_err:
                if isinstance(parse_err, ValueError):
                    raise parse_err
                pass
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

        result = response.json()
        data_list = result.get("data") or []
        if not data_list:
            raise ValueError("OpenAI API returned no image data")

        image_b64 = data_list[0].get("b64_json")
        if not image_b64:
            raise ValueError("OpenAI API response missing image payload")

        return base64.b64decode(image_b64)

    @staticmethod
    def _extract_image_from_response(response):
        if not response or not getattr(response, "output", None):
            raise ValueError("OpenAI API returned no output")

        for output in response.output:
            content_list = getattr(output, "content", None) or []
            for part in content_list:
                part_type = getattr(part, "type", "")
                if part_type in {"output_image", "image"}:
                    image_payload = getattr(part, "image_base64", None) or getattr(part, "b64_json", None)
                    if image_payload:
                        return base64.b64decode(image_payload)

        raise ValueError("OpenAI API response missing image payload")

    # def _responses_http(self, edit_prompt, image_data_url):
    #     api_key = getattr(settings, "OPENAI_API_KEY", None)
    #     if not api_key:
    #         raise ValueError("OPENAI_API_KEY not configured in settings")

    #     base_url = self._base_url or "https://api.openai.com"
    #     if base_url.endswith("/v1"):
    #         url = f"{base_url}/responses"
    #     else:
    #         url = f"{base_url}/v1/responses"

    #     headers = {
    #         "Authorization": f"Bearer {api_key}",
    #         "Content-Type": "application/json",
    #     }
    #     if self._project_id:
    #         headers["OpenAI-Project"] = self._project_id
    #     if self._organization:
    #         headers["OpenAI-Organization"] = self._organization

    #     payload = {
    #         "model": "gpt-image-2",
    #         "input": [
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {"type": "input_text", "text": edit_prompt},
    #                     {"type": "input_image", "image_url": image_data_url},
    #                 ],
    #             }
    #         ],
    #     }

    #     response = requests.post(url, headers=headers, json=payload, timeout=90)
    #     if response.status_code != 200:
    #         raise Exception(response.text)

    #     data = response.json()
    #     output = data.get("output") or []
    #     for item in output:
    #         for part in item.get("content", []):
    #             if part.get("type") in {"output_image", "image"}:
    #                 image_payload = part.get("image_base64") or part.get("b64_json")
    #                 if image_payload:
    #                     return base64.b64decode(image_payload)

    #     raise ValueError("OpenAI API response missing image payload")

    def _responses_http(self, edit_prompt, image_data_url):
        api_key = getattr(settings, "OPENAI_API_KEY", None)

        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        base_url = self._base_url or "https://api.openai.com"

        if base_url.endswith("/v1"):
            url = f"{base_url}/responses"
        else:
            url = f"{base_url}/v1/responses"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if self._project_id:
            headers["OpenAI-Project"] = self._project_id

        if self._organization:
            headers["OpenAI-Organization"] = self._organization

        payload = {
            "model": "gpt-image-2-2026-04-21",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": edit_prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                        },
                    ],
                }
            ],
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=180,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise Exception(
                f"OpenAI API error: "
                f"{response.status_code} - {response.text}"
            )

        data = response.json()

        output = data.get("output", [])

        for item in output:
            for part in item.get("content", []):

                if part.get("type") == "output_image":
                    image_payload = part.get("image_base64")

                    if image_payload:
                        return base64.b64decode(image_payload)

        raise ValueError("No image returned from OpenAI")
