from rest_framework import serializers

from apps.image_gen.models import GeneratedImage, ImageGenerationJob, ImageSize, ImageStyle


class ImageSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageSize
        fields = ["id", "size"]


class ImageStyleSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ImageStyle
        fields = ["id", "name", "style_text", "image_url"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if not obj.image:
            return None
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class GenerateImageRequestSerializer(serializers.Serializer):
    """
    Serializer for image generation and editing requests.
    
    Two modes:
    1. Text-to-Image: Provide only prompt → Generates new image
    2. Image Edit: Provide source_image + prompt → Edits only the parts you describe changing
    """
    prompt = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Describe the image (or desired changes). For editing, include context: 'person wearing red shirt' not just 'red shirt'"
    )
    style_id = serializers.PrimaryKeyRelatedField(
        queryset=ImageStyle.objects.filter(is_active=True),
        source="style",
        required=False,
        allow_null=True,
        help_text="Style ID from the styles list (optional)"
    )
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=ImageSize.objects.all(), 
        source="size",
        required=False,
        allow_null=True,
        help_text="Image size/aspect ratio ID (optional, defaults to 1:1)"
    )
    source_image = serializers.ImageField(
        required=False, 
        allow_null=True,
        help_text="Upload image to edit. Only specified changes will be applied, everything else preserved."
    )
    search_prompt = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional target object/region for image editing (e.g. 'eyes', 'shirt', 'background').",
    )


class RegenerateImageRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Edit instructions or description. Optional if style_id is provided."
    )
    style_id = serializers.PrimaryKeyRelatedField(
        queryset=ImageStyle.objects.filter(is_active=True),
        source="style",
        required=False,
        allow_null=True,
        help_text="Style ID to apply (optional). Falls back to the existing image's style if not provided."
    )


class SaveCreationSerializer(serializers.Serializer):
    image_id = serializers.IntegerField(required=False)
    image = serializers.ImageField(required=False, allow_null=True)
    image_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    custom_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    prompt = serializers.CharField(required=False, allow_blank=True, default="")
    style = serializers.CharField(required=False, allow_blank=True, default="")
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=ImageSize.objects.all(),
        source="size",
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        image_id = attrs.get("image_id")
        image = attrs.get("image")

        if not image_id and not image:
            raise serializers.ValidationError("Either image_id or image is required")

        if image_id and image:
            raise serializers.ValidationError("Provide only one of image_id or image")

        image_name = attrs.get("image_name") or attrs.get("custom_name")
        if image and not image_name:
            raise serializers.ValidationError("image_name is required when uploading image")

        attrs["resolved_name"] = image_name or attrs.get("custom_name") or "Untitled"

        return attrs


class GeneratedImageSerializer(serializers.ModelSerializer):
    size = ImageSizeSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    source_image_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    share_link = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedImage
        fields = [
            "id",
            "user",
            "custom_name",
            "title",
            "prompt",
            "user_prompt",
            "style",
            "size",
            "tags",
            "description",
            "is_saved_creation",
            "created_at",
            "image_url",
            "source_image_url",
            "download_url",
            "share_link",
        ]

    def get_user(self, obj):
        user = obj.user
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }

    def get_image_url(self, obj):
        request = self.context.get("request")
        if not obj.image:
            return None
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def get_source_image_url(self, obj):
        request = self.context.get("request")
        if not obj.source_image:
            return None
        if request:
            return request.build_absolute_uri(obj.source_image.url)
        return obj.source_image.url

    def get_download_url(self, obj):
        request = self.context.get("request")
        relative = f"/api/v1/images/{obj.id}/download/"
        if request:
            return request.build_absolute_uri(relative)
        return relative

    def get_share_link(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(f"/api/v1/images/{obj.id}/share/{obj.share_id}/")
        return f"/api/v1/images/{obj.id}/share/{obj.share_id}/"


class GenerationJobSerializer(serializers.ModelSerializer):
    size = ImageSizeSerializer(read_only=True)
    generated_image = GeneratedImageSerializer(read_only=True)

    class Meta:
        model = ImageGenerationJob
        fields = [
            "id",
            "prompt",
            "style",
            "size",
            "status",
            "credit_cost",
            "error_message",
            "created_at",
            "generated_image",
        ]
