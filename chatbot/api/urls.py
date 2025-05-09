from django.urls import include, path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("", views.index, name="index"),
    # Chat URLs:
    # - The plain /chat/ URL will create a new session or handle message submission
    # - The /chat/<uuid>/ URL will use an existing session
    path("chat/", views.chat_view, name="chat_view_with_no_nonce"),
    path("chat/<str:session_nonce>/", views.chat_view, name="chat_view_with_nonce"),
    # API endpoints
    path("api/chat/", views.chat, name="chat_api"),
    path("api/rating/", views.Rating.as_view(), name="rating_api"),
]
