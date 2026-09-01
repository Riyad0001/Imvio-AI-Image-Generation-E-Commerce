from unfold.admin import ModelAdmin
from django.contrib import admin
from .models import *


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(ModelAdmin):
    list_display = ["email", "subscribed_at"]
    list_filter = [ "subscribed_at"]
    search_fields = ["email"]
    readonly_fields = ["subscribed_at"]


@admin.register(FooterData)
class FooterDataAdmin(ModelAdmin):
    list_display = ["contact_email", "contact_phone"]
    search_fields = ["contact_email"]
    fieldsets = (
        ("Contact Information", {
            "fields": ("contact_email", "contact_phone")
        }),
        ("Social Media Links", {
            "fields": ("facebook_url", "twitter_url", "instagram_url", "tiktok_url", "youtube_url", "linkedin_url")
        }),
        ("Footer Text", {
            "fields": ("all_rights_reserved",)
        }),
    )


@admin.register(Contact)
class ContactAdmin(ModelAdmin):
    list_display = ["full_name", "email", "subject", "is_read", "created_at"]
    list_filter = ["subject", "is_read", "created_at"]
    search_fields = ["full_name", "email", "subject"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Contact Information", {
            "fields": ("full_name", "email")
        }),
        ("Message", {
            "fields": ("subject", "message")
        }),
        ("Status", {
            "fields": ("is_read",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

@admin.register(GenExample)
class GenExampleAdmin(ModelAdmin):
    list_display = ["prompt", "created_at"]
    search_fields = ["prompt"]
    readonly_fields = ["created_at", "updated_at"]