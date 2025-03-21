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
            # Find user by provider and social_id (which should be unique)
            user = User.objects.get(provider=provider, social_id=social_id)
            return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class EmailBackend(ModelBackend):
    """
    Custom authentication backend for admin users.
    Authenticates users with email and password instead of username.
    Username is now automatically set to use social_id or ID for uniqueness.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try to authenticate by email first
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            # Try with username as fallback for admin users
            try:
                # Only look for admin users with this username
                user = User.objects.filter(user_type="admin").get(username=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                pass
        return None
