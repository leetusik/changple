from django.contrib import admin

from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("recipient", "subject", "status", "sent_at", "created_at")
    list_filter = ("status",)
    search_fields = ("recipient", "subject", "status_message")
    readonly_fields = (
        "recipient",
        "subject",
        "status",
        "status_message",
        "sent_at",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
