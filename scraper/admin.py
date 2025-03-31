from django.contrib import admin

from scraper.models import AllowedAuthor, AllowedCategory, NaverCafeData, PostStatus


class NaverCafeDataAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "published_date", "url", "post_id", "vectorized")
    list_filter = ("vectorized",)
    search_fields = ("title", "content")
    list_per_page = 20


class PostStatusAdmin(admin.ModelAdmin):
    list_display = ("post_id", "status", "last_checked", "error_message")
    list_filter = ("status", "last_checked")
    search_fields = ("post_id", "error_message")
    list_per_page = 50
    readonly_fields = ("last_checked",)
    actions = ["delete_post_statuses"]

    def delete_post_statuses(self, request, queryset):
        """Action to delete selected post statuses to allow re-crawling"""
        deleted_count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f"{deleted_count} post statuses have been deleted. These posts will be attempted again when crawling.",
        )

    delete_post_statuses.short_description = (
        "Delete selected post statuses (allows re-crawling)"
    )


class AllowedCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_group", "is_active", "date_added")
    list_filter = ("is_active", "category_group")
    search_fields = ("name",)
    list_per_page = 50  # Show more categories per page
    actions = ["activate_categories", "deactivate_categories"]
    ordering = ("category_group", "name")  # Sort by group then name
    list_editable = ["is_active"]  # Allow toggling active status directly from the list

    def activate_categories(self, request, queryset):
        """Action to activate multiple categories at once"""
        queryset.update(is_active=True)
        self.message_user(
            request, f"{queryset.count()} categories have been activated."
        )

    activate_categories.short_description = "Activate selected categories"

    def deactivate_categories(self, request, queryset):
        """Action to deactivate multiple categories at once"""
        queryset.update(is_active=False)
        self.message_user(
            request, f"{queryset.count()} categories have been deactivated."
        )

    deactivate_categories.short_description = "Deactivate selected categories"


class AllowedAuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "author_group", "is_active", "date_added")
    list_filter = ("is_active", "author_group")
    search_fields = ("name",)
    list_per_page = 50
    actions = ["activate_authors", "deactivate_authors"]
    ordering = ("author_group", "name")
    list_editable = ["is_active"]  # Allow toggling active status directly from the list

    def activate_authors(self, request, queryset):
        """Action to activate multiple authors at once"""
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} authors have been activated.")

    activate_authors.short_description = "Activate selected authors"

    def deactivate_authors(self, request, queryset):
        """Action to deactivate multiple authors at once"""
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} authors have been deactivated.")

    deactivate_authors.short_description = "Deactivate selected authors"


admin.site.register(NaverCafeData, NaverCafeDataAdmin)
admin.site.register(PostStatus, PostStatusAdmin)
admin.site.register(AllowedCategory, AllowedCategoryAdmin)
admin.site.register(AllowedAuthor, AllowedAuthorAdmin)
