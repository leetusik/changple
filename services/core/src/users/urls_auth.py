"""
URL patterns for authentication API.
"""

from django.urls import path

from src.users.auth_views import AuthStatusView, LogoutView, NaverCallbackView, NaverLoginView

urlpatterns = [
    path("naver/login/", NaverLoginView.as_view(), name="naver-login"),
    path("naver/callback/", NaverCallbackView.as_view(), name="naver-callback"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("status/", AuthStatusView.as_view(), name="auth-status"),
]
