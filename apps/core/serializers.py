from rest_framework import serializers
from .models import User
from django.db import transaction
import uuid

class SignupSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'password', 'confirm_password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        email = User.objects.normalize_email(validated_data.get("email", "").strip())

        with transaction.atomic():
            deleted_user = User.all_objects.select_for_update().filter(email=email, is_deleted=True).first()
            if deleted_user and not deleted_user.email.endswith("@deleted.local"):
                deleted_user.email = f"deleted-{deleted_user.pk}-{uuid.uuid4().hex[:8]}@deleted.local"
                deleted_user.save(update_fields=["email", "updated_at"])

            validated_data["email"] = email
            user = User(**validated_data)
            user.set_password(password)
            user.save()
        return user


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('full_name', 'email', 'password', 'password2')

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password2 and password != password2:
            raise serializers.ValidationError('Passwords do not match')
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2', None)
        password = validated_data.pop('password')

        email = User.objects.normalize_email(validated_data.get("email", "").strip())

        with transaction.atomic():
            deleted_user = User.all_objects.select_for_update().filter(email=email, is_deleted=True).first()
            if deleted_user and not deleted_user.email.endswith("@deleted.local"):
                deleted_user.email = f"deleted-{deleted_user.pk}-{uuid.uuid4().hex[:8]}@deleted.local"
                deleted_user.save(update_fields=["email", "updated_at"])

            validated_data["email"] = email
            user = User(**validated_data)
            user.set_password(password)
            user.save()
        return user
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")

        validate_password(data['new_password'])
        return data
from rest_framework import serializers

class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=False, allow_blank=True)
    token = serializers.CharField(required=False, allow_blank=True)
    credential = serializers.CharField(required=False, allow_blank=True)
    access_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        raw_token = (
            attrs.get('id_token')
            or attrs.get('token')
            or attrs.get('credential')
            or attrs.get('access_token')
        )

        if not raw_token:
            raise serializers.ValidationError('Google token is required')

        attrs['id_token'] = raw_token.strip()
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    total_available_credits = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "phone_number",
            "profile_photo",
            "is_disabled",
            "total_available_credits",
            "created_at",
        ]
        read_only_fields = ["id", "email", "is_disabled", "created_at"]

    def get_total_available_credits(self, obj):
        wallet = getattr(obj, "wallet", None)
        return wallet.balance if wallet else 0


class ProfileUpdateSerializer(serializers.ModelSerializer):
    remove_profile_photo = serializers.BooleanField(default=False, write_only=True, required=False)

    class Meta:
        model = User
        fields = ["full_name", "phone_number", "profile_photo", "remove_profile_photo"]

    def update(self, instance, validated_data):
        remove_photo = validated_data.pop("remove_profile_photo", False)
        if remove_photo and instance.profile_photo:
            instance.profile_photo.delete(save=False)
            instance.profile_photo = None

        return super().update(instance, validated_data)


class CreditBalanceSerializer(serializers.Serializer):
    total_available_credits = serializers.IntegerField()