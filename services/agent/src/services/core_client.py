"""
HTTP client for Core service API calls.

All Django data access goes through Core's REST APIs.
Agent has no direct database access except for LangGraph checkpointer.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CoreClientError(Exception):
    """Error from Core service API."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class CoreClient:
    """
    HTTP client for all Core service API calls.

    Provides caching for infrequently changing data (authors, brands).
    """

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)

    def _get_cached(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, expires_at = self._cache[key]
            if datetime.now() < expires_at:
                return value
            del self._cache[key]
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        self._cache[key] = (value, datetime.now() + self._cache_ttl)

    # =========================================================================
    # Scraper data (read-only)
    # =========================================================================

    async def get_allowed_authors(self) -> list[str]:
        """
        Get list of active allowed authors for Pinecone filtering.

        Returns:
            List of author names (e.g., ["창플", "팀비즈니스"])

        Cached for 5 minutes.
        """
        cached = self._get_cached("allowed_authors")
        if cached is not None:
            return cached

        try:
            response = await self.client.get("/api/v1/scraper/internal/allowed-authors/")
            response.raise_for_status()
            data = response.json()
            authors = data.get("authors", [])

            # Fallback to default if empty
            if not authors:
                authors = ["창플"]

            self._set_cached("allowed_authors", authors)
            return authors

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get allowed authors: {e}")
            raise CoreClientError(
                f"Failed to get allowed authors: {e.response.text}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error getting allowed authors: {e}")
            # Return default on network error
            return ["창플"]

    async def get_brands(self) -> list[dict]:
        """
        Get list of GoodtoKnow brands for query generation.

        Returns:
            List of dicts with 'name' and 'description' keys.

        Cached for 5 minutes.
        """
        cached = self._get_cached("brands")
        if cached is not None:
            return cached

        try:
            response = await self.client.get("/api/v1/scraper/internal/brands/")
            response.raise_for_status()
            data = response.json()
            brands = data.get("brands", [])

            self._set_cached("brands", brands)
            return brands

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get brands: {e}")
            raise CoreClientError(
                f"Failed to get brands: {e.response.text}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error getting brands: {e}")
            return []

    async def get_brands_formatted(self) -> str:
        """
        Get brands as formatted string for prompts.

        Returns:
            Formatted string like "브랜드1: 설명1\n브랜드2: 설명2"
        """
        brands = await self.get_brands()
        return "\n".join(f"{b['name']}: {b.get('description', '')}" for b in brands)

    async def get_post_content(self, post_id: int) -> dict:
        """
        Get post title and content by post_id.

        Args:
            post_id: The NaverCafeData post_id

        Returns:
            Dict with 'post_id', 'title', 'content', 'url' keys

        Raises:
            CoreClientError: If post not found or API error
        """
        try:
            response = await self.client.get(f"/api/v1/scraper/internal/posts/{post_id}/")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Post {post_id} not found")
                return {"post_id": post_id, "title": "", "content": "", "url": ""}
            logger.error(f"Failed to get post {post_id}: {e}")
            raise CoreClientError(
                f"Failed to get post content: {e.response.text}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error getting post {post_id}: {e}")
            return {"post_id": post_id, "title": "", "content": "", "url": ""}

    # =========================================================================
    # Content (read-only)
    # =========================================================================

    async def get_content_text(self, content_ids: list[int]) -> dict:
        """
        Get text content from NotionContent for chat attachment.

        Args:
            content_ids: List of NotionContent IDs

        Returns:
            Dict with 'contents' list, each containing 'id', 'title', 'text'
        """
        if not content_ids:
            return {"contents": []}

        try:
            response = await self.client.post(
                "/api/v1/content/internal/attachment/",
                json={"content_ids": content_ids},
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get content text: {e}")
            raise CoreClientError(
                f"Failed to get content text: {e.response.text}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error getting content text: {e}")
            return {"contents": []}

    async def get_content_text_formatted(self, content_ids: list[int]) -> str:
        """
        Get content text as formatted string for user_attached_content.

        Args:
            content_ids: List of NotionContent IDs

        Returns:
            Formatted string combining all content texts
        """
        if not content_ids:
            return ""

        data = await self.get_content_text(content_ids)
        texts = []

        for content in data.get("contents", []):
            if content.get("text"):
                title = content.get("title", "")
                text = content["text"]
                if title:
                    texts.append(f"## {title}\n{text}")
                else:
                    texts.append(text)

        return "\n\n---\n\n".join(texts)

    # =========================================================================
    # Chat (write operations)
    # =========================================================================

    async def create_session(self, user_id: int | None = None, nonce: str | None = None) -> dict:
        """
        Create a new chat session.

        Args:
            user_id: Optional user ID
            nonce: Optional session nonce (UUID string)

        Returns:
            Dict with 'id', 'nonce', 'user_id' keys
        """
        payload = {}
        if user_id is not None:
            payload["user_id"] = user_id
        if nonce is not None:
            payload["nonce"] = nonce

        try:
            response = await self.client.post(
                "/api/v1/chat/internal/sessions/",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create session: {e}")
            raise CoreClientError(
                f"Failed to create session: {e.response.text}",
                status_code=e.response.status_code,
            )

    async def get_session(self, nonce: str) -> dict | None:
        """
        Get chat session by nonce.

        Args:
            nonce: Session nonce (UUID string)

        Returns:
            Session data dict or None if not found
        """
        try:
            response = await self.client.get(f"/api/v1/chat/internal/sessions/{nonce}/")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get session {nonce}: {e}")
            raise CoreClientError(
                f"Failed to get session: {e.response.text}",
                status_code=e.response.status_code,
            )

    async def save_messages(
        self,
        session_nonce: str,
        messages: list[dict],
        user_id: int | None = None,
    ) -> dict:
        """
        Bulk save messages after streaming ends.

        Args:
            session_nonce: Session nonce (UUID string)
            messages: List of message dicts with 'role', 'content', etc.
            user_id: Optional user ID

        Returns:
            Response with saved session and messages
        """
        payload = {
            "session_nonce": session_nonce,
            "messages": messages,
        }
        if user_id is not None:
            payload["user_id"] = user_id

        try:
            response = await self.client.post(
                "/api/v1/chat/internal/messages/bulk/",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to save messages: {e}")
            raise CoreClientError(
                f"Failed to save messages: {e.response.text}",
                status_code=e.response.status_code,
            )
