"""
Admin configuration for chat app.
"""

from django.contrib import admin

from src.chat.models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """Admin for ChatSession."""

    list_display = ["id", "nonce", "user", "message_count", "created_at", "updated_at"]
    list_filter = ["created_at"]
    search_fields = ["nonce", "user__email", "user__name"]
    ordering = ["-updated_at"]
    readonly_fields = ["nonce", "created_at", "updated_at"]

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Messages"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin for ChatMessage."""

    list_display = ["id", "session", "role", "content_preview", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["content", "session__nonce"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "Content"
