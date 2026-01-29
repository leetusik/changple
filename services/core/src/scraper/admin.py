"""
Admin configuration for scraper app.
"""

from django.contrib import admin

from src.scraper.models import AllowedAuthor, BatchJob, GoodtoKnowBrands, NaverCafeData, PostStatus


@admin.register(NaverCafeData)
class NaverCafeDataAdmin(admin.ModelAdmin):
    """Admin for NaverCafeData."""

    list_display = [
        "post_id",
        "title",
        "author",
        "category",
        "ingested",
        "published_date",
    ]
    list_filter = ["ingested", "author", "category"]
    search_fields = ["title", "content", "author", "post_id"]
    ordering = ["-published_date"]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 50


@admin.register(PostStatus)
class PostStatusAdmin(admin.ModelAdmin):
    """Admin for PostStatus."""

    list_display = ["post_id", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["post_id", "error_message"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AllowedAuthor)
class AllowedAuthorAdmin(admin.ModelAdmin):
    """Admin for AllowedAuthor."""

    list_display = ["name", "author_group", "is_active"]
    list_filter = ["author_group", "is_active"]
    search_fields = ["name"]
    ordering = ["author_group", "name"]


@admin.register(GoodtoKnowBrands)
class GoodtoKnowBrandsAdmin(admin.ModelAdmin):
    """Admin for GoodtoKnowBrands."""

    list_display = ["name", "is_goodto_know"]
    list_filter = ["is_goodto_know"]
    search_fields = ["name", "description"]


@admin.register(BatchJob)
class BatchJobAdmin(admin.ModelAdmin):
    """Admin for BatchJob."""

    list_display = [
        "id",
        "job_type",
        "provider",
        "status",
        "post_count",
        "submitted_at",
        "completed_at",
    ]
    list_filter = ["job_type", "provider", "status"]
    search_fields = ["job_id"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def post_count(self, obj):
        return len(obj.post_ids) if obj.post_ids else 0

    post_count.short_description = "Posts"
