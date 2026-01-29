"""
URL patterns for scraper API.
"""

from django.urls import path

from src.scraper.api_views import (
    AllowedAuthorListView,
    BatchJobListView,
    IngestRunView,
    InternalAllowedAuthorsView,
    InternalBrandsView,
    InternalPostContentView,
    NaverCafeDataDetailView,
    NaverCafeDataListView,
    ScraperRunView,
    ScraperStatusView,
)

urlpatterns = [
    # Control endpoints (admin only)
    path("run/", ScraperRunView.as_view(), name="scraper-run"),
    path("ingest/", IngestRunView.as_view(), name="scraper-ingest"),
    # Status
    path("status/", ScraperStatusView.as_view(), name="scraper-status"),
    # Data endpoints
    path("posts/", NaverCafeDataListView.as_view(), name="scraper-posts"),
    path("posts/<int:post_id>/", NaverCafeDataDetailView.as_view(), name="scraper-post-detail"),
    path("authors/", AllowedAuthorListView.as_view(), name="scraper-authors"),
    path("batch-jobs/", BatchJobListView.as_view(), name="scraper-batch-jobs"),
    # Internal endpoints for Agent service
    path("internal/allowed-authors/", InternalAllowedAuthorsView.as_view(), name="scraper-internal-allowed-authors"),
    path("internal/brands/", InternalBrandsView.as_view(), name="scraper-internal-brands"),
    path("internal/posts/<int:post_id>/", InternalPostContentView.as_view(), name="scraper-internal-post-content"),
]
