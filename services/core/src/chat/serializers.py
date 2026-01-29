"""
Serializers for chat app.
"""

from rest_framework import serializers

from src.chat.models import ChatMessage, ChatSession


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage."""

    helpful_document_ids = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "role",
            "content",
            "attached_content_ids",
            "helpful_document_ids",
            "created_at",
        ]

    def get_helpful_document_ids(self, obj) -> list[int]:
        return list(obj.helpful_documents.values_list("post_id", flat=True))


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for ChatSession list view."""

    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "nonce",
            "message_count",
            "last_message",
            "created_at",
            "updated_at",
        ]

    def get_message_count(self, obj) -> int:
        return obj.messages.count()

    def get_last_message(self, obj) -> str | None:
        last = obj.messages.order_by("-created_at").first()
        if last:
            return last.content[:100]
        return None


class ChatSessionDetailSerializer(serializers.ModelSerializer):
    """Serializer for ChatSession detail view with messages."""

    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "nonce",
            "messages",
            "created_at",
            "updated_at",
        ]


# ============================================================================
# Serializers for Agent Service (internal API)
# ============================================================================


class CreateChatSessionSerializer(serializers.Serializer):
    """Serializer for creating a chat session from Agent service."""

    user_id = serializers.IntegerField(required=False, allow_null=True)
    nonce = serializers.UUIDField(required=False)


class CreateChatMessageSerializer(serializers.Serializer):
    """Serializer for creating a chat message from Agent service."""

    session_nonce = serializers.UUIDField()
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField()
    attached_content_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )
    helpful_document_post_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )


class BulkCreateMessagesSerializer(serializers.Serializer):
    """Serializer for bulk creating messages (user + assistant pair)."""

    session_nonce = serializers.UUIDField()
    user_id = serializers.IntegerField(required=False, allow_null=True)
    messages = serializers.ListField(
        child=CreateChatMessageSerializer(),
        min_length=1,
    )
