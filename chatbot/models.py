import uuid

from django.db import models
from django.urls import reverse

# Create your models here.


class ChatSession(models.Model):
    """채팅 세션 모델"""

    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_nonce = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        return f"채팅 세션 {self.session_id}"

    def get_absolute_url(self):
        """Return the URL for accessing this chat session using the nonce"""
        return reverse("root_chat_view_with_nonce", args=[str(self.session_nonce)])


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
