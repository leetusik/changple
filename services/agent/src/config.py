"""
Configuration settings for Agent service using pydantic-settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service info
    app_name: str = "Changple Agent"
    debug: bool = False

    # Core service URL (all data access through here)
    core_service_url: str = "http://core:8000"

    # LangGraph checkpoint database (separate from Django database)
    langgraph_database_url: str = "postgresql://changple:changple@postgres:5432/changple_langgraph"

    # Redis
    redis_url: str = "redis://redis:6379/1"

    # AI service keys
    openai_api_key: str = ""
    google_api_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "changple-index"
    pinecone_environment: str = "us-east-1"

    # LLM settings
    default_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-3-large"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
