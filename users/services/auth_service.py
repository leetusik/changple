from django.contrib.auth import get_user_model

User = get_user_model()


class AuthService:
    """
    Service for handling user authentication.
    """

    @staticmethod
    def get_user_by_id(user_id):
        """
        Get a user by their ID.

        Args:
            user_id (int): User ID

        Returns:
            User: User instance or None
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_email(email):
        """
        Get a user by their email.

        Args:
            email (str): User email

        Returns:
            User: User instance or None
        """
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def generate_unique_username(base_username):
        """
        Generate a unique username based on a base username.

        Args:
            base_username (str): Base username

        Returns:
            str: Unique username
        """
        username = base_username
        count = 1

        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{count}"
            count += 1

        return username
