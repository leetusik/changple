"""
API views for scraper app.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from src.common.pagination import StandardResultsSetPagination
from src.scraper.models import AllowedAuthor, BatchJob, NaverCafeData, PostStatus
from src.scraper.serializers import (
    AllowedAuthorSerializer,
    BatchJobSerializer,
    IngestRunSerializer,
    NaverCafeDataDetailSerializer,
    NaverCafeDataSerializer,
    PostStatusSerializer,
    ScraperRunSerializer,
)
from src.scraper.tasks import (
    full_rescan_task,
    ingest_docs_task,
    scheduled_scraping_task,
    submit_batch_jobs_task,
)

logger = logging.getLogger(__name__)


class ScraperRunView(APIView):
    """
    Trigger scraper task.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Trigger scraping task."""
        serializer = ScraperRunSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        if data.get("start_id") or data.get("end_id"):
            # Full rescan
            task = full_rescan_task.delay(
                start_id=data.get("start_id", 1),
                end_id=data.get("end_id"),
                batch_size=data.get("batch_size", 100),
                force_update=data.get("force_update", False),
            )
            return Response(
                {
                    "message": "Full rescan task started",
                    "task_id": task.id,
                }
            )
        else:
            # Scheduled scraping
            task = scheduled_scraping_task.delay(
                batch_size=data.get("batch_size", 100),
            )
            return Response(
                {
                    "message": "Scheduled scraping task started",
                    "task_id": task.id,
                }
            )


class IngestRunView(APIView):
    """
    Trigger document ingestion.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Trigger ingestion task."""
        serializer = IngestRunSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        use_batch_api = data.get("use_batch_api", True)

        if use_batch_api:
            # Use batch API for 50% cost savings
            task = submit_batch_jobs_task.delay(
                batch_size=data.get("batch_size", 100),
                use_batch_api=True,
            )
            return Response(
                {
                    "message": "Batch ingestion task started (50% cost savings)",
                    "task_id": task.id,
                }
            )
        else:
            # Use regular ingestion
            task = ingest_docs_task.delay()
            return Response(
                {
                    "message": "Regular ingestion task started",
                    "task_id": task.id,
                }
            )


class ScraperStatusView(APIView):
    """
    Get scraper status and statistics.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return scraper status."""
        total_posts = NaverCafeData.objects.count()
        ingested_posts = NaverCafeData.objects.filter(ingested=True).count()
        pending_posts = NaverCafeData.objects.filter(ingested=False).count()

        status_counts = {
            "SAVED": PostStatus.objects.filter(status="SAVED").count(),
            "DELETED": PostStatus.objects.filter(status="DELETED").count(),
            "ERROR": PostStatus.objects.filter(status="ERROR").count(),
        }

        # Get recent batch jobs
        recent_batch_jobs = BatchJob.objects.order_by("-created_at")[:5]
        batch_job_data = BatchJobSerializer(recent_batch_jobs, many=True).data

        return Response(
            {
                "total_posts": total_posts,
                "ingested_posts": ingested_posts,
                "pending_posts": pending_posts,
                "post_status_counts": status_counts,
                "recent_batch_jobs": batch_job_data,
            }
        )


class NaverCafeDataListView(APIView):
    """
    List NaverCafeData with pagination.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Return paginated list of NaverCafeData."""
        queryset = NaverCafeData.objects.all().order_by("-published_date")

        # Filter by ingested status
        ingested = request.query_params.get("ingested")
        if ingested is not None:
            queryset = queryset.filter(ingested=ingested.lower() == "true")

        # Filter by author
        author = request.query_params.get("author")
        if author:
            queryset = queryset.filter(author=author)

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = NaverCafeDataSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = NaverCafeDataSerializer(queryset, many=True)
        return Response(serializer.data)


class NaverCafeDataDetailView(APIView):
    """
    Get NaverCafeData detail by post_id.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        """Return NaverCafeData detail."""
        try:
            data = NaverCafeData.objects.get(post_id=post_id)
        except NaverCafeData.DoesNotExist:
            return Response(
                {"error": "게시글을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = NaverCafeDataDetailSerializer(data)
        return Response(serializer.data)


class AllowedAuthorListView(APIView):
    """
    List allowed authors.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return list of allowed authors."""
        queryset = AllowedAuthor.objects.all()
        serializer = AllowedAuthorSerializer(queryset, many=True)
        return Response(serializer.data)


class BatchJobListView(APIView):
    """
    List batch jobs.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Return paginated list of batch jobs."""
        queryset = BatchJob.objects.all().order_by("-created_at")

        # Filter by status
        job_status = request.query_params.get("status")
        if job_status:
            queryset = queryset.filter(status=job_status)

        # Filter by type
        job_type = request.query_params.get("type")
        if job_type:
            queryset = queryset.filter(job_type=job_type)

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = BatchJobSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = BatchJobSerializer(queryset, many=True)
        return Response(serializer.data)


# ============================================================================
# Internal APIs for Agent Service
# ============================================================================


class InternalAllowedAuthorsView(APIView):
    """
    Get list of active allowed authors (for Agent service).

    Returns author names for Pinecone vector store filtering.
    """

    permission_classes = []  # TODO: Add service auth

    def get(self, request):
        """Return list of active author names."""
        authors = list(
            AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
        )
        return Response({"authors": authors})


class InternalBrandsView(APIView):
    """
    Get list of GoodtoKnow brands (for Agent service).

    Returns brand names and descriptions for query generation prompts.
    """

    permission_classes = []  # TODO: Add service auth

    def get(self, request):
        """Return list of brands with descriptions."""
        from src.scraper.models import GoodtoKnowBrands

        brands = GoodtoKnowBrands.objects.filter(is_goodto_know=True).values(
            "name", "description"
        )
        return Response({"brands": list(brands)})


class InternalPostContentView(APIView):
    """
    Get post content by post_id (for Agent service).

    Returns original post title and content for document retrieval.
    """

    permission_classes = []  # TODO: Add service auth

    def get(self, request, post_id):
        """Return post title and content."""
        try:
            post = NaverCafeData.objects.get(post_id=post_id)
            return Response(
                {
                    "post_id": post.post_id,
                    "title": post.title,
                    "content": post.content,
                    "url": post.get_url(),
                }
            )
        except NaverCafeData.DoesNotExist:
            return Response(
                {"error": "게시글을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
