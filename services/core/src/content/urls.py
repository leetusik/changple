"""
URL patterns for content API.
"""

from django.urls import path

from src.content.api_views import (
    ContentAttachmentTextView,
    ContentDetailView,
    ContentListView,
    ContentViewHistoryListView,
    InternalContentAttachmentTextView,
    PreferredContentListView,
    RecommendedContentView,
    RecordContentViewView,
)

urlpatterns = [
    path("columns/", ContentListView.as_view(), name="content-list"),
    path("preferred/", PreferredContentListView.as_view(), name="content-preferred"),
    path("<int:pk>/", ContentDetailView.as_view(), name="content-detail"),
    path(
        "recommended/<int:pk>/",
        RecommendedContentView.as_view(),
        name="content-recommended",
    ),
    path("history/", ContentViewHistoryListView.as_view(), name="content-history"),
    path("view/", RecordContentViewView.as_view(), name="content-record-view"),
    path("attachment/", ContentAttachmentTextView.as_view(), name="content-attachment"),
    # Internal endpoint for Agent service
    path("internal/attachment/", InternalContentAttachmentTextView.as_view(), name="content-internal-attachment"),
]
