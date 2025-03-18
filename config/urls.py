"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView

# Import NaverCallbackView directly
from users.views import NaverCallbackView, NaverLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("django-rq/", include("django_rq.urls")),  # Add RQ dashboard URLs
    path("users/", include("users.urls")),  # Include users app URLs
    path(
        "social-auth/", include("social_django.urls", namespace="social")
    ),  # Social auth URLs
    path(
        "", TemplateView.as_view(template_name="index.html"), name="home"
    ),  # Home page
    path(
        "mypage/",
        login_required(TemplateView.as_view(template_name="mypage.html")),
        name="mypage",
    ),  # My page, login required
    path(
        "login-error/",
        TemplateView.as_view(template_name="login_error.html"),
        name="login_error",
    ),  # Login error page
    # Add Naver auth URLs at the root level
    path("naver/callback/", NaverCallbackView.as_view(), name="naver_callback_root"),
    path("naver/login/", NaverLoginView.as_view(), name="naver_login_root"),
]
