"""
URL patterns for chat API.
"""

from django.urls import path

from src.chat.api_views import (
    ChatHistoryListView,
    ChatSessionMessagesView,
    DeleteChatSessionView,
    InternalBulkCreateMessagesView,
    InternalCreateMessageView,
    InternalCreateSessionView,
    InternalGetSessionView,
)

urlpatterns = [
    # User-facing endpoints (require authentication)
    path("history/", ChatHistoryListView.as_view(), name="chat-history"),
    path("<str:nonce>/messages/", ChatSessionMessagesView.as_view(), name="chat-messages"),
    path("<str:nonce>/", DeleteChatSessionView.as_view(), name="chat-delete"),

    # Internal endpoints for Agent service
    path("internal/sessions/", InternalCreateSessionView.as_view(), name="chat-internal-create-session"),
    path("internal/sessions/<str:nonce>/", InternalGetSessionView.as_view(), name="chat-internal-get-session"),
    path("internal/messages/", InternalCreateMessageView.as_view(), name="chat-internal-create-message"),
    path("internal/messages/bulk/", InternalBulkCreateMessagesView.as_view(), name="chat-internal-bulk-messages"),
]
