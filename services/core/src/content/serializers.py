"""
Serializers for content app.
"""

from rest_framework import serializers

from src.content.models import ContentViewHistory, NotionContent


class NotionContentListSerializer(serializers.ModelSerializer):
    """Serializer for NotionContent list view."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = NotionContent
        fields = [
            "id",
            "title",
            "description",
            "thumbnail_url",
            "is_preferred",
            "uploaded_at",
        ]

    def get_thumbnail_url(self, obj) -> str | None:
        """Return relative URL for thumbnail (proxied by Next.js)."""
        if obj.thumbnail_img_path:
            return obj.thumbnail_img_path.url
        return None


class NotionContentDetailSerializer(serializers.ModelSerializer):
    """Serializer for NotionContent detail view."""

    thumbnail_url = serializers.SerializerMethodField()
    html_url = serializers.SerializerMethodField()

    class Meta:
        model = NotionContent
        fields = [
            "id",
            "title",
            "description",
            "thumbnail_url",
            "html_url",
            "is_preferred",
            "uploaded_at",
            "updated_at",
        ]

    def get_thumbnail_url(self, obj) -> str | None:
        """Return relative URL for thumbnail (proxied by Next.js)."""
        if obj.thumbnail_img_path:
            return obj.thumbnail_img_path.url
        return None

    def get_html_url(self, obj) -> str | None:
        """Return relative URL for HTML content (proxied by Next.js)."""
        if obj.html_path:
            return obj.get_html_url()
        return None


class ContentViewHistorySerializer(serializers.ModelSerializer):
    """Serializer for ContentViewHistory."""

    content = NotionContentListSerializer(read_only=True)

    class Meta:
        model = ContentViewHistory
        fields = ["id", "content", "viewed_at"]


class RecordViewSerializer(serializers.Serializer):
    """Serializer for recording content view."""

    content_id = serializers.IntegerField()


class ContentTextSerializer(serializers.Serializer):
    """Serializer for getting content text."""

    content_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=10,
    )
