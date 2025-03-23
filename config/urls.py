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
# 새로 만든 HomeView 임포트
from chatbot.api.views import HomeView  # core 앱을 생성했다고 가정, 원하는 앱에 뷰를 만들 수 있습니다

urlpatterns = [
    path("admin/", admin.site.urls),
    path("django-rq/", include("django_rq.urls")),  # Add RQ dashboard URLs
    path("chatbot/", include("chatbot.api.urls")),
    path("users/", include("users.urls")),  # Include users app URLs
    path(
        "social-auth/", include("social_django.urls", namespace="social")
    ),  # Social auth URLs
    path("", HomeView.as_view(), name="home"),
    path(
        "profile/",
        login_required(TemplateView.as_view(template_name="auth/profile.html")),
        name="profile",
    ),  # Profile page, login required
    # Add Naver auth URLs at the root level
    path("naver/callback/", NaverCallbackView.as_view(), name="naver_callback"),
    path("naver/login/", NaverLoginView.as_view(), name="naver_login"),
    path("notifications/", include("notifications.urls", namespace="notifications")),
]
