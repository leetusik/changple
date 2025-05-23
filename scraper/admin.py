from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from scraper.models import (
    AllowedAuthor,
    AllowedCategory,
    DisallowedBrands,
    GoodtoKnowBrands,
    NaverCafeData,
    PostStatus,
)


class ActiveCategoryFilter(admin.SimpleListFilter):
    title = _("활성화된 카테고리")
    parameter_name = "active_category"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("활성화된 카테고리만")),
            ("no", _("비활성화된 카테고리 포함")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            active_categories = AllowedCategory.objects.filter(
                is_active=True
            ).values_list("name", flat=True)
            return queryset.filter(category__in=active_categories)
        return queryset


class ActiveAuthorFilter(admin.SimpleListFilter):
    title = _("활성화된 작성자")
    parameter_name = "active_author"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("활성화된 작성자만")),
            ("no", _("비활성화된 작성자 포함")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            active_authors = AllowedAuthor.objects.filter(is_active=True).values_list(
                "name", flat=True
            )
            return queryset.filter(author__in=active_authors)
        return queryset


class NaverCafeDataAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "published_date", "post_id")
    list_filter = (ActiveCategoryFilter, ActiveAuthorFilter, "category")
    search_fields = ("title", "content", "category", "post_id")
    list_per_page = 20
    actions = ["enqueue_cafe_sync", "only_error_scrape"]

    def enqueue_cafe_sync(self, request, queryset):

        from django_rq import get_queue

        from scraper.tasks import run_sync_db_with_cafe_data

        queue = get_queue("default")
        job = queue.enqueue(run_sync_db_with_cafe_data, timeout=36000)
        self.message_user(request, f"Enqueued cafe sync job with ID: {job.id}")

    enqueue_cafe_sync.short_description = "Enqueue Cafe Sync Job (DB ↔ Cafe)"

    def only_error_scrape(self, request, queryset):
        from django_rq import get_queue

        from scraper.tasks import run_only_error_scrape

        queue = get_queue("default")
        job = queue.enqueue(run_only_error_scrape, timeout=36000)
        self.message_user(request, f"Enqueded only error scraper")

    only_error_scrape.short_description = "Enqueue Only Error Scraper"


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


class DisallowedBrandsAdmin(admin.ModelAdmin):
    list_display = ("name", "is_disallowed", "date_added")
    list_filter = ("is_disallowed",)
    search_fields = ("name",)
    list_per_page = 50
    actions = ["activate_disallowed_brands", "deactivate_disallowed_brands"]
    list_editable = ["is_disallowed"]

    def activate_disallowed_brands(self, request, queryset):
        queryset.update(is_disallowed=True)
        self.message_user(
            request, f"{queryset.count()} disallowed brands have been activated."
        )

    activate_disallowed_brands.short_description = "Activate selected disallowed brands"

    def deactivate_disallowed_brands(self, request, queryset):
        queryset.update(is_disallowed=False)
        self.message_user(
            request, f"{queryset.count()} disallowed brands have been deactivated."
        )

    deactivate_disallowed_brands.short_description = (
        "Deactivate selected disallowed brands"
    )


class GoodtoKnowBrandsAdmin(admin.ModelAdmin):
    list_display = ("name", "is_goodto_know", "date_added")
    list_filter = ("is_goodto_know",)
    search_fields = ("name",)
    list_per_page = 50
    actions = ["activate_goodto_know_brands", "deactivate_goodto_know_brands"]
    list_editable = ["is_goodto_know"]

    def activate_goodto_know_brands(self, request, queryset):
        queryset.update(is_goodto_know=True)
        self.message_user(
            request, f"{queryset.count()} good to know brands have been activated."
        )

    activate_goodto_know_brands.short_description = (
        "Activate selected good to know brands"
    )

    def deactivate_goodto_know_brands(self, request, queryset):
        queryset.update(is_goodto_know=False)
        self.message_user(
            request, f"{queryset.count()} good to know brands have been deactivated."
        )

    deactivate_goodto_know_brands.short_description = (
        "Deactivate selected good to know brands"
    )


admin.site.register(AllowedAuthor, AllowedAuthorAdmin)
admin.site.register(DisallowedBrands, DisallowedBrandsAdmin)
admin.site.register(GoodtoKnowBrands, GoodtoKnowBrandsAdmin)
admin.site.register(NaverCafeData, NaverCafeDataAdmin)
