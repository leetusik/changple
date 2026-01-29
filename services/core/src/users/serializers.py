"""
Serializers for users app.
"""

from rest_framework import serializers

from src.users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "nickname",
            "profile_image",
            "user_type",
            "provider",
            "mobile",
            "information",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "email",
            "user_type",
            "provider",
            "date_joined",
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = [
            "name",
            "nickname",
            "mobile",
            "information",
        ]
