from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    Form for creating admin users.
    """

    name = forms.CharField(max_length=255, required=True, help_text="Full Korean name")
    nickname = forms.CharField(
        max_length=100, required=False, help_text="Display nickname (optional)"
    )

    class Meta:
        model = User
        fields = ("email", "name", "nickname", "user_type")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field from the form
        if "username" in self.fields:
            del self.fields["username"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = "admin"  # Force user_type to admin for manual creation

        # Set the name and nickname fields
        user.name = self.cleaned_data.get("name")
        user.nickname = self.cleaned_data.get("nickname")

        # No need to set username - model.save will handle it based on ID

        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Form for updating user information.
    """

    class Meta:
        model = User
        fields = (
            "email",
            "name",
            "nickname",
            "mobile",
            "user_type",
            "provider",
            "social_id",
            "profile_image",
            "daily_query_limit",
            "is_premium",
            "premium_until",
        )
        # Exclude username from form
        exclude = ("username",)
