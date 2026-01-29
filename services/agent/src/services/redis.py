"""
Redis service for stop_generation flags.

Uses redis.asyncio for async operations.
"""

import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Key prefix for stop flags
STOP_FLAG_PREFIX = "agent:stop:"
STOP_FLAG_TTL = 300  # 5 minutes TTL


class RedisService:
    """Redis service for managing stop_generation flags."""

    def __init__(self, client: redis.Redis):
        self.client = client

    def _stop_key(self, session_nonce: str) -> str:
        """Get Redis key for stop flag."""
        return f"{STOP_FLAG_PREFIX}{session_nonce}"

    async def set_stop_flag(self, session_nonce: str) -> None:
        """
        Set stop generation flag for a session.

        Args:
            session_nonce: The chat session nonce
        """
        key = self._stop_key(session_nonce)
        await self.client.setex(key, STOP_FLAG_TTL, "1")
        logger.info(f"Set stop flag for session {session_nonce}")

    async def check_stop_flag(self, session_nonce: str) -> bool:
        """
        Check if stop generation flag is set.

        Args:
            session_nonce: The chat session nonce

        Returns:
            True if stop flag is set
        """
        key = self._stop_key(session_nonce)
        return await self.client.exists(key) > 0

    async def clear_stop_flag(self, session_nonce: str) -> None:
        """
        Clear stop generation flag for a session.

        Args:
            session_nonce: The chat session nonce
        """
        key = self._stop_key(session_nonce)
        await self.client.delete(key)
        logger.debug(f"Cleared stop flag for session {session_nonce}")

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return await self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
