"""
URL configuration for Changple Core service.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/auth/", include("src.users.urls_auth")),
    path("api/v1/users/", include("src.users.urls")),
    path("api/v1/content/", include("src.content.urls")),
    path("api/v1/chat/", include("src.chat.urls")),
    path("api/v1/scraper/", include("src.scraper.urls")),
    # OpenAPI documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
