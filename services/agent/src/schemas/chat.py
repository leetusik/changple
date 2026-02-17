"""
Pydantic schemas for chat messages (SSE events).
"""

from typing import Optional

from pydantic import BaseModel, Field

# =============================================================================
# Client → Agent Request
# =============================================================================


class ChatSendRequest(BaseModel):
    """Request body for sending a chat message."""

    content: str
    content_ids: list[int] = Field(default_factory=list)
    user_id: Optional[int] = None


# =============================================================================
# SSE Event Models
# =============================================================================


class SourceDocument(BaseModel):
    """Source document metadata."""

    id: int
    title: str
    source: str


class SSEStatusData(BaseModel):
    """Data for status SSE event."""

    message: str


class SSEChunkData(BaseModel):
    """Data for chunk SSE event."""

    content: str


class SSEEndData(BaseModel):
    """Data for end SSE event."""

    source_documents: list[SourceDocument] = Field(default_factory=list)
    processed_content: str = ""


class SSEStoppedData(BaseModel):
    """Data for stopped SSE event."""

    message: str = "생성이 중단되었습니다"


class SSEErrorData(BaseModel):
    """Data for error SSE event."""

    message: str
    code: Optional[str] = None
