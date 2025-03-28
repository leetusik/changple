from django.urls import include, path
from rest_framework import routers

from . import views
from .api.views import ConsultationRequestAPIView, EmailLogViewSet, SendEmailAPIView

router = routers.DefaultRouter()
router.register(r"emails", EmailLogViewSet)

app_name = "notifications"

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/send-email/", SendEmailAPIView.as_view(), name="send_email"),
    path(
        "api/consultation-request/",
        ConsultationRequestAPIView.as_view(),
        name="consultation_request",
    ),
    # Web interface URLs
    path("send-email/", views.send_email_page, name="send_email_page"),
    path("send-test-email/", views.send_test_email, name="send_test_email"),
]
