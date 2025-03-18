from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "users"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("naver/callback/", views.naver_login_callback, name="naver_callback"),
    path("api/login/naver/", views.naver_login_api, name="naver_login_api"),
    path(
        "api/login/naver/callback/",
        views.naver_login_callback_api,
        name="naver_callback_api",
    ),
    path("login/success/", views.login_success_view, name="login_success"),
    path("api/me/", views.user_info_api, name="user_info_api"),
    path("profile/", views.profile_view, name="profile"),
    path("mypage/", RedirectView.as_view(pattern_name="users:profile"), name="mypage"),
]
