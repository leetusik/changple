from django.contrib import admin
from .models import Prompt, ABTest

# Register your models here.

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('prompt_id', 'name', 'score', 'num_exposure', 'updated_at')
    search_fields = ('prompt_id', 'name', 'content', 'description')
    list_filter = ('prompt_id',)

@admin.register(ABTest)
class ABTestAdmin(admin.ModelAdmin):
    list_display = ('query', 'prompt_a', 'prompt_b', 'llm_model', 'winner', 'created_at')
    search_fields = ('query',)
    list_filter = ('winner', 'llm_model')
    
    def get_queryset(self, request):
        return super().get_queryset(request)