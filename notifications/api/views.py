import os

import django_rq
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import EmailLog
from notifications.tasks import send_consultation_request_email, send_notification_email

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


class ConsultationRequestAPIView(APIView):
    """API view for sending a consultation request email"""

    def post(self, request, *args, **kwargs):
        """Send a consultation request email to host"""
        user_email = request.data.get("user_email", "")
        session_nonce = request.data.get("session_nonce", "")
        additional_message = request.data.get("message", "")

        if not user_email:
            return Response(
                {"error": "사용자 이메일은 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not session_nonce:
            return Response(
                {"error": "세션 정보가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Import here to avoid circular imports
        from chatbot.models import ChatSession

        try:
            # Get chat session and messages
            chat_session = ChatSession.objects.get(session_nonce=session_nonce)
            chat_messages = chat_session.messages.all()

            # Format chat messages for email
            formatted_messages = [
                {
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at,
                }
                for message in chat_messages[1:]  # to avoid duplicated initial message.
            ]
            host_email = os.getenv("EMAIL_HOST_USER")
            # Host email address (you can set this in settings.py or .env)
            # host_email = request.data.get("host_email") or "tiger9@changple.com"

            # Queue the consultation request email
            django_rq.enqueue(
                send_consultation_request_email,
                host_email=host_email,
                user_email=user_email,
                chat_history=formatted_messages,
                additional_message=additional_message,
            )

            chat_session.request_sent = True
            chat_session.save()

            return Response(
                {
                    "status": "success",
                    "message": "상담 요청이 성공적으로 전송되었습니다.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except ChatSession.DoesNotExist:
            return Response(
                {"error": "유효하지 않은 채팅 세션입니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": f"상담 요청 전송 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
