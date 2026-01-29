"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "changple-agent"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Changple Agent Service", "version": "3.0.0"}
