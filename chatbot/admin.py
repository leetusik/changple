import csv
from datetime import datetime

from django.contrib import admin
from django.db.models import Exists, OuterRef
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

from .models import ChatMessage, ChatSession

admin.site.site_header = format_html(
    '<img src="/static/img/cp-logo-main.svg" height="40px" style="margin-right: 10px; filter: brightness(0) invert(1);"><br>Changple AI - Admin Page'
)
admin.site.site_title = "창플 AI 관리자 페이지"
admin.site.index_title = "관리자 home"


class ChatMessageInline(admin.StackedInline):
    model = ChatMessage
    extra = 0
    readonly_fields = (
        "role",
        "formatted_content",
        "user_messages_content",
        "formatted_rating",
        "formatted_retrieve_queries",
        "formatted_helpful_documents",
        "created_at",
    )
    fields = (
        "user_messages_content",
        "formatted_content",
        "formatted_rating",
        "formatted_retrieve_queries",
        "formatted_helpful_documents",
        "created_at",
        "human_feedback",
    )
    can_delete = False
    verbose_name = "채팅 메시지"
    verbose_name_plural = "채팅 기록"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role="assistant")

    def user_messages_content(self, obj):
        if obj.session:
            previous_user_message = (
                obj.session.messages.filter(role="user", created_at__lt=obj.created_at)
                .order_by("-created_at")
                .first()
            )

            if previous_user_message:
                return previous_user_message.content
        return "-"

    user_messages_content.short_description = "사용자 질문"

    def formatted_content(self, obj):
        md = MarkdownIt()
        return mark_safe(md.render(obj.content))

    formatted_content.short_description = "창플 AI 답변"

    def formatted_rating(self, obj):
        if obj.good_or_bad == "good":
            return format_html(
                '<span style="color: green; font-weight: bold;">👍 좋아요</span>'
            )
        elif obj.good_or_bad == "bad":
            return format_html(
                '<span style="color: red; font-weight: bold;">👎 별로예요</span>'
            )
        return "-"

    formatted_rating.short_description = "피드백"

    def formatted_retrieve_queries(self, obj):
        if obj.retrieve_queries:
            if isinstance(obj.retrieve_queries, list):
                return format_html("<br>".join(obj.retrieve_queries))
            else:
                return obj.retrieve_queries
        return "-"

    formatted_retrieve_queries.short_description = "검색 쿼리"

    def formatted_helpful_documents(self, obj):
        if obj.helpful_documents:
            if isinstance(obj.helpful_documents, list):
                doc_strings = []
                for doc in obj.helpful_documents:
                    title = doc.get("title", "N/A")
                    source = doc.get("source", "#")
                    doc_strings.append(
                        f'<a href="{source}" target="_blank">{title}</a>'
                    )
                return format_html("<br>".join(doc_strings))
            else:
                return obj.helpful_documents
        return "-"

    formatted_helpful_documents.short_description = "참고 문서"


# Custom filter for sessions with rated messages
class HasRatedMessagesFilter(admin.SimpleListFilter):
    title = "피드백이 있는 세션"
    parameter_name = "has_rated_messages"

    def lookups(self, request, model_admin):
        return (
            ("liked", "좋아요 있음"),
            ("disliked", "별로예요 있음"),
            ("any_rating", "아무 피드백이나 있음"),
        )

    def queryset(self, request, queryset):
        if self.value() == "liked":
            return queryset.filter(
                Exists(
                    ChatMessage.objects.filter(
                        session=OuterRef("pk"), good_or_bad="good"
                    )
                )
            )
        elif self.value() == "disliked":
            return queryset.filter(
                Exists(
                    ChatMessage.objects.filter(
                        session=OuterRef("pk"), good_or_bad="bad"
                    )
                )
            )
        elif self.value() == "any_rating":
            return queryset.filter(
                Exists(
                    ChatMessage.objects.filter(
                        session=OuterRef("pk"), good_or_bad__isnull=False
                    )
                )
            )
        return queryset


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "get_first_message",
        "user",
        "updated_at",
        "is_updated",
        "updated_by",
        "has_ratings",
        "download_session_link",
    )
    search_fields = (
        "session_id",
        "user__name",
        "user__nickname",
        "user__username",
        "user__email",
    )
    readonly_fields = (
        "session_nonce",
        "session_id",
        "request_sent",
        "is_updated",
        "updated_by",
    )
    list_filter = (
        "created_at",
        HasRatedMessagesFilter,
        # "updated_at",
        # "user",
        "updated_by",
        "is_updated",
    )
    date_hierarchy = "created_at"
    inlines = [ChatMessageInline]
    actions = ["export_selected_sessions"]
    save_on_top = True
    list_per_page = 20
    fieldsets = (
        ("체크 박스", {"fields": ("request_sent", "is_updated", "updated_by")}),
        ("세션 정보", {"fields": ("session_id", "session_nonce")}),
    )

    def has_ratings(self, obj):
        good_count = obj.messages.filter(good_or_bad="good").count()
        bad_count = obj.messages.filter(good_or_bad="bad").count()

        result = []
        if good_count:
            result.append(f'<span style="color: green;">👍 {good_count}</span>')
        if bad_count:
            result.append(f'<span style="color: red;">👎 {bad_count}</span>')

        if result:
            return format_html(" | ".join(result))
        return "-"

    has_ratings.short_description = "피드백"

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
            writer.writerow(["Timestamp", "Role", "Content", "Rating"])

            for message in messages:
                writer.writerow(
                    [
                        message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        message.role,
                        message.content,
                        message.good_or_bad or "-",
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
            [
                "Session ID",
                "User",
                "Created At",
                "Timestamp",
                "Role",
                "Content",
                "Rating",
            ]
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
                            message.good_or_bad or "-",
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
        "good_or_bad",
        "created_at",
        "download_message_link",
    )
    list_filter = ("role", "created_at", "session__user", "good_or_bad")
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
                f'Created: {message.created_at.strftime("%Y-%m-%d %H:%M:%S")}\n'
            )
            if message.good_or_bad:
                response.write(f"Rating: {message.good_or_bad}\n")
            response.write("\n")
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
        writer.writerow(
            ["Session ID", "User", "Timestamp", "Role", "Content", "Rating"]
        )

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
                    message.good_or_bad or "-",
                ]
            )

        return response

    export_selected_messages.short_description = "Export selected messages to CSV"
