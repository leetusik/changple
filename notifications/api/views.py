import django_rq
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import EmailLog
from notifications.tasks import send_notification_email

from .serializers import EmailLogSerializer, SendEmailSerializer


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing EmailLogs (read-only)"""

    queryset = EmailLog.objects.all().order_by("-created_at")
    serializer_class = EmailLogSerializer

    def get_queryset(self):
        """Filter logs by recipient if provided"""
        queryset = super().get_queryset()
        recipient = self.request.query_params.get("recipient")
        if recipient:
            queryset = queryset.filter(recipient=recipient)
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset


class SendEmailAPIView(APIView):
    """API view for sending an email"""

    def post(self, request, *args, **kwargs):
        """Send an email via RQ"""
        serializer = SendEmailSerializer(data=request.data)

        if serializer.is_valid():
            # Queue the email job
            django_rq.enqueue(
                send_notification_email,
                user_email=serializer.validated_data["email"],
                subject=serializer.validated_data["subject"],
                message=serializer.validated_data["message"],
            )

            return Response(
                {
                    "status": "success",
                    "message": "이메일이 성공적으로 대기열에 추가되었습니다.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
