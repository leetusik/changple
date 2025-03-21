from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model that supports both admin users and social login users.
    Admin users can log in through Django admin interface with username/password.
    Regular users can only login through social authentication.

    Note: username is still required by Django's auth system but we don't use it.
    We use the name field instead for displaying users.
    """

    # Hide username but keep it unique (will be filled with social_id or ID)
    username = models.CharField(
        max_length=150,
        unique=True,  # Required by Django auth
        help_text="Internal field used for authentication only.",
        editable=False,  # Hide from forms
    )

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

    # In Korean context, we use full name rather than first/last name
    # We'll keep this as the primary name field
    name = models.CharField(max_length=255, null=True, blank=True)

    # Nickname field for display
    nickname = models.CharField(max_length=100, blank=True)

    mobile = models.CharField(max_length=20, blank=True, null=True)

    # User query related fields
    daily_query_limit = models.IntegerField(default=10)
    daily_queries_used = models.IntegerField(default=0)
    last_query_reset = models.DateTimeField(default=timezone.now)

    # Payment related fields
    is_premium = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def is_admin_user(self):
        return self.user_type == "admin"

    def is_social_user(self):
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
            # Save again with the ID-based username (but avoid infinite recursion)
            type(self).objects.filter(pk=self.pk).update(username=self.username)

        # Ensure we have a value in name field
        if not self.name and self.nickname:
            self.name = self.nickname
            type(self).objects.filter(pk=self.pk).update(name=self.nickname)

    def has_available_queries(self):
        # Reset counter if it's a new day
        if timezone.now().date() > self.last_query_reset.date():
            self.daily_queries_used = 0
            self.last_query_reset = timezone.now()
            self.save()

        # Premium users have unlimited queries
        if (
            self.is_premium
            and self.premium_until
            and self.premium_until > timezone.now()
        ):
            return True

        return self.daily_queries_used < self.daily_query_limit

    def increment_query_count(self):
        # Reset counter if it's a new day
        if timezone.now().date() > self.last_query_reset.date():
            self.daily_queries_used = 0
            self.last_query_reset = timezone.now()

        self.daily_queries_used += 1
        self.save()

    def __str__(self):
        """Show name as the string representation instead of username"""
        return self.name or self.nickname or self.email or self.username
