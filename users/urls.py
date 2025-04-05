from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from django.views.generic import RedirectView

from .views import NaverCallbackView, NaverLoginView, logout_view, withdraw_account

urlpatterns = [
    # Include API URLs
    path("api/", include("users.api.urls")),
    # Basic auth URLs
    path("logout/", logout_view, name="logout"),
    path("login/", RedirectView.as_view(url="/", permanent=False), name="login"),
    # Account management
    path("withdraw/", login_required(withdraw_account), name="withdraw_account"),
    # Social login URLs will be added as they are implemented
    # Example: path('login/google/', GoogleLoginView.as_view(), name='login_google'),
    # Example: path('login/google/callback/', GoogleLoginCallbackView.as_view(), name='login_google_callback'),
    # Naver social login URLs
    path("naver/login/", NaverLoginView.as_view(), name="naver_login"),
    path("naver/callback/", NaverCallbackView.as_view(), name="naver_callback"),
]
