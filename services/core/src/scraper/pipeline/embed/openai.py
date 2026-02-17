"""
OpenAI Batch API embedder (50% cost savings).

Wraps the existing batch_embed.py logic into the pipeline interface.
"""

import logging
from typing import List, Optional

from src.scraper.ingest.batch_embed import (
    check_embedding_batch,
    submit_embedding_batch,
)
from src.scraper.pipeline.base import BaseEmbedder

logger = logging.getLogger(__name__)


class OpenAIBatchEmbedder(BaseEmbedder):
    """Batch embedder using OpenAI Batch API for 50% cost savings."""

    def embed_batch_submit(self, texts: List[str], ids: List[str]) -> Optional[str]:
        """
        Submit texts for batch embedding.

        Returns:
            batch_id for polling, or None if failed
        """
        return submit_embedding_batch(texts, ids)

    def embed_batch_check(self, job_id: str) -> tuple[str, Optional[dict]]:
        """
        Check OpenAI embedding batch status.

        Returns:
            (status, embeddings_dict) - status is "processing", "completed", or "failed"
        """
        return check_embedding_batch(job_id)
