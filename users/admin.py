from django.contrib import admin

from .models import NaverUserProfile


class NaverUserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "nickname",
        "naver_id",
        "is_premium",
        "daily_query_limit",
        "daily_queries_used",
    )
    list_filter = ("is_premium",)
    search_fields = ("nickname", "naver_id")

    fieldsets = (
        (None, {"fields": ("user", "naver_id", "nickname")}),
        ("Personal info", {"fields": ("profile_image", "gender", "age", "birthday")}),
        (
            "Query Usage",
            {"fields": ("daily_query_limit", "daily_queries_used", "last_query_reset")},
        ),
        ("Premium Status", {"fields": ("is_premium", "premium_until")}),
    )


admin.site.register(NaverUserProfile, NaverUserProfileAdmin)
