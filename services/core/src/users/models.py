"""
User models for Changple Core service.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model that supports both admin users and social login users.
    Admin users can log in through Django admin interface with username/password.
    Regular users can only login through social authentication.
    """

    # Hide username but keep it unique (will be filled with social_id or ID)
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Internal field used for authentication only.",
        editable=False,
    )

    USER_TYPE_CHOICES = (
        ("admin", "Admin"),
        ("social", "Social User"),
    )
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default="social",
    )

    # Social auth fields
    provider = models.CharField(max_length=30, blank=True)
    social_id = models.CharField(max_length=100, blank=True)
    profile_image = models.URLField(blank=True)

    # Token for social auth operations (disconnection)
    naver_access_token = models.TextField(blank=True, null=True)

    # In Korean context, we use full name rather than first/last name
    name = models.CharField(max_length=255, null=True, blank=True)

    # Nickname field for display
    nickname = models.CharField(max_length=100, blank=True)

    mobile = models.CharField(max_length=20, blank=True, null=True)

    # User profile information stored as JSON
    information = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text="Structured user profile information",
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def is_admin_user(self) -> bool:
        return self.user_type == "admin"

    def is_social_user(self) -> bool:
        return self.user_type == "social"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # For social users, use social_id as username if available
        if self.is_social_user() and self.social_id and not self.username:
            provider_prefix = f"{self.provider}_" if self.provider else ""
            self.username = f"{provider_prefix}{self.social_id}"

        # First save to get an ID for new users
        super().save(*args, **kwargs)

        # For admin users or if no social_id is available, use ID-based username
        if is_new and not self.username and not self.social_id:
            self.username = f"id_{self.pk}"
            type(self).objects.filter(pk=self.pk).update(username=self.username)

        # Ensure we have a value in name field
        if not self.name and self.nickname:
            self.name = self.nickname
            type(self).objects.filter(pk=self.pk).update(name=self.nickname)

    def __str__(self):
        """Show name as the string representation instead of username"""
        return self.name or self.nickname or self.email or self.username
