"""
Admin configuration for users app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from src.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin."""

    list_display = [
        "id",
        "email",
        "name",
        "nickname",
        "user_type",
        "provider",
        "is_active",
        "date_joined",
    ]
    list_filter = ["user_type", "provider", "is_active", "is_staff"]
    search_fields = ["email", "name", "nickname", "username"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {"fields": ("email", "name", "nickname", "mobile", "profile_image")},
        ),
        (
            "Social auth",
            {"fields": ("user_type", "provider", "social_id", "naver_access_token")},
        ),
        ("Additional info", {"fields": ("information",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "user_type"),
            },
        ),
    )
