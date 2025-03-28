from django.contrib import admin

from .models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("session_id", "created_at", "updated_at")
    search_fields = ("session_id",)
    readonly_fields = ("session_nonce",)
    list_filter = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "short_content", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "session__session_id")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"

    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    short_content.short_description = "Content"
