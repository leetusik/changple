"""
FastAPI application for Changple Agent Service.
"""

import logging
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from src.api.router import api_router
from src.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global resources
_resources: dict = {}


def get_resources() -> dict:
    """Get global resources (pool, redis, httpx client)."""
    return _resources


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Initializes and cleans up:
    - PostgreSQL connection pool (for LangGraph checkpointer)
    - Redis client (for stop_generation flags)
    - httpx client (for Core API calls)
    """
    settings = get_settings()
    logger.info("Starting Changple Agent Service...")

    # Initialize PostgreSQL pool for LangGraph checkpointer
    logger.info("Initializing PostgreSQL connection pool...")
    pool = AsyncConnectionPool(
        settings.langgraph_database_url,
        min_size=2,
        max_size=20,
        timeout=300,
        open=False,
    )
    await pool.open()
    _resources["pool"] = pool
    logger.info("PostgreSQL pool initialized")

    # Initialize Redis client
    logger.info("Initializing Redis client...")
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    _resources["redis"] = redis_client
    logger.info("Redis client initialized")

    # Initialize httpx client for Core API calls
    logger.info("Initializing httpx client...")
    httpx_client = httpx.AsyncClient(
        base_url=settings.core_service_url,
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
    )
    _resources["httpx"] = httpx_client
    logger.info("httpx client initialized")

    # Setup LangGraph checkpointer tables
    logger.info("Setting up LangGraph checkpointer tables...")
    try:
        from src.graph.checkpointer import setup_checkpointer

        await setup_checkpointer(pool)
        logger.info("LangGraph checkpointer tables ready")
    except Exception as e:
        logger.error(f"Failed to setup checkpointer: {e}")
        raise

    logger.info("Changple Agent Service started successfully")

    yield

    # Cleanup
    logger.info("Shutting down Changple Agent Service...")

    await httpx_client.aclose()
    logger.info("httpx client closed")

    await redis_client.aclose()
    logger.info("Redis client closed")

    await pool.close()
    logger.info("PostgreSQL pool closed")

    _resources.clear()
    logger.info("Changple Agent Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Changple Agent Service",
    description="LangGraph RAG Chatbot for Changple AI",
    version="3.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(api_router)

# WebSocket router
from src.api.websocket import router as websocket_router

app.include_router(websocket_router)
