from django.contrib import admin

from scraper.models import NaverCafeData


class NaverCafeDataAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "published_date", "url", "post_id")
    list_filter = ("author", "published_date")
    search_fields = ("title", "content")
    list_per_page = 20


admin.site.register(NaverCafeData, NaverCafeDataAdmin)
