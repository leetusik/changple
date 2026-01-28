"""
Serializers for scraper app.
"""

from rest_framework import serializers

from src.scraper.models import AllowedAuthor, BatchJob, NaverCafeData, PostStatus


class NaverCafeDataSerializer(serializers.ModelSerializer):
    """Serializer for NaverCafeData."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = NaverCafeData
        fields = [
            "id",
            "post_id",
            "title",
            "category",
            "author",
            "published_date",
            "summary",
            "keywords",
            "ingested",
            "url",
            "created_at",
        ]

    def get_url(self, obj) -> str:
        return obj.get_url()


class NaverCafeDataDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for NaverCafeData."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = NaverCafeData
        fields = [
            "id",
            "post_id",
            "title",
            "category",
            "content",
            "author",
            "published_date",
            "notation",
            "keywords",
            "summary",
            "possible_questions",
            "ingested",
            "url",
            "created_at",
            "updated_at",
        ]

    def get_url(self, obj) -> str:
        return obj.get_url()


class PostStatusSerializer(serializers.ModelSerializer):
    """Serializer for PostStatus."""

    class Meta:
        model = PostStatus
        fields = ["id", "post_id", "status", "error_message", "created_at"]


class AllowedAuthorSerializer(serializers.ModelSerializer):
    """Serializer for AllowedAuthor."""

    class Meta:
        model = AllowedAuthor
        fields = ["id", "name", "author_group", "is_active"]


class BatchJobSerializer(serializers.ModelSerializer):
    """Serializer for BatchJob."""

    class Meta:
        model = BatchJob
        fields = [
            "id",
            "job_type",
            "provider",
            "job_id",
            "status",
            "post_ids",
            "error_message",
            "submitted_at",
            "completed_at",
            "created_at",
        ]


class ScraperRunSerializer(serializers.Serializer):
    """Serializer for triggering scraper."""

    start_id = serializers.IntegerField(required=False, default=None)
    end_id = serializers.IntegerField(required=False, default=None)
    batch_size = serializers.IntegerField(required=False, default=100)
    force_update = serializers.BooleanField(required=False, default=False)


class IngestRunSerializer(serializers.Serializer):
    """Serializer for triggering ingestion."""

    use_batch_api = serializers.BooleanField(required=False, default=True)
    batch_size = serializers.IntegerField(required=False, default=100)
