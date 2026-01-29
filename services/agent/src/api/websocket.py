"""
WebSocket endpoint for real-time chat.

Handles streaming responses from LangGraph with stop_generation support.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.builder import get_app
from src.graph.prompts import STATUS_MESSAGES
from src.main import get_resources
from src.schemas.chat import (
    ErrorMessage,
    GenerationStoppedMessage,
    ServerMessage,
    SessionCreatedMessage,
    SourceDocument,
    StatusUpdateMessage,
    StreamChunkMessage,
    StreamEndMessage,
)
from src.services.core_client import CoreClient
from src.services.redis import RedisService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatHandler:
    """
    Handles a single WebSocket chat session.

    Manages streaming responses, stop_generation, and message persistence.
    """

    def __init__(
        self,
        websocket: WebSocket,
        session_nonce: str,
        core_client: CoreClient,
        redis_service: RedisService,
    ):
        self.websocket = websocket
        self.session_nonce = session_nonce
        self.core_client = core_client
        self.redis_service = redis_service
        self.is_generating = False
        self.current_user_id: int | None = None

    async def send_message(self, message: ServerMessage) -> None:
        """Send a message to the client."""
        await self.websocket.send_json(message.model_dump())

    async def send_status(self, status_key: str) -> None:
        """Send a status update message."""
        message = STATUS_MESSAGES.get(status_key, status_key)
        await self.send_message(StatusUpdateMessage(message=message))

    async def handle_chat_message(
        self,
        content: str,
        content_ids: list[int],
        user_id: int | None,
    ) -> None:
        """
        Handle a chat message from the client.

        Args:
            content: User message content
            content_ids: Optional NotionContent IDs for context
            user_id: Optional user ID
        """
        self.is_generating = True
        self.current_user_id = user_id

        try:
            # Clear any existing stop flag
            await self.redis_service.clear_stop_flag(self.session_nonce)

            # Get user-attached content if content_ids provided
            user_attached_content = None
            if content_ids:
                user_attached_content = await self.core_client.get_content_text_formatted(
                    content_ids
                )

            # Get the LangGraph app
            resources = get_resources()
            app = await get_app(resources["pool"], resources["httpx"])

            # Prepare input
            input_data = {
                "messages": [HumanMessage(content=content)],
            }
            if user_attached_content:
                input_data["user_attached_content"] = user_attached_content

            # Config for checkpointer
            config = {
                "configurable": {
                    "thread_id": self.session_nonce,
                }
            }

            # Send analyzing status
            await self.send_status("analyzing")

            # Stream the graph execution
            full_response = ""
            source_documents = []
            last_node = ""

            async for event in app.astream_events(input_data, config=config, version="v2"):
                # Check for stop flag
                if await self.redis_service.check_stop_flag(self.session_nonce):
                    logger.info(f"Generation stopped for session {self.session_nonce}")
                    await self.send_message(GenerationStoppedMessage())
                    return

                event_type = event.get("event")
                event_name = event.get("name", "")

                # Handle node entry for status updates
                if event_type == "on_chain_start":
                    if event_name == "generate_queries":
                        await self.send_status("generating_queries")
                    elif event_name == "retrieve_documents":
                        await self.send_status("retrieving")
                    elif event_name == "documents_handler":
                        await self.send_status("filtering")
                    elif event_name in ("respond_simple", "respond_with_docs"):
                        await self.send_status("generating")

                # Handle streaming chunks
                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        full_response += chunk.content
                        await self.send_message(StreamChunkMessage(content=chunk.content))

                # Capture source documents from final state
                if event_type == "on_chain_end" and event_name in (
                    "respond_simple",
                    "respond_with_docs",
                ):
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        source_docs = output.get("source_documents", [])
                        if source_docs:
                            source_documents = [
                                SourceDocument(**doc) for doc in source_docs
                            ]

            # Send stream end
            await self.send_message(
                StreamEndMessage(
                    source_documents=source_documents,
                    processed_content=full_response,
                )
            )

            # Save messages to Core service
            messages_to_save = [
                {
                    "role": "user",
                    "content": content,
                    "attached_content_ids": content_ids,
                },
                {
                    "role": "assistant",
                    "content": full_response,
                    "helpful_document_post_ids": [doc.id for doc in source_documents],
                },
            ]

            await self.core_client.save_messages(
                session_nonce=self.session_nonce,
                messages=messages_to_save,
                user_id=user_id,
            )

        except Exception as e:
            logger.exception(f"Error handling chat message: {e}")
            await self.send_message(
                ErrorMessage(message=f"처리 중 오류가 발생했습니다: {str(e)}")
            )

        finally:
            self.is_generating = False

    async def handle_stop_generation(self) -> None:
        """Handle stop generation request."""
        if self.is_generating:
            await self.redis_service.set_stop_flag(self.session_nonce)
            logger.info(f"Stop flag set for session {self.session_nonce}")


@router.websocket("/ws/chat/{nonce}")
async def websocket_chat(websocket: WebSocket, nonce: str):
    """
    WebSocket endpoint for chat.

    Protocol:
    - Client sends: {"type": "message", "content": "...", "content_ids": [], "user_id": 123}
    - Client sends: {"type": "stop_generation"}
    - Server sends: {"type": "session_created", "nonce": "..."}
    - Server sends: {"type": "status_update", "message": "..."}
    - Server sends: {"type": "stream_chunk", "content": "..."}
    - Server sends: {"type": "stream_end", "source_documents": [...], "processed_content": "..."}
    - Server sends: {"type": "generation_stopped"}
    - Server sends: {"type": "error", "message": "..."}
    """
    await websocket.accept()

    # Validate nonce format or generate new one
    try:
        session_nonce = str(uuid.UUID(nonce))
    except ValueError:
        # Generate new nonce if invalid
        session_nonce = str(uuid.uuid4())

    # Get resources
    resources = get_resources()
    core_client = CoreClient(resources["httpx"])
    redis_service = RedisService(resources["redis"])

    # Create handler
    handler = ChatHandler(
        websocket=websocket,
        session_nonce=session_nonce,
        core_client=core_client,
        redis_service=redis_service,
    )

    # Send session created message
    await handler.send_message(SessionCreatedMessage(nonce=session_nonce))

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "message":
                content = data.get("content", "")
                content_ids = data.get("content_ids", [])
                user_id = data.get("user_id")

                if not content.strip():
                    await handler.send_message(
                        ErrorMessage(message="메시지를 입력해주세요.")
                    )
                    continue

                # Handle message (non-blocking to allow stop_generation)
                asyncio.create_task(
                    handler.handle_chat_message(content, content_ids, user_id)
                )

            elif message_type == "stop_generation":
                await handler.handle_stop_generation()

            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_nonce}")

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await handler.send_message(ErrorMessage(message=str(e)))
        except Exception:
            pass
