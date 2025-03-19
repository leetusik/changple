from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SocialAuthView, UserViewSet

# Create a router and register viewsets
router = DefaultRouter()
router.register(r"users", UserViewSet)

# API URL patterns
urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
    # Social auth endpoint
    path("social-auth/", SocialAuthView.as_view(), name="social-auth"),
]
