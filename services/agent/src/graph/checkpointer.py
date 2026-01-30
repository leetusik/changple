"""
PostgreSQL checkpointer for LangGraph with connection pooling.

Ported from changple2/chatbot/bot.py.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import psycopg
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


class PooledAsyncPostgresSaver(AsyncPostgresSaver):
    """
    Custom PostgreSQL checkpointer using connection pooling.

    Extends AsyncPostgresSaver to work with a connection pool instead of
    individual connections, improving performance and resource management.
    """

    def __init__(self, pool: AsyncConnectionPool):
        """Initialize with connection pool."""
        BaseCheckpointSaver.__init__(self, serde=None)
        self.pool = pool
        self.conn = None
        self.pipe = None

    @asynccontextmanager
    async def _cursor(self, **kwargs) -> AsyncIterator["psycopg.AsyncCursor"]:
        """
        Provide database cursor from connection pool.

        Args:
            **kwargs: Additional keyword arguments for cursor configuration

        Yields:
            Configured database cursor
        """
        async with self.pool.connection(timeout=300) as conn:
            async with conn.cursor(binary=True, row_factory=dict_row) as cur:
                yield cur


async def setup_checkpointer(pool: AsyncConnectionPool) -> None:
    """
    Set up LangGraph checkpoint tables in the database.

    This should be called on application startup to ensure tables exist.

    Args:
        pool: AsyncConnectionPool instance
    """
    # Get a connection and run setup with autocommit to allow CREATE INDEX CONCURRENTLY
    async with pool.connection() as conn:
        # Set autocommit mode for DDL statements like CREATE INDEX CONCURRENTLY
        await conn.set_autocommit(True)
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()
    logger.info("LangGraph checkpointer tables created/verified")


async def get_checkpointer(pool: AsyncConnectionPool) -> PooledAsyncPostgresSaver:
    """
    Get a checkpointer instance.

    Args:
        pool: AsyncConnectionPool instance

    Returns:
        Configured PooledAsyncPostgresSaver
    """
    return PooledAsyncPostgresSaver(pool)
