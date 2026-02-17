"""
Pinecone vector store operations.

Wraps the existing Pinecone logic from ingest.py and batch_embed.py
into the pipeline interface.
"""

import logging
from typing import Any, List, Optional

from django.conf import settings
from django.db import transaction
from django.db.models.functions import Length
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from src.scraper.ingest.batch_embed import ingest_embeddings_to_pinecone
from src.scraper.models import AllowedAuthor, NaverCafeData
from src.scraper.pipeline.base import BaseVectorStore, ProcessedItem

logger = logging.getLogger(__name__)


class PineconeStore(BaseVectorStore):
    """Pinecone vector store for document storage and retrieval."""

    def _get_embeddings_model(self) -> OpenAIEmbeddings:
        """Returns an embedding model instance."""
        return OpenAIEmbeddings(model="text-embedding-3-large", chunk_size=200)

    def _get_pinecone_index(self):
        """Get or create Pinecone index."""
        pc = Pinecone(api_key=settings.PINECONE_API_KEY, transport="http")

        index_names = pc.list_indexes()
        if settings.PINECONE_INDEX_NAME not in index_names.names():
            logger.info("Creating Pinecone index...")
            pc.create_index(
                settings.PINECONE_INDEX_NAME,
                dimension=3072,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=settings.PINECONE_ENVIRONMENT,
                ),
            )

        return pc.Index(settings.PINECONE_INDEX_NAME)

    def _get_all_pinecone_ids(self, index) -> set:
        """Get all existing IDs from a Pinecone index."""
        response = list(index.list())
        temp_list = []
        for i in response:
            temp_list += i
        return set(temp_list)

    def cleanup(self) -> dict:
        """
        Pre-ingestion cleanup of Pinecone vectors.

        - Delete vectors for posts that changed (ingested=False)
        - Delete orphaned vectors (exist in Pinecone but not in DB)
        """
        index = self._get_pinecone_index()

        existing_pinecone_ids = self._get_all_pinecone_ids(index)
        logger.info(f"Found {len(existing_pinecone_ids)} existing vectors in Pinecone")

        allowed_authors = list(AllowedAuthor.objects.values_list("name", flat=True))
        if not allowed_authors:
            allowed_authors = ["창플"]

        all_posts = list(
            NaverCafeData.objects.annotate(content_length=Length("content"))
            .filter(author__in=allowed_authors, content_length__gt=1000)
            .values_list("post_id", "ingested")
        )

        db_post_ids = set(str(post_id) for post_id, _ in all_posts)
        posts_to_reingest = set(
            str(post_id) for post_id, ingested in all_posts if not ingested
        )

        ids_to_delete = []

        # Delete vectors for re-ingestion
        reingest_vectors = existing_pinecone_ids.intersection(posts_to_reingest)
        if reingest_vectors:
            ids_to_delete.extend(list(reingest_vectors))

        # Delete orphaned vectors
        orphaned_vectors = existing_pinecone_ids - db_post_ids
        if orphaned_vectors:
            ids_to_delete.extend(list(orphaned_vectors))

        deleted_count = 0
        if ids_to_delete:
            batch_size = 1000
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i : i + batch_size]
                index.delete(ids=batch)
                deleted_count += len(batch)

        try:
            stats = index.describe_index_stats()
            final_vector_count = stats.total_vector_count
        except Exception:
            final_vector_count = "unknown"

        return {
            "initial_vectors": len(existing_pinecone_ids),
            "database_posts": len(db_post_ids),
            "posts_to_reingest": len(posts_to_reingest),
            "reingest_deletions": len(reingest_vectors),
            "orphaned_deletions": len(orphaned_vectors),
            "total_deleted": deleted_count,
            "final_vector_count": final_vector_count,
        }

    def ingest(
        self, items: List[ProcessedItem], embeddings: Optional[dict] = None
    ) -> int:
        """
        Ingest processed items to Pinecone using LangChain.

        Generates embeddings on-the-fly and upserts to Pinecone.
        """
        embedding_model = self._get_embeddings_model()

        vector_store = PineconeVectorStore(
            index_name=settings.PINECONE_INDEX_NAME,
            embedding=embedding_model,
            text_key="text",
        )

        docs_to_embed = []
        batch_ids = []

        for item in items:
            keywords_str = ",".join(item.keywords) if item.keywords else ""
            questions_str = (
                ",".join(item.retrieval_queries) if item.retrieval_queries else ""
            )

            text_for_embedding = (
                f"제목:'{item.title}',키워드:'{keywords_str}',"
                f"요약:'{item.summary}',질문:'{questions_str}'"
            )

            doc = Document(
                page_content=text_for_embedding,
                metadata={
                    "post_id": int(item.source_id),
                    "title": item.title,
                    "author": item.author,
                    "summary": item.summary,
                    "keywords": keywords_str,
                },
            )
            docs_to_embed.append(doc)
            batch_ids.append(item.source_id)

        if docs_to_embed:
            vector_store.add_documents(documents=docs_to_embed, ids=batch_ids)
            logger.info(f"Ingested {len(docs_to_embed)} documents to Pinecone")

            # Mark as ingested
            post_ids = [int(item.source_id) for item in items]
            self._update_ingested_status(post_ids)

        return len(docs_to_embed)

    def ingest_embeddings(self, batch_job: Any, embeddings: dict) -> int:
        """Ingest pre-computed embeddings from OpenAI Batch API."""
        return ingest_embeddings_to_pinecone(batch_job, embeddings)

    def _update_ingested_status(self, post_ids: List[int]) -> int:
        """Mark documents as successfully ingested."""
        with transaction.atomic():
            updated = NaverCafeData.objects.filter(post_id__in=post_ids).update(
                ingested=True
            )
            logger.info(f"Marked {updated} documents as ingested=True")
            return updated
