"""
Gemini Batch API summarizer (50% cost savings).

Wraps the existing batch_summarize.py logic into the pipeline interface.
"""

import logging
from typing import Any, Optional

from src.scraper.ingest.batch_summarize import (
    check_summarization_batch,
    process_summarization_results,
    submit_summarization_batch,
)
from src.scraper.pipeline.base import BaseProcessor, ProcessedItem, ScrapedItem

logger = logging.getLogger(__name__)


class GeminiSummarizer(BaseProcessor):
    """Batch processor using Gemini Batch API for 50% cost savings."""

    def process(self, item: ScrapedItem) -> ProcessedItem:
        """
        Not typically used for batch processing.
        Use the ContentEvaluator for synchronous processing.
        """
        raise NotImplementedError(
            "GeminiSummarizer is for batch processing. Use ContentEvaluator for sync."
        )

    def process_batch_submit(self, items: list) -> Optional[str]:
        """
        Submit batch to Gemini Batch API.

        Args:
            items: List of NaverCafeData model objects

        Returns:
            job_name for polling, or None if failed
        """
        return submit_summarization_batch(items)

    def process_batch_check(self, job_id: str) -> tuple[str, Optional[list]]:
        """
        Check Gemini batch job status.

        Returns:
            (status, results) - status is "processing", "completed", or "failed"
        """
        return check_summarization_batch(job_id)

    def process_batch_apply(self, batch_job: Any, results: list) -> int:
        """
        Apply batch summarization results to database.

        Returns:
            Number of successfully processed posts
        """
        return process_summarization_results(batch_job, results)
