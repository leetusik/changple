"""
Abstract base classes and data models for the ingestion pipeline.

Defines the interfaces that all pipeline stages must implement,
enabling easy extension to new content sources (YouTube, Blog, etc.).
"""

import enum
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class ContentSource(enum.Enum):
    """Supported content sources."""

    NAVER_CAFE = "naver_cafe"
    YOUTUBE = "youtube"  # future
    BLOG = "blog"  # future


@dataclass
class ScrapedItem:
    """Universal format for scraped content across all sources."""

    source: ContentSource
    source_id: str  # Unique ID within the source (e.g., post_id)
    title: str
    content: str
    author: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ProcessedItem:
    """Content after LLM processing (summarization, keyword extraction)."""

    source_id: str
    title: str
    content: str
    author: str
    summary: str
    keywords: List[str]
    retrieval_queries: List[str]
    metadata: dict = field(default_factory=dict)


class BaseScraper(ABC):
    """Abstract base class for content scrapers."""

    @abstractmethod
    def get_items_to_process(self, **kwargs) -> List[ScrapedItem]:
        """Get items that need processing."""
        ...

    @abstractmethod
    def get_item_ids_to_process(self, **kwargs) -> List[str]:
        """Get IDs of items that need processing."""
        ...


class BaseProcessor(ABC):
    """Abstract base class for content processors (summarization, etc.)."""

    @abstractmethod
    def process(self, item: ScrapedItem) -> ProcessedItem:
        """Process a single scraped item."""
        ...

    @abstractmethod
    def process_batch_submit(self, items: list) -> Optional[str]:
        """Submit a batch for async processing. Returns job ID."""
        ...

    @abstractmethod
    def process_batch_check(self, job_id: str) -> tuple[str, Optional[list]]:
        """Check batch status. Returns (status, results)."""
        ...

    @abstractmethod
    def process_batch_apply(self, batch_job: Any, results: list) -> int:
        """Apply batch results to database. Returns count processed."""
        ...


class BaseEmbedder(ABC):
    """Abstract base class for embedding generators."""

    @abstractmethod
    def embed_batch_submit(self, texts: List[str], ids: List[str]) -> Optional[str]:
        """Submit texts for batch embedding. Returns job ID."""
        ...

    @abstractmethod
    def embed_batch_check(self, job_id: str) -> tuple[str, Optional[dict]]:
        """Check embedding batch status. Returns (status, embeddings_dict)."""
        ...


class BaseVectorStore(ABC):
    """Abstract base class for vector store operations."""

    @abstractmethod
    def cleanup(self) -> dict:
        """Pre-ingestion cleanup. Returns cleanup summary."""
        ...

    @abstractmethod
    def ingest(
        self, items: List[ProcessedItem], embeddings: Optional[dict] = None
    ) -> int:
        """Ingest processed items. Returns count ingested."""
        ...

    @abstractmethod
    def ingest_embeddings(self, batch_job: Any, embeddings: dict) -> int:
        """Ingest pre-computed embeddings. Returns count ingested."""
        ...
