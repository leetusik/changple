from django.contrib import admin
from .models import NotionContent

@admin.register(NotionContent)
class NotionContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'id', 'description', 'uploaded_at', 'updated_at')
    # zip_file 필드는 저장 후 비워지므로 readonly_fields에 entry_html_path 추가
    readonly_fields = ('html_path', 'contents_img_path', 'uploaded_at', 'updated_at')

    def delete_queryset(self, request, queryset):
        """
        일괄 삭제(action) 시에도 각 객체의 delete() 메소드가 호출되도록 오버라이드합니다.
        이를 통해 파일 시스템의 파일들도 함께 삭제됩니다.
        """
        for obj in queryset:
            obj.delete()
