from django.contrib.auth import get_user_model

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
