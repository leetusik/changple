"""
Chat models for Changple Core service.

Note: Real-time chat is handled by the Agent service.
This module only manages chat history persistence.
"""

import uuid

from django.conf import settings
from django.db import models

from src.common.models import CommonModel


class ChatSession(CommonModel):
    """
    Chat session model.

    Sessions can be associated with authenticated users or be anonymous.
    The nonce field provides a unique identifier for client-side session tracking.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )
    nonce = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chat Session"
        verbose_name_plural = "Chat Sessions"

    def __str__(self):
        return f"채팅 세션 {self.nonce}"


class ChatMessage(CommonModel):
    """
    Chat message model.

    Stores individual messages within a chat session.
    """

    ROLE_CHOICES = [
        ("user", "사용자"),
        ("assistant", "창플 AI"),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
    )
    content = models.TextField()
    attached_content_ids = models.JSONField(
        default=list,
        null=True,
        blank=True,
        help_text="첨부된 NotionContent의 ID 목록",
    )
    helpful_documents = models.ManyToManyField(
        "scraper.NaverCafeData",
        blank=True,
        related_name="referenced_in_messages",
        help_text="이 메시지 생성에 참조된 문서들",
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."
