"""
Pydantic schemas for WebSocket chat messages.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Client → Agent Messages
# =============================================================================


class ClientMessage(BaseModel):
    """Base message from client."""

    type: str


class ChatMessage(ClientMessage):
    """Chat message from client."""

    type: Literal["message"] = "message"
    content: str
    content_ids: list[int] = Field(default_factory=list)
    user_id: Optional[int] = None


class StopGenerationMessage(ClientMessage):
    """Stop generation request from client."""

    type: Literal["stop_generation"] = "stop_generation"


# =============================================================================
# Agent → Client Messages
# =============================================================================


class ServerMessage(BaseModel):
    """Base message to client."""

    type: str


class SessionCreatedMessage(ServerMessage):
    """Session created notification."""

    type: Literal["session_created"] = "session_created"
    nonce: str


class StatusUpdateMessage(ServerMessage):
    """Status update during processing."""

    type: Literal["status_update"] = "status_update"
    message: str


class StreamChunkMessage(ServerMessage):
    """Streaming chunk of response."""

    type: Literal["stream_chunk"] = "stream_chunk"
    content: str


class SourceDocument(BaseModel):
    """Source document metadata."""

    id: int
    title: str
    source: str


class StreamEndMessage(ServerMessage):
    """End of streaming response."""

    type: Literal["stream_end"] = "stream_end"
    source_documents: list[SourceDocument] = Field(default_factory=list)
    processed_content: str = ""


class GenerationStoppedMessage(ServerMessage):
    """Generation was stopped by user."""

    type: Literal["generation_stopped"] = "generation_stopped"


class ErrorMessage(ServerMessage):
    """Error message."""

    type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None
