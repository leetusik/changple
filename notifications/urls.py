from django.urls import include, path

from . import views

app_name = "notifications"

urlpatterns = [
    # API URLs
    path("api/", include("notifications.api.urls")),
    # Web interface URLs
    path("send-email/", views.send_email_page, name="send_email_page"),
    path("send-test-email/", views.send_test_email, name="send_test_email"),
]
