"""
Admin configuration for content app.
"""

from django.contrib import admin

from src.content.models import ContentViewHistory, NotionContent


@admin.register(NotionContent)
class NotionContentAdmin(admin.ModelAdmin):
    """Admin for NotionContent."""

    list_display = [
        "id",
        "title",
        "is_preferred",
        "uploaded_at",
        "updated_at",
    ]
    list_filter = ["is_preferred", "uploaded_at"]
    search_fields = ["title", "description"]
    ordering = ["-uploaded_at"]
    readonly_fields = ["html_path", "contents_img_path", "uploaded_at", "updated_at"]


@admin.register(ContentViewHistory)
class ContentViewHistoryAdmin(admin.ModelAdmin):
    """Admin for ContentViewHistory."""

    list_display = ["id", "user", "content", "viewed_at"]
    list_filter = ["viewed_at"]
    search_fields = ["user__email", "user__name", "content__title"]
    ordering = ["-viewed_at"]
    readonly_fields = ["viewed_at"]
