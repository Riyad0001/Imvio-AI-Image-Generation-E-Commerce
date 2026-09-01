from rest_framework import serializers

from .models import (
    User,
    # Profile
)


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=['validate_password'])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password', 'password2')

    def validate_password(self, value):
        if value['password'] != value['password2']:
            raise serializers.ValidationError('Passwords do not match')
        return value

    def create(self, validated_data):
        validated_data.pop('password2')
        try:
            user = User.objects.create_user(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(e)
        return user
