from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model that supports both admin users and social login users.
    Admin users can log in through Django admin interface with username/password.
    Regular users can only login through social authentication.
    """

    USER_TYPE_CHOICES = (
        ("admin", "Admin"),
        ("social", "Social User"),
    )
    user_type = models.CharField(
        max_length=10, choices=USER_TYPE_CHOICES, default="social"
    )

    # Social auth fields
    provider = models.CharField(max_length=30, blank=True)
    social_id = models.CharField(max_length=100, blank=True)
    profile_image = models.URLField(blank=True)

    # Add the missing name field
    name = models.CharField(max_length=255, null=True, blank=True)

    # Add a nickname field
    nickname = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def is_admin_user(self):
        return self.user_type == "admin"

    def is_social_user(self):
        return self.user_type == "social"

    def save(self, *args, **kwargs):
        # Auto-populate name field from first_name and last_name if not provided
        if not self.name and (self.first_name or self.last_name):
            self.name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)
