from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    Form for creating admin users.
    """

    class Meta:
        model = User
        fields = ("username", "email", "user_type")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = "admin"  # Force user_type to admin for manual creation
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Form for updating user information.
    """

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "user_type")
