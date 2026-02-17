"""
Naver Cafe scraper implementation.

Wraps existing database queries for NaverCafeData posts.
"""

import logging
from typing import List, Optional

from django.db.models.functions import Length

from src.scraper.models import AllowedAuthor, NaverCafeData
from src.scraper.pipeline.base import BaseScraper, ContentSource, ScrapedItem

logger = logging.getLogger(__name__)


class NaverCafeScraper(BaseScraper):
    """Scraper for Naver Cafe posts (reads from database)."""

    def __init__(self, min_content_length: int = 1000):
        self.min_content_length = min_content_length

    def _get_active_authors(self) -> List[str]:
        """Get list of active author names."""
        active_authors = list(
            AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
        )
        if not active_authors:
            logger.warning("No active authors found. Using default author.")
            active_authors = ["창플"]
        return active_authors

    def get_items_to_process(
        self,
        offset: int = 0,
        limit: int = 100,
        post_ids: Optional[List[int]] = None,
    ) -> List[ScrapedItem]:
        """
        Get scraped items from database that need processing.

        Args:
            offset: Starting position for pagination
            limit: Maximum number of posts
            post_ids: Specific post IDs to retrieve

        Returns:
            List of ScrapedItem objects
        """
        active_authors = self._get_active_authors()

        if post_ids:
            logger.info(f"Loading {len(post_ids)} specific posts from database")
            posts = NaverCafeData.objects.annotate(
                content_length=Length("content")
            ).filter(
                post_id__in=post_ids,
                author__in=active_authors,
                content_length__gt=self.min_content_length,
                ingested=False,
            )
        else:
            logger.info(f"Loading posts {offset}-{offset + limit} from database")
            posts = NaverCafeData.objects.annotate(
                content_length=Length("content")
            ).filter(
                author__in=active_authors,
                content_length__gt=self.min_content_length,
                ingested=False,
            )[offset : offset + limit]

        items = []
        for post in posts:
            items.append(
                ScrapedItem(
                    source=ContentSource.NAVER_CAFE,
                    source_id=str(post.post_id),
                    title=post.title,
                    content=post.content,
                    author=post.author,
                    metadata={
                        "post_id": post.post_id,
                        "keywords": post.keywords,
                        "summary": post.summary,
                        "possible_questions": post.possible_questions,
                        "ingested": post.ingested,
                    },
                )
            )

        logger.info(f"Loaded {len(items)} posts")
        return items

    def get_item_ids_to_process(self) -> List[str]:
        """Get all post IDs that need processing (ingested=False)."""
        active_authors = self._get_active_authors()

        post_ids = list(
            NaverCafeData.objects.annotate(content_length=Length("content"))
            .filter(
                author__in=active_authors,
                content_length__gt=self.min_content_length,
                ingested=False,
            )
            .values_list("post_id", flat=True)
        )

        logger.info(f"Found {len(post_ids)} posts that need processing")
        return [str(pid) for pid in post_ids]
