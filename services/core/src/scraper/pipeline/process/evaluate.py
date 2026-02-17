"""
Content evaluation using LLM for individual document processing.

Wraps the existing content_evaluator.py logic into the pipeline interface.
"""

import logging
from typing import Any, Optional

from src.scraper.ingest.content_evaluator import summary_and_keywords
from src.scraper.models import NaverCafeData
from src.scraper.pipeline.base import BaseProcessor, ProcessedItem, ScrapedItem

logger = logging.getLogger(__name__)


class SkipDocumentError(Exception):
    """Exception raised when a document should be skipped from processing."""

    pass


class ContentEvaluator(BaseProcessor):
    """Processes documents using synchronous LLM calls (Gemini)."""

    def process(self, item: ScrapedItem) -> ProcessedItem:
        """
        Process a single scraped item: generate summary, keywords, and queries.

        Raises:
            SkipDocumentError: If the document should be skipped
        """
        post_id = int(item.source_id)

        try:
            db_object = NaverCafeData.objects.get(post_id=post_id)
        except NaverCafeData.DoesNotExist as e:
            raise SkipDocumentError(
                f"Post with ID {post_id} not found in database"
            ) from e

        if not item.metadata.get("ingested", False):
            try:
                temp_content = f"제목:{item.title}\n{item.content}"
                summary, keywords, questions = summary_and_keywords(temp_content)

                questions_list = questions if isinstance(questions, list) else []

                # Save to database
                db_object.summary = summary
                db_object.keywords = keywords
                db_object.possible_questions = questions_list
                db_object.save(
                    update_fields=["summary", "keywords", "possible_questions"]
                )

                logger.info(
                    f"Generated summary/keywords/questions for post_id {post_id}"
                )

                return ProcessedItem(
                    source_id=item.source_id,
                    title=item.title,
                    content=item.content,
                    author=db_object.author,
                    summary=summary,
                    keywords=keywords,
                    retrieval_queries=questions_list,
                    metadata=item.metadata,
                )

            except ValueError as e:
                raise SkipDocumentError(
                    f"Failed to generate summary/keywords: {e}"
                ) from e
            except Exception as e:
                raise SkipDocumentError(f"Unexpected error processing post: {e}") from e
        else:
            logger.info(f"Post {post_id} already processed. Skipping generation.")
            return ProcessedItem(
                source_id=item.source_id,
                title=item.title,
                content=item.content,
                author=db_object.author,
                summary=db_object.summary or "",
                keywords=db_object.keywords or [],
                retrieval_queries=db_object.possible_questions or [],
                metadata=item.metadata,
            )

    def process_batch_submit(self, items: list) -> Optional[str]:
        """Not used for synchronous evaluator."""
        raise NotImplementedError("Use GeminiSummarizer for batch processing")

    def process_batch_check(self, job_id: str) -> tuple[str, Optional[list]]:
        """Not used for synchronous evaluator."""
        raise NotImplementedError("Use GeminiSummarizer for batch processing")

    def process_batch_apply(self, batch_job: Any, results: list) -> int:
        """Not used for synchronous evaluator."""
        raise NotImplementedError("Use GeminiSummarizer for batch processing")
