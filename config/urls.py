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
from django.conf import settings
from django.conf.urls.static import static

# 새로 만든 HomeView 임포트
from chatbot.api.views import (  # Import privacy_policy view
    HomeView,
    Rating,
    chat,
    chat_view,
    privacy_policy,
)

# Import NaverCallbackView directly
from users.views import NaverCallbackView, NaverLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("django-rq/", include("django_rq.urls")),  # Add RQ dashboard URLs
    # path("chatbot/", include("chatbot.api.urls")),
    path("users/", include("users.urls")),  # Include users app URLs
    path(
        "social-auth/", include("social_django.urls", namespace="social")
    ),  # Social auth URLs
    path("", HomeView.as_view(), name="home"),
    path(
        "mypage/",
        login_required(TemplateView.as_view(template_name="auth/mypage.html")),
        name="mypage",
    ),  # mypage page, login required
    # Add Naver auth URLs at the root level
    path("naver/callback/", NaverCallbackView.as_view(), name="naver_callback"),
    path("naver/login/", NaverLoginView.as_view(), name="naver_login"),
    path("notifications/", include("notifications.urls", namespace="notifications")),
    # Add chat URLs at the root level
    path("chat/", chat_view, name="root_chat_view_with_no_nonce"),
    path("chat/<str:session_nonce>/", chat_view, name="root_chat_view_with_nonce"),
    path("api/chat/", chat, name="root_chat_api"),
    path("api/rating/", Rating.as_view(), name="rating_api"),
    # Privacy policy URL
    path("privacy/", privacy_policy, name="privacy_policy"),
    # Content uploader URL
    path("contents/", include("content_uploader.urls")),
    # Payment plan URL
    path(
        "payplan/",
        TemplateView.as_view(template_name="payment/payplan.html"),
        name="payplan",
    ),
]

# 개발 환경에서 미디어 파일을 서빙하기 위한 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
