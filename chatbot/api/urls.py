from django.urls import path, include
from . import views

app_name = 'chatbot'

urlpatterns = [
    path("", views.index, name="index"),
    path("chat-view/", views.chat_view, name="chat_view"),
    path("search/", views.search_documents, name="search_documents"),
    path("index-cafe-data/", views.index_cafe_data, name="index_cafe_data"),
    path("pinecone-stats/", views.get_pinecone_stats, name="get_pinecone_stats"),
    path("chat/", views.chat, name="chat"),
    path('ab-test/', views.ab_test_view, name='ab_test'),
    path('run-ab-test/', views.run_ab_test, name='run_ab_test'),
    path('vote-ab-test/', views.vote_ab_test, name='vote_ab_test'),
    path('create-prompt/', views.create_prompt, name='create_prompt'),
    path('update-prompt/<str:prompt_id>/', views.update_prompt, name='update_prompt'),
    path('delete-prompt/<str:prompt_id>/', views.delete_prompt, name='delete_prompt'),
]