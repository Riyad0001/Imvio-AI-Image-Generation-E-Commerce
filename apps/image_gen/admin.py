from django.contrib import admin
from apps.image_gen.models import GeneratedImage, ImageGenerationJob, ImageSize, ImageCreditSettings, ImageStyle


# @admin.register(ImageSize)
# class ImageSizeAdmin(admin.ModelAdmin):
# 	list_display = ("id", "size")
# 	search_fields = ("size",)


@admin.register(ImageStyle)
class ImageStyleAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "style_text", "is_active", "created_at")
	search_fields = ("name", "style_text")
	list_filter = ("is_active",)
	list_editable = ("is_active",)


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "size", "created_at", "is_saved_creation", "is_deleted")
	search_fields = ("prompt", "style", "user__email")
	list_filter = ("size", "is_saved_creation", "is_deleted", "created_at")


@admin.register(ImageGenerationJob)
class ImageGenerationJobAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "status", "size", "credit_cost", "created_at")
	search_fields = ("prompt", "style", "user__email")
	list_filter = ("status", "size", "created_at")


@admin.register(ImageCreditSettings)
class ImageCreditSettingsAdmin(admin.ModelAdmin):
	list_display = ("generation_credit_cost", "regeneration_credit_cost", "download_credit_cost", "updated_at")

	def has_add_permission(self, request):
		return not ImageCreditSettings.objects.exists()
