"""
FastAPI dependency injection for shared resources.

Replaces the global _resources dict pattern with proper Depends().
"""

from typing import Annotated

import httpx
import redis.asyncio as redis
from fastapi import Depends, Request
from psycopg_pool import AsyncConnectionPool

from src.services.core_client import CoreClient
from src.services.redis import RedisService


def get_pool(request: Request) -> AsyncConnectionPool:
    """Get PostgreSQL connection pool from app state."""
    return request.app.state.pool


def get_redis(request: Request) -> redis.Redis:
    """Get Redis client from app state."""
    return request.app.state.redis


def get_httpx(request: Request) -> httpx.AsyncClient:
    """Get httpx client from app state."""
    return request.app.state.httpx


def get_core_client(httpx_client: Annotated[httpx.AsyncClient, Depends(get_httpx)]) -> CoreClient:
    """Get CoreClient instance."""
    return CoreClient(httpx_client)


def get_redis_service(redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> RedisService:
    """Get RedisService instance."""
    return RedisService(redis_client)


# Type aliases for cleaner endpoint signatures
Pool = Annotated[AsyncConnectionPool, Depends(get_pool)]
Redis = Annotated[redis.Redis, Depends(get_redis)]
HttpxClient = Annotated[httpx.AsyncClient, Depends(get_httpx)]
Core = Annotated[CoreClient, Depends(get_core_client)]
RedisServiceDep = Annotated[RedisService, Depends(get_redis_service)]
