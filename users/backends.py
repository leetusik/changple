from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class SocialAuthBackend(ModelBackend):
    """
    Custom authentication backend for social login.
    Authenticates users based on provider and social_id.
    """

    def authenticate(self, request, provider=None, social_id=None, **kwargs):
        if provider is None or social_id is None:
            return None

        try:
            user = User.objects.get(provider=provider, social_id=social_id)
            return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
