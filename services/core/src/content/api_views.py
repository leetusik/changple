"""
API views for content app.
"""

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from src.common.pagination import StandardResultsSetPagination
from src.content.models import ContentViewHistory, NotionContent
from src.content.serializers import (
    ContentTextSerializer,
    ContentViewHistorySerializer,
    NotionContentDetailSerializer,
    NotionContentListSerializer,
    RecordViewSerializer,
)
from src.content.utils import extract_text_from_notion_content

logger = logging.getLogger(__name__)


class ContentListView(APIView):
    """
    List all content (columns).
    """

    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Return paginated list of all content."""
        queryset = NotionContent.objects.all().order_by("-uploaded_at")

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = NotionContentListSerializer(
                page, many=True, context={"request": request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = NotionContentListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class PreferredContentListView(APIView):
    """
    List preferred/featured content.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Return list of preferred content."""
        queryset = NotionContent.objects.filter(is_preferred=True).order_by(
            "-uploaded_at"
        )
        serializer = NotionContentListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class ContentDetailView(APIView):
    """
    Get content detail by ID.
    """

    permission_classes = [AllowAny]

    def get(self, request, pk):
        """Return content detail."""
        try:
            content = NotionContent.objects.get(pk=pk)
        except NotionContent.DoesNotExist:
            return Response(
                {"error": "콘텐츠를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = NotionContentDetailSerializer(content, context={"request": request})
        return Response(serializer.data)


class RecommendedContentView(APIView):
    """
    Get recommended content based on a specific content.
    """

    permission_classes = [AllowAny]

    def get(self, request, pk):
        """Return recommended content (excluding the specified content)."""
        try:
            content = NotionContent.objects.get(pk=pk)
        except NotionContent.DoesNotExist:
            return Response(
                {"error": "콘텐츠를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get random content excluding the current one
        recommended = NotionContent.objects.exclude(pk=pk).order_by("?")[:4]
        serializer = NotionContentListSerializer(
            recommended, many=True, context={"request": request}
        )
        return Response(serializer.data)


class ContentViewHistoryListView(APIView):
    """
    Get user's content view history.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Return user's content view history."""
        queryset = ContentViewHistory.objects.filter(user=request.user).order_by(
            "-viewed_at"
        )

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = ContentViewHistorySerializer(
                page, many=True, context={"request": request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = ContentViewHistorySerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class RecordContentViewView(APIView):
    """
    Record a content view.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Record that user viewed a content."""
        serializer = RecordViewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        content_id = serializer.validated_data["content_id"]

        try:
            content = NotionContent.objects.get(pk=content_id)
        except NotionContent.DoesNotExist:
            return Response(
                {"error": "콘텐츠를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create view history record
        ContentViewHistory.objects.create(user=request.user, content=content)

        return Response(
            {"message": "조회 기록이 저장되었습니다."},
            status=status.HTTP_201_CREATED,
        )


class ContentAttachmentTextView(APIView):
    """
    Get text content from NotionContent for chat attachment.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Extract text from specified content IDs."""
        serializer = ContentTextSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        content_ids = serializer.validated_data["content_ids"]
        results = []

        for content_id in content_ids:
            try:
                text = extract_text_from_notion_content(content_id)
                content = NotionContent.objects.get(pk=content_id)
                results.append(
                    {
                        "id": content_id,
                        "title": content.title,
                        "text": text,
                    }
                )
            except NotionContent.DoesNotExist:
                results.append(
                    {
                        "id": content_id,
                        "title": None,
                        "text": None,
                        "error": "콘텐츠를 찾을 수 없습니다.",
                    }
                )
            except Exception as e:
                logger.error(f"Error extracting text from content {content_id}: {e}")
                results.append(
                    {
                        "id": content_id,
                        "title": None,
                        "text": None,
                        "error": str(e),
                    }
                )

        return Response({"contents": results})
