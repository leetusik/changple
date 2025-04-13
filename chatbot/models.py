import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

# Create your models here.


class ChatSession(models.Model):
    """채팅 세션 모델"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_nonce = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    request_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"채팅 세션 {self.session_id}"

    def get_absolute_url(self):
        """Return the URL for accessing this chat session using the nonce"""
        return reverse("root_chat_view_with_nonce", args=[str(self.session_nonce)])

    def get_first_message(self):
        """Get the first user message of this session"""
        first_message = self.messages.filter(role="user").order_by("created_at").first()
        if first_message:
            return (
                first_message.content[:20] + "..."
                if len(first_message.content) > 20
                else first_message.content
            )
        return "Empty chat"


class ChatMessage(models.Model):
    """채팅 메시지 모델"""

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20)  # 'user' 또는 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
