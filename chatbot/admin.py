from django.contrib import admin
from .models import Prompt, ABTest

# Register your models here.

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'score', 'num_exposure', 'updated_at', 'description')
    search_fields = ('name', 'content', 'description')
    # list_filter = ('updated_at', 'created_at')

@admin.register(ABTest)
class ABTestAdmin(admin.ModelAdmin):
    list_display = ('query', 'prompt_a', 'prompt_b', 'llm_model', 'winner', 'created_at')
    search_fields = ('query', 'winner')
    # list_filter = ('winner', 'llm_model')
    
    def get_queryset(self, request):
        return super().get_queryset(request)