from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

# Import and unregister social_django models
from social_django.models import Association, Nonce, UserSocialAuth

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import User

# Unregister social_django models
try:
    admin.site.unregister(Association)
    admin.site.unregister(Nonce)
    admin.site.unregister(UserSocialAuth)
except admin.sites.NotRegistered:
    # Handle case where models are not registered
    pass


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = (
        "name",
        "nickname",
        "email",
        "user_type",
        "is_premium",
        "daily_queries_used",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "user_type",
        "is_staff",
        "is_superuser",
        "is_active",
        "is_premium",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "password",
                )
            },
        ),  # Remove username from here
        (
            _("Korean User Information"),
            {
                "fields": (
                    "nickname",
                    "email",
                    "mobile",
                    "profile_image",
                ),
                "description": "Primary user information in Korean context.",
            },
        ),
        (
            _("Legacy Name Fields"),
            {
                "fields": ("first_name", "last_name"),
                "classes": ("collapse",),
                "description": "Legacy fields from Django's User model - not used in Korean context.",
            },
        ),
        (
            _("User type"),
            {
                "fields": ("user_type",),
                "description": "Admin users can log in through Django admin. Social users can only login through social authentication.",
            },
        ),
        (
            _("Social login info"),
            {
                "fields": ("provider", "social_id"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Query Management"),
            {
                "fields": (
                    "daily_query_limit",
                    "daily_queries_used",
                    "last_query_reset",
                ),
                "description": "Manage user's daily query limits and usage.",
            },
        ),
        (
            _("Premium Status"),
            {
                "fields": ("is_premium", "premium_until"),
                "description": "Manage user's premium subscription status.",
            },
        ),
        (
            _("Permissions"),
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
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "nickname",
                    "password1",
                    "password2",
                    "user_type",
                    "is_staff",
                ),
            },
        ),
    )
    search_fields = (
        "name",
        "nickname",
        "email",
        "mobile",
    )
    ordering = ("name", "id")
    readonly_fields = ("last_query_reset", "daily_queries_used")


admin.site.register(User, CustomUserAdmin)
