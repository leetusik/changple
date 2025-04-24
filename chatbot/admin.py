import csv
from datetime import datetime

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import ChatMessage, ChatSession

admin.site.site_header = format_html('<img src="/static/img/cp-logo-main.svg" height="40px" style="margin-right: 10px; filter: brightness(0) invert(1);"><br>Changple AI - Admin Page')
admin.site.site_title = "창플 AI 관리자 페이지"
admin.site.index_title = "관리자 home"

class ChatMessageInline(admin.StackedInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("role", "created_at", "user_liked", "user_disliked")
    fields = ("role", "content", "user_disliked", "created_at")
    can_delete = False
    verbose_name = "채팅 내용"
    verbose_name_plural = "채팅 내용"


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "get_first_message",
        "user",
        "updated_at",
        "is_updated",
        "updated_by",
        "download_session_link",
    )
    search_fields = ("session_id", "user__name", "user__nickname", "user__username", "user__email")
    readonly_fields = ("session_nonce", "session_id", "request_sent", "is_updated", "updated_by")
    list_filter = ("created_at", "updated_at", "user", "updated_by", "is_updated")
    date_hierarchy = "created_at"
    inlines = [ChatMessageInline]
    actions = ["export_selected_sessions"]
    save_on_top = True
    list_per_page = 20
    fieldsets = (
        ("체크 박스", {"fields": ("request_sent", "is_updated", "updated_by")}),
        ("세션 정보", {"fields": ("session_id", "session_nonce")}),
    )

    def download_session_link(self, obj):
        return format_html(
            '<a href="{}?session_id={}" class="button">Download</a>',
            "/admin/chatbot/chatsession/download-session/",
            obj.session_id,
        )

    download_session_link.short_description = "Download"

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "download-session/",
                self.admin_site.admin_view(self.download_session_view),
                name="download-session",
            ),
        ]
        return custom_urls + urls

    def download_session_view(self, request):
        session_id = request.GET.get("session_id")
        if not session_id:
            return HttpResponse("No session ID provided", status=400)

        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = session.messages.all().order_by("created_at")

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="chat_session_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            )

            writer = csv.writer(response)
            writer.writerow(["Timestamp", "Role", "Content"])

            for message in messages:
                writer.writerow(
                    [
                        message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        message.role,
                        message.content,
                    ]
                )

            return response
        except ChatSession.DoesNotExist:
            return HttpResponse("Session not found", status=404)

    def export_selected_sessions(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="chat_sessions_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            ["Session ID", "User", "Created At", "Timestamp", "Role", "Content"]
        )

        for session in queryset:
            messages = session.messages.all().order_by("created_at")
            if not messages:
                writer.writerow(
                    [
                        session.session_id,
                        session.user.username if session.user else "Anonymous",
                        session.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "",
                        "",
                        "",
                    ]
                )
            else:
                for message in messages:
                    writer.writerow(
                        [
                            session.session_id,
                            session.user.username if session.user else "Anonymous",
                            session.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            message.role,
                            message.content,
                        ]
                    )

        return response

    export_selected_sessions.short_description = "Export selected sessions to CSV"

    def save_model(self, request, obj, form, change):
        if change:
            print(f"chat {obj.session_id} modified (Admin) by {request.user.username}")
            obj.is_updated = True
            obj.updated_by = request.user.username
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        # disable adding new ChatSession
        return False

# @admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "role",
        "short_content",
        "created_at",
        "download_message_link",
    )
    list_filter = ("role", "created_at", "session__user")
    search_fields = (
        "content",
        "session__session_id",
        "session__user__username",
        "session__user__email",
    )
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    actions = ["export_selected_messages"]

    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    short_content.short_description = "Content"

    def download_message_link(self, obj):
        return format_html(
            '<a href="{}?message_id={}" class="button">Download</a>',
            "/admin/chatbot/chatmessage/download-message/",
            obj.id,
        )

    download_message_link.short_description = "Download"

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "download-message/",
                self.admin_site.admin_view(self.download_message_view),
                name="download-message",
            ),
        ]
        return custom_urls + urls

    def download_message_view(self, request):
        message_id = request.GET.get("message_id")
        if not message_id:
            return HttpResponse("No message ID provided", status=400)

        try:
            message = ChatMessage.objects.get(id=message_id)

            response = HttpResponse(content_type="text/plain")
            response["Content-Disposition"] = (
                f'attachment; filename="message_{message_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"'
            )

            response.write(f"Session: {message.session.session_id}\n")
            response.write(f"Role: {message.role}\n")
            response.write(
                f'Created: {message.created_at.strftime("%Y-%m-%d %H:%M:%S")}\n\n'
            )
            response.write(message.content)

            return response
        except ChatMessage.DoesNotExist:
            return HttpResponse("Message not found", status=404)

    def export_selected_messages(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="chat_messages_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["Session ID", "User", "Timestamp", "Role", "Content"])

        for message in queryset:
            writer.writerow(
                [
                    message.session.session_id,
                    (
                        message.session.user.username
                        if message.session.user
                        else "Anonymous"
                    ),
                    message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    message.role,
                    message.content,
                ]
            )

        return response

    export_selected_messages.short_description = "Export selected messages to CSV"
