from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class NaverUserProfile(models.Model):
    """
    Profile model that extends the built-in User model through a OneToOneField.
    This approach avoids migrations issues while providing all the custom fields we need.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="naver_profile"
    )
    naver_id = models.CharField(max_length=255, unique=True)
    nickname = models.CharField(max_length=255)
    profile_image = models.URLField(max_length=2000, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    age = models.CharField(max_length=10, blank=True, null=True)
    birthday = models.CharField(max_length=10, blank=True, null=True)

    # Add new fields from Naver profile API
    name = models.CharField(max_length=255, blank=True, null=True)
    birthyear = models.CharField(max_length=4, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)

    # User query related fields
    daily_query_limit = models.IntegerField(default=10)
    daily_queries_used = models.IntegerField(default=0)
    last_query_reset = models.DateTimeField(default=timezone.now)

    # Payment related fields
    is_premium = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nickname

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


# Keep the temp model for migration compatibility
class TempModel(models.Model):
    name = models.CharField(max_length=255)
