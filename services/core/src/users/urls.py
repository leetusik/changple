"""
URL patterns for users API.
"""

from django.urls import path

from src.users.api_views import CurrentUserView, UserProfileUpdateView, UserWithdrawView

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="user-me"),
    path("profile/", UserProfileUpdateView.as_view(), name="user-profile-update"),
    path("withdraw/", UserWithdrawView.as_view(), name="user-withdraw"),
]
