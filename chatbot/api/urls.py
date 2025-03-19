from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("chat-view/", views.chat_view, name="chat_view"),
    path("search/", views.search_documents, name="search_documents"),
    path("index-cafe-data/", views.index_cafe_data, name="index_cafe_data"),
    path("pinecone-stats/", views.get_pinecone_stats, name="get_pinecone_stats"),
    path("chat/", views.chat, name="chat"),
]