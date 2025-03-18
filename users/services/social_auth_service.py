import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class SocialAuthService:
    """
    Service for handling social authentication.
    Responsible for creating/retrieving users based on social login data.
    """

    @staticmethod
    def get_or_create_user(provider, social_id, email, **extra_data):
        """
        Get an existing user or create a new one based on social login data.

        Args:
            provider (str): Social auth provider (e.g., 'google', 'facebook')
            social_id (str): Unique ID from the social provider
            email (str): User's email address
            **extra_data: Additional user data like first_name, last_name, profile_image

        Returns:
            User: User instance
            bool: True if user was created, False if existing user
        """
        try:
            # Try to find existing user by provider and social_id
            user = User.objects.get(provider=provider, social_id=social_id)
            created = False

            # Update user data that might have changed
            if extra_data:
                for key, value in extra_data.items():
                    if hasattr(user, key) and value:
                        setattr(user, key, value)
                user.save()

            return user, created
        except User.DoesNotExist:
            # Try to find user by email
            try:
                user = User.objects.get(email=email)
                # Update social auth fields
                user.provider = provider
                user.social_id = social_id
                if extra_data:
                    for key, value in extra_data.items():
                        if hasattr(user, key) and value:
                            setattr(user, key, value)
                user.save()
                return user, False
            except User.DoesNotExist:
                # Create new user
                username = f"{provider}_{social_id}"

                # Check if username exists, if so, make it unique
                if User.objects.filter(username=username).exists():
                    username = f"{provider}_{social_id}_{User.objects.count()}"

                user_data = {
                    "username": username,
                    "email": email,
                    "provider": provider,
                    "social_id": social_id,
                    "user_type": "social",
                    **extra_data,
                }

                user = User.objects.create(**user_data)
                return user, True

    @staticmethod
    def update_user_profile(user, provider, profile_data):
        """
        Update user profile with data from social login.

        Args:
            user (User): User instance
            provider (str): Social auth provider
            profile_data (dict): Profile data from social provider

        Returns:
            User: Updated user instance
        """
        if user.provider != provider:
            logger.warning(
                f"Attempted to update {user.provider} user with {provider} data"
            )
            return user

        # Update fields based on provider
        if provider == "naver":
            if profile_data.get("profile_image"):
                user.profile_image = profile_data.get("profile_image")

            if profile_data.get("username"):
                user.name = profile_data.get("username")

            # Special case for specific user
            if profile_data.get("email") == "gusang0@naver.com":
                user.nickname = "sugnag"
            elif not user.nickname and profile_data.get("email"):
                # Set nickname to email username part
                email_parts = profile_data.get("email", "").split("@")
                user.nickname = email_parts[0] if email_parts else ""

        # Add more providers as needed

        user.save()
        return user
