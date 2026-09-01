from rest_framework import serializers
from .models import *


class NewsletterSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscription
        fields = ["id", "email", "is_active", "subscribed_at"]
        read_only_fields = ["id", "subscribed_at"]


class NewsletterSubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if NewsletterSubscription.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already subscribed.")
        return value


class FooterDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FooterData
        fields = [
            "id",
            "contact_email",
            "contact_phone",
            "facebook_url",
            "twitter_url",
            "instagram_url",
            "tiktok_url",
            "youtube_url",
            "linkedin_url",
            "all_rights_reserved",
        ]
        read_only_fields = ["id"]


class ContactSerializer(serializers.ModelSerializer):
    subject_display = serializers.CharField(source="get_subject_display", read_only=True)
    
    class Meta:
        model = Contact
        fields = [
            "id",
            "full_name",
            "email",
            "subject",
            "subject_display",
            "message",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ContactCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "full_name",
            "email",
            "subject",
            "message",
        ]

    def validate_subject(self, value):
        valid_choices = [choice[0] for choice in Contact.Subject.choices]
        if value not in valid_choices:
            raise serializers.ValidationError("Invalid subject choice.")
        return value

class GenExampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenExample
        fields = ["id", "prompt", "image", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]