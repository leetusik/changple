from rest_framework import serializers

from notifications.models import EmailLog


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer for the EmailLog model"""

    class Meta:
        model = EmailLog
        fields = [
            "id",
            "recipient",
            "subject",
            "template",
            "status",
            "status_message",
            "sent_at",
            "created_at",
        ]
        read_only_fields = ["status", "status_message", "sent_at", "created_at"]


class SendEmailSerializer(serializers.Serializer):
    """Serializer for sending an email"""

    email = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()

    class Meta:
        fields = ["email", "subject", "message"]
