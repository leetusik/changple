"""
Pipeline orchestrator coordinating scrape → process → embed → store.

Provides both synchronous (per-chunk) and batch API (async) workflows.
"""

import logging
from typing import List, Optional

from src.scraper.pipeline.base import ContentSource
from src.scraper.pipeline.embed.openai import OpenAIBatchEmbedder
from src.scraper.pipeline.embed.pinecone import PineconeStore
from src.scraper.pipeline.process.evaluate import ContentEvaluator, SkipDocumentError
from src.scraper.pipeline.process.summarize import GeminiSummarizer
from src.scraper.pipeline.scrape.naver_cafe import NaverCafeScraper

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Coordinates the full ingestion pipeline.

    Supports two modes:
    1. Synchronous: scrape → evaluate → embed → store (per-chunk)
    2. Batch API: submit → poll → apply (async with 50% cost savings)
    """

    def __init__(
        self,
        scraper: NaverCafeScraper,
        processor: ContentEvaluator,
        batch_processor: GeminiSummarizer,
        embedder: OpenAIBatchEmbedder,
        vector_store: PineconeStore,
    ):
        self.scraper = scraper
        self.processor = processor
        self.batch_processor = batch_processor
        self.embedder = embedder
        self.vector_store = vector_store

    def cleanup(self) -> dict:
        """Run pre-ingestion cleanup."""
        return self.vector_store.cleanup()

    def get_item_ids_to_process(self) -> List[str]:
        """Get IDs of items that need processing."""
        return self.scraper.get_item_ids_to_process()

    def process_chunk(
        self,
        offset: int = 0,
        limit: int = 100,
        post_ids: Optional[List[int]] = None,
    ) -> None:
        """
        Process a chunk of documents synchronously.

        Steps:
        1. Load items from database
        2. Process each item (generate summary/keywords via LLM)
        3. Ingest to Pinecone
        """
        items = self.scraper.get_items_to_process(
            offset=offset, limit=limit, post_ids=post_ids
        )

        if not items:
            logger.info("No items to process")
            return

        logger.info(f"Processing {len(items)} items")

        processed_items = []
        for idx, item in enumerate(items, 1):
            try:
                processed = self.processor.process(item)
                processed_items.append(processed)
                logger.info(f"Processed {idx}/{len(items)} items")
            except SkipDocumentError as e:
                logger.info(f"Skipping item {item.source_id}: {e}")
            except Exception as e:
                logger.error(f"Error processing item {item.source_id}: {e}")

        if not processed_items:
            logger.info("No items successfully processed")
            return

        ingested = self.vector_store.ingest(processed_items)
        logger.info(f"Ingested {ingested} items to vector store")

    def submit_batch(self, items: list) -> Optional[str]:
        """Submit items for batch processing (Gemini Batch API)."""
        return self.batch_processor.process_batch_submit(items)

    def check_batch(self, job_id: str) -> tuple[str, Optional[list]]:
        """Check batch processing status."""
        return self.batch_processor.process_batch_check(job_id)

    def apply_batch_results(self, batch_job, results: list) -> int:
        """Apply batch results to database."""
        return self.batch_processor.process_batch_apply(batch_job, results)

    def submit_embeddings(self, texts: List[str], ids: List[str]) -> Optional[str]:
        """Submit texts for batch embedding (OpenAI Batch API)."""
        return self.embedder.embed_batch_submit(texts, ids)

    def check_embeddings(self, job_id: str) -> tuple[str, Optional[dict]]:
        """Check embedding batch status."""
        return self.embedder.embed_batch_check(job_id)

    def ingest_embeddings(self, batch_job, embeddings: dict) -> int:
        """Ingest pre-computed embeddings to vector store."""
        return self.vector_store.ingest_embeddings(batch_job, embeddings)


def get_default_pipeline(
    source: ContentSource = ContentSource.NAVER_CAFE,
) -> PipelineOrchestrator:
    """
    Factory function to create a pipeline with default components.

    Args:
        source: Content source type (currently only NAVER_CAFE supported)

    Returns:
        Configured PipelineOrchestrator
    """
    if source != ContentSource.NAVER_CAFE:
        raise ValueError(f"Unsupported content source: {source}")

    return PipelineOrchestrator(
        scraper=NaverCafeScraper(),
        processor=ContentEvaluator(),
        batch_processor=GeminiSummarizer(),
        embedder=OpenAIBatchEmbedder(),
        vector_store=PineconeStore(),
    )
