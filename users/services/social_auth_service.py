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
                # Create new user - username will be set automatically based on social_id in the model
                user_data = {
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

            # Update mobile if available
            if profile_data.get("mobile"):
                user.mobile = profile_data.get("mobile")

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

    @staticmethod
    def disconnect_naver_and_delete_user(user, access_token):
        """
        Disconnect user from Naver API and delete their account.

        Args:
            user (User): User instance to delete
            access_token (str): Naver access token

        Returns:
            bool: True if successful, False otherwise
        """
        import requests
        from django.conf import settings

        # Only proceed with Naver disconnection if user is a Naver social user
        if user.provider != "naver" or not user.social_id:
            logger.warning(f"Attempted to disconnect non-Naver user: {user.id}")
            # Still delete the user even if not Naver user
            user.delete()
            return True

        # Try to get access token from user model if not provided
        if not access_token and hasattr(user, "naver_access_token"):
            access_token = user.naver_access_token
            logger.info(f"Using access token from user model for user {user.id}")

        # If still no access token, log a warning but continue with user deletion
        if not access_token:
            logger.warning(
                f"No access token available for Naver user {user.id}, skipping Naver disconnection"
            )
            user.delete()
            return True

        # Call Naver API to disconnect the user
        try:
            disconnect_url = "https://nid.naver.com/oauth2.0/token"
            params = {
                "grant_type": "delete",
                "client_id": settings.SOCIAL_AUTH_NAVER_KEY,
                "client_secret": settings.SOCIAL_AUTH_NAVER_SECRET,
                "access_token": access_token,
            }

            logger.info(f"Calling Naver disconnection API for user {user.id}")
            logger.info(f"Using client_id: {settings.SOCIAL_AUTH_NAVER_KEY[:5]}***")
            logger.info(f"Using access_token: {access_token[:5]}***")

            response = requests.get(disconnect_url, params=params)
            data = response.json()

            if response.status_code == 200 and data.get("result") == "success":
                logger.info(f"Successfully disconnected Naver user: {user.id}")
            else:
                logger.warning(
                    f"Failed to disconnect Naver user: {user.id}. Response: {data}"
                )
        except Exception as e:
            logger.error(f"Error disconnecting Naver user: {str(e)}")
            # Continue with user deletion even if Naver disconnection fails

        # Delete the user regardless of Naver disconnect result
        try:
            user.delete()
            logger.info(f"User {user.id} successfully deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False
