from django.contrib import admin, messages
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

    # Default fieldsets for all users
    default_fieldsets = (
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

    # Read-only fieldsets for social users
    social_user_fieldsets = (
        (
            None,
            {"fields": ("name",)},
        ),
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
            _("User type"),
            {
                "fields": ("user_type",),
                "description": "Social users can only login through social authentication.",
            },
        ),
        (
            _("Social login info"),
            {
                "fields": ("provider", "social_id"),
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
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    # Use default fieldsets initially
    fieldsets = default_fieldsets

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

    # List of fields that can be safely edited for social users
    EDITABLE_SOCIAL_FIELDS = [
        "daily_query_limit",
        "is_premium",
        "premium_until",
        "is_active",
    ]

    def get_readonly_fields(self, request, obj=None):
        """Make all fields read-only for social users except for specific fields"""
        if obj and obj.user_type == "social":
            # For social users, make all fields read-only except the allowed ones
            return [
                field.name
                for field in obj._meta.fields
                if field.name not in self.EDITABLE_SOCIAL_FIELDS
            ]
        return ["daily_queries_used", "last_query_reset"]  # Always read-only fields

    def get_fieldsets(self, request, obj=None):
        """Use different fieldsets for social users"""
        if obj and obj.user_type == "social":
            return self.social_user_fieldsets
        return self.default_fieldsets

    def has_change_permission(self, request, obj=None):
        """Allow changing social users but with limited fields"""
        return True

    def save_model(self, request, obj, form, change):
        """Safely save user models to avoid foreign key constraint issues"""
        try:
            if change and obj.user_type == "social":
                # Only update specific fields for social users using raw update
                update_fields = {
                    field: getattr(obj, field)
                    for field in self.EDITABLE_SOCIAL_FIELDS
                    if field in form.cleaned_data
                }

                # Only update if we have fields to update
                if update_fields:
                    User.objects.filter(pk=obj.pk).update(**update_fields)
                    messages.success(request, f"Successfully updated user {obj.name}")
                else:
                    messages.warning(request, "No fields were updated")
            else:
                # For admin users or new users, use normal save
                super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving user: {str(e)}")


admin.site.register(User, CustomUserAdmin)
