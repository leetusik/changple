from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r"logs", views.EmailLogViewSet, basename="email-log")

# URL patterns
urlpatterns = [
    # ViewSet URLs
    path("", include(router.urls)),
    # Send email endpoint
    path("send/", views.SendEmailAPIView.as_view(), name="send-email"),
]
