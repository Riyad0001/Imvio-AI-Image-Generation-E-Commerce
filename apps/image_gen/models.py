from django.db import models
from apps.core.models import User
import uuid


class ImageSize(models.Model):
    size = models.CharField(max_length=16, unique=True)

    def __str__(self):
        return self.size


class ImageStyle(models.Model):
    name = models.CharField(max_length=255, help_text="Display name for this style")
    style_text = models.TextField(help_text="Style prompt text sent to the AI model")
    image = models.ImageField(upload_to="styles/", blank=True, null=True, help_text="Preview image for this style")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GeneratedImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.TextField()
    user_prompt = models.TextField(blank=True, help_text="The raw prompt typed by the user (before composition)")
    style = models.TextField(blank=True)
    size = models.ForeignKey(ImageSize, on_delete=models.PROTECT, related_name="generated_images")
    source_image = models.ImageField(upload_to="generated/source/", blank=True, null=True)
    image = models.ImageField(upload_to="generated/")
    custom_name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    share_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_saved_creation = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True, related_name="regenerated_versions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.prompt


class ImageGenerationJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="image_generation_jobs")
    prompt = models.TextField()
    user_prompt = models.TextField(blank=True, help_text="Raw prompt typed by the user before composition")
    style = models.TextField(blank=True,null=True)
    size = models.ForeignKey(ImageSize, on_delete=models.PROTECT, related_name="generation_jobs")
    source_image = models.ImageField(upload_to="generated/job-source/", blank=True, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    credit_cost = models.PositiveIntegerField(default=5)
    error_message = models.TextField(blank=True)
    generated_image = models.ForeignKey(GeneratedImage, on_delete=models.SET_NULL, blank=True, null=True, related_name="jobs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ImageCreditSettings(models.Model):
    generation_credit_cost = models.PositiveIntegerField(default=5)
    regeneration_credit_cost = models.PositiveIntegerField(default=5)
    download_credit_cost = models.PositiveIntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Image Credit Settings"
        verbose_name_plural = "Image Credit Settings"

    def __str__(self):
        return f"Generate: {self.generation_credit_cost}, Regenerate: {self.regeneration_credit_cost}, Download: {self.download_credit_cost}"

    @classmethod
    def get_solo(cls):
        settings_obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "generation_credit_cost": 5,
                "regeneration_credit_cost": 5,
                "download_credit_cost": 10,
            },
        )
        return settings_obj