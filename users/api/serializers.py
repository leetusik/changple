from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "name",
            "nickname",
            "user_type",
            "provider",
            "social_id",
            "profile_image",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "date_joined",
            "last_login",
            "user_type",
            "provider",
            "social_id",
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for User profile data.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "name",
            "nickname",
            "profile_image",
        ]
        read_only_fields = ["id", "email"]


class SocialAuthSerializer(serializers.Serializer):
    """
    Serializer for social authentication data.
    """

    provider = serializers.CharField()
    code = serializers.CharField()
    redirect_uri = serializers.CharField(required=False)

    class Meta:
        fields = ["provider", "code", "redirect_uri"]
