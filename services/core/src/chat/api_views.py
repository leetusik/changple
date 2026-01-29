"""
API views for chat app.

Note: Real-time chat is handled by the Agent service.
These views manage chat history and provide internal APIs for Agent.
"""

import logging
import uuid

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from src.chat.models import ChatMessage, ChatSession
from src.chat.serializers import (
    BulkCreateMessagesSerializer,
    ChatMessageSerializer,
    ChatSessionDetailSerializer,
    ChatSessionSerializer,
    CreateChatMessageSerializer,
    CreateChatSessionSerializer,
)
from src.common.pagination import StandardResultsSetPagination
from src.scraper.models import NaverCafeData
from src.users.models import User

logger = logging.getLogger(__name__)


class ChatHistoryListView(APIView):
    """
    Get user's chat session history.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Return paginated list of user's chat sessions."""
        queryset = ChatSession.objects.filter(user=request.user).order_by("-updated_at")

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = ChatSessionSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ChatSessionSerializer(queryset, many=True)
        return Response(serializer.data)


class ChatSessionMessagesView(APIView):
    """
    Get messages in a chat session.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, nonce):
        """Return all messages in a chat session."""
        try:
            nonce_uuid = uuid.UUID(str(nonce))
        except ValueError:
            return Response(
                {"error": "유효하지 않은 세션 ID입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = ChatSession.objects.get(nonce=nonce_uuid, user=request.user)
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "채팅 세션을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ChatSessionDetailSerializer(session)
        return Response(serializer.data)


class DeleteChatSessionView(APIView):
    """
    Delete a chat session.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, nonce):
        """Delete a chat session and all its messages."""
        try:
            nonce_uuid = uuid.UUID(str(nonce))
        except ValueError:
            return Response(
                {"error": "유효하지 않은 세션 ID입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = ChatSession.objects.get(nonce=nonce_uuid, user=request.user)
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "채팅 세션을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        session.delete()
        return Response(
            {"message": "채팅 세션이 삭제되었습니다."},
            status=status.HTTP_200_OK,
        )


# ============================================================================
# Internal APIs for Agent Service
# ============================================================================


class InternalCreateSessionView(APIView):
    """
    Create a chat session (called by Agent service).

    This is an internal API - no user authentication required.
    Agent service should use service-to-service auth in production.
    """

    permission_classes = [AllowAny]  # TODO: Add service auth

    def post(self, request):
        """Create a new chat session."""
        serializer = CreateChatSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = None

        # Get user if user_id provided
        if data.get("user_id"):
            try:
                user = User.objects.get(id=data["user_id"])
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Create session with provided nonce or generate new one
        session = ChatSession.objects.create(
            user=user,
            nonce=data.get("nonce", uuid.uuid4()),
        )

        return Response(
            {
                "id": session.id,
                "nonce": str(session.nonce),
                "user_id": session.user_id,
            },
            status=status.HTTP_201_CREATED,
        )


class InternalCreateMessageView(APIView):
    """
    Create a chat message (called by Agent service).

    This is an internal API for saving messages after streaming ends.
    """

    permission_classes = [AllowAny]  # TODO: Add service auth

    def post(self, request):
        """Create a new chat message."""
        serializer = CreateChatMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get or create session
        try:
            session = ChatSession.objects.get(nonce=data["session_nonce"])
        except ChatSession.DoesNotExist:
            # Create new session if it doesn't exist
            session = ChatSession.objects.create(nonce=data["session_nonce"])

        # Create message
        message = ChatMessage.objects.create(
            session=session,
            role=data["role"],
            content=data["content"],
            attached_content_ids=data.get("attached_content_ids", []),
        )

        # Add helpful documents if provided
        if data.get("helpful_document_post_ids"):
            docs = NaverCafeData.objects.filter(
                post_id__in=data["helpful_document_post_ids"]
            )
            message.helpful_documents.set(docs)

        return Response(
            ChatMessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


class InternalBulkCreateMessagesView(APIView):
    """
    Bulk create messages (called by Agent service after streaming ends).

    This is the main endpoint for saving a complete conversation turn.
    Creates/updates session and saves both user and assistant messages.
    """

    permission_classes = [AllowAny]  # TODO: Add service auth

    def post(self, request):
        """Bulk create messages for a session."""
        serializer = BulkCreateMessagesSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        with transaction.atomic():
            # Get or create session
            session, created = ChatSession.objects.get_or_create(
                nonce=data["session_nonce"],
                defaults={"user_id": data.get("user_id")},
            )

            # Update user if provided and session was existing without user
            if not created and data.get("user_id") and not session.user_id:
                session.user_id = data["user_id"]
                session.save(update_fields=["user_id"])

            created_messages = []

            for msg_data in data["messages"]:
                message = ChatMessage.objects.create(
                    session=session,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    attached_content_ids=msg_data.get("attached_content_ids", []),
                )

                # Add helpful documents for assistant messages
                if msg_data.get("helpful_document_post_ids"):
                    docs = NaverCafeData.objects.filter(
                        post_id__in=msg_data["helpful_document_post_ids"]
                    )
                    message.helpful_documents.set(docs)

                created_messages.append(message)

            # Touch session to update updated_at
            session.save()

        return Response(
            {
                "session": {
                    "id": session.id,
                    "nonce": str(session.nonce),
                    "user_id": session.user_id,
                },
                "messages": ChatMessageSerializer(created_messages, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class InternalGetSessionView(APIView):
    """
    Get session by nonce (called by Agent service).
    """

    permission_classes = [AllowAny]  # TODO: Add service auth

    def get(self, request, nonce):
        """Get session with messages by nonce."""
        try:
            nonce_uuid = uuid.UUID(str(nonce))
        except ValueError:
            return Response(
                {"error": "Invalid session nonce"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = ChatSession.objects.get(nonce=nonce_uuid)
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(ChatSessionDetailSerializer(session).data)
