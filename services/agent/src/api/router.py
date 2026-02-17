"""API router aggregator."""

from fastapi import APIRouter

from src.api.chat import router as chat_router
from src.api.health import router as health_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health_router)
api_router.include_router(chat_router)
