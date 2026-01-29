"""
Document ingestion for RAG chatbot.

Loads posts from database, generates summaries/keywords, and ingests to Pinecone.
"""

import logging
import os
from typing import List, Optional

from django.conf import settings
from django.db import transaction
from django.db.models.functions import Length
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from src.scraper.ingest.content_evaluator import summary_and_keywords
from src.scraper.models import AllowedAuthor, NaverCafeData

logger = logging.getLogger(__name__)


class SkipDocumentError(Exception):
    """Exception raised when a document should be skipped from processing."""

    pass


def get_embeddings_model() -> Embeddings:
    """Returns an embedding model instance."""
    return OpenAIEmbeddings(model="text-embedding-3-large", chunk_size=200)


def get_active_authors() -> List[str]:
    """Get list of active author names."""
    active_authors = list(
        AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
    )
    if not active_authors:
        logger.warning("No active authors found. Using default author.")
        active_authors = ["창플"]
    return active_authors


def load_posts_from_database(
    min_content_length: int = 1000,
    offset: int = 0,
    limit: int = 100,
    post_ids: Optional[List[int]] = None,
) -> List[Document]:
    """
    Load posts from database and convert to documents.

    Args:
        min_content_length: Minimum content length filter
        offset: Starting position for pagination (ignored if post_ids provided)
        limit: Maximum number of posts to retrieve (ignored if post_ids provided)
        post_ids: Specific post IDs to retrieve (overrides offset/limit)

    Returns:
        List of Documents
    """
    try:
        active_authors = get_active_authors()

        if post_ids:
            logger.info(f"Loading {len(post_ids)} specific posts from database")
            posts = NaverCafeData.objects.annotate(
                content_length=Length("content")
            ).filter(
                post_id__in=post_ids,
                author__in=active_authors,
                content_length__gt=min_content_length,
                ingested=False,
            )
        else:
            logger.info(f"Loading posts {offset}-{offset+limit} from database")
            posts = NaverCafeData.objects.annotate(
                content_length=Length("content")
            ).filter(
                author__in=active_authors,
                content_length__gt=min_content_length,
                ingested=False,
            )[
                offset : offset + limit
            ]

        documents = []
        for post in posts:
            doc = Document(
                page_content=post.content,
                metadata={
                    "post_id": post.post_id,
                    "title": post.title,
                    "keywords": post.keywords,
                    "summary": post.summary,
                    "possible_questions": post.possible_questions,
                    "author": post.author,
                    "ingested": post.ingested,
                },
            )
            documents.append(doc)

        logger.info(f"Loaded {len(documents)} posts")
        return documents

    except Exception as e:
        logger.error(f"Error loading posts from database: {e}")
        return []


def get_posts_to_ingest_ids(min_content_length: int = 1000) -> List[int]:
    """
    Get all post IDs that need processing (ingested=False).

    Returns:
        List of post IDs that need processing
    """
    try:
        active_authors = get_active_authors()

        post_ids = list(
            NaverCafeData.objects.annotate(content_length=Length("content"))
            .filter(
                author__in=active_authors,
                content_length__gt=min_content_length,
                ingested=False,
            )
            .values_list("post_id", flat=True)
        )

        logger.info(f"Found {len(post_ids)} posts that need processing")
        return post_ids

    except Exception as e:
        logger.error(f"Error getting posts to ingest: {e}")
        return []


def gpt_summarize_sync(doc: Document) -> Document:
    """
    Process document: generate summary, keywords, and possible questions.

    Args:
        doc: Document object with metadata

    Returns:
        Processed document with updated metadata

    Raises:
        SkipDocumentError: If the document should be skipped
    """
    post_id = doc.metadata["post_id"]

    try:
        db_object = NaverCafeData.objects.get(post_id=post_id)
    except NaverCafeData.DoesNotExist:
        logger.error(f"Post with ID {post_id} not found in database")
        raise SkipDocumentError(f"Post with ID {post_id} not found in database")

    if doc.metadata["ingested"] is False:
        try:
            temp_content = f"제목:{doc.metadata['title']}\n{doc.page_content}"
            summary, keywords, possible_questions_list = summary_and_keywords(
                temp_content
            )

            questions_str_list = (
                possible_questions_list
                if isinstance(possible_questions_list, list)
                else []
            )

            doc.metadata["summary"] = summary
            doc.metadata["keywords"] = keywords
            doc.metadata["possible_questions"] = questions_str_list

            logger.info(
                f"Generated summary, keywords, and questions for post_id {post_id}"
            )

            db_object.summary = summary
            db_object.keywords = keywords
            db_object.possible_questions = questions_str_list
            db_object.save(update_fields=["summary", "keywords", "possible_questions"])

        except ValueError as e:
            logger.error(
                f"Failed to generate summary/keywords/questions for post_id {post_id}: {e}"
            )
            raise SkipDocumentError(
                f"Failed to generate summary/keywords/questions: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error during generation/DB update for post_id {post_id}: {e}"
            )
            raise SkipDocumentError(f"Unexpected error processing post: {e}")
    else:
        logger.info(f"Post {post_id} already has data. Skipping generation.")

    doc.metadata["author"] = db_object.author
    return doc


def update_ingested_status(post_ids: List[int]) -> int:
    """Mark documents as successfully ingested in the database."""
    try:
        with transaction.atomic():
            updated_count = NaverCafeData.objects.filter(post_id__in=post_ids).update(
                ingested=True
            )
            logger.info(f"Marked {updated_count} documents as ingested=True")
            return updated_count
    except Exception as e:
        logger.error(f"Error updating ingested status: {e}")
        raise


def get_all_pinecone_ids(index) -> set:
    """Get all existing IDs from a Pinecone index."""
    response = list(index.list())
    temp_list = []
    for i in response:
        temp_list += i
    return set(temp_list)


def cleanup_pinecone_vectors() -> dict:
    """
    Clean up Pinecone vectors before ingestion.

    - Delete vectors for posts that changed (ingested=False)
    - Delete orphaned vectors (exist in Pinecone but not in DB)

    Returns:
        dict: Summary of cleanup operations
    """
    pc = Pinecone(api_key=settings.PINECONE_API_KEY, transport="http")

    # Ensure index exists
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

    index = pc.Index(settings.PINECONE_INDEX_NAME)

    # Get all vectors currently in Pinecone
    existing_pinecone_ids = get_all_pinecone_ids(index)
    logger.info(f"Found {len(existing_pinecone_ids)} existing vectors in Pinecone")

    # Get all posts from database
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

    logger.info(f"Found {len(db_post_ids)} posts in database")
    logger.info(f"Found {len(posts_to_reingest)} posts that need (re)ingestion")

    ids_to_delete = []

    # Delete vectors for posts that need re-ingestion
    reingest_vectors_in_pinecone = existing_pinecone_ids.intersection(posts_to_reingest)
    if reingest_vectors_in_pinecone:
        ids_to_delete.extend(list(reingest_vectors_in_pinecone))
        logger.info(
            f"Will delete {len(reingest_vectors_in_pinecone)} vectors for re-ingestion"
        )

    # Delete orphaned vectors
    orphaned_vectors = existing_pinecone_ids - db_post_ids
    if orphaned_vectors:
        ids_to_delete.extend(list(orphaned_vectors))
        logger.info(f"Will delete {len(orphaned_vectors)} orphaned vectors")

    # Perform deletions in batches
    deleted_count = 0
    if ids_to_delete:
        logger.info(f"Deleting {len(ids_to_delete)} vectors from Pinecone...")

        batch_size = 1000
        for i in range(0, len(ids_to_delete), batch_size):
            batch = ids_to_delete[i : i + batch_size]
            index.delete(ids=batch)
            deleted_count += len(batch)

        logger.info(f"Successfully deleted {deleted_count} vectors")

    # Get final stats
    try:
        stats = index.describe_index_stats()
        final_vector_count = stats.total_vector_count
    except Exception as e:
        logger.warning(f"Could not retrieve final index stats: {e}")
        final_vector_count = "unknown"

    return {
        "initial_vectors": len(existing_pinecone_ids),
        "database_posts": len(db_post_ids),
        "posts_to_reingest": len(posts_to_reingest),
        "reingest_deletions": len(reingest_vectors_in_pinecone),
        "orphaned_deletions": len(orphaned_vectors),
        "total_deleted": deleted_count,
        "final_vector_count": final_vector_count,
    }


def ingest_docs_chunk_sync(
    offset: int = 0,
    limit: int = 100,
    post_ids: Optional[List[int]] = None,
):
    """
    Synchronous function to process a chunk of documents for ingestion.

    Args:
        offset: Starting position for this chunk
        limit: Number of posts to process
        post_ids: Specific post IDs to process (overrides offset/limit)
    """
    embedding = get_embeddings_model()

    pc = Pinecone(api_key=settings.PINECONE_API_KEY, transport="http")
    index = pc.Index(settings.PINECONE_INDEX_NAME)

    vector_store = PineconeVectorStore(
        index_name=settings.PINECONE_INDEX_NAME, embedding=embedding, text_key="text"
    )

    # Load posts
    if post_ids:
        raw_docs = load_posts_from_database(post_ids=post_ids)
        chunk_description = (
            f"IDs {post_ids[:3]}...{post_ids[-3:]} ({len(post_ids)} posts)"
        )
    else:
        raw_docs = load_posts_from_database(offset=offset, limit=limit)
        chunk_description = f"{offset}-{offset+limit}"

    if not raw_docs:
        logger.info(f"No documents found for chunk {chunk_description}")
        return

    logger.info(f"Processing {len(raw_docs)} documents for chunk {chunk_description}")

    # Process documents
    processed_docs = []
    for idx, raw_doc in enumerate(raw_docs, 1):
        try:
            processed_doc = gpt_summarize_sync(raw_doc)
            processed_docs.append(processed_doc)
            logger.info(
                f"Chunk {chunk_description}: processed {idx}/{len(raw_docs)} documents"
            )
        except SkipDocumentError as skip_e:
            logger.info(
                f"Skipping document with post_id {raw_doc.metadata['post_id']}: {skip_e}"
            )
        except Exception as e:
            logger.error(
                f"Error processing document with post_id {raw_doc.metadata['post_id']}: {e}"
            )

    if not processed_docs:
        logger.info(f"No documents successfully processed for chunk {chunk_description}")
        return

    # Prepare and ingest to Pinecone
    successfully_ingested_post_ids = []

    try:
        docs_to_embed = []
        batch_ids = []

        for doc in processed_docs:
            title = doc.metadata.get("title", "")
            summary = doc.metadata.get("summary", "")
            keywords_list = doc.metadata.get("keywords", [])
            questions_list = doc.metadata.get("possible_questions", [])

            keywords_str = ",".join(keywords_list) if keywords_list else ""
            questions_str = ",".join(questions_list) if questions_list else ""

            text_for_embedding = f"""제목:'{title}',키워드:'{keywords_str}',요약:'{summary}',질문:'{questions_str}'"""

            doc.page_content = text_for_embedding
            docs_to_embed.append(doc)
            batch_ids.append(str(doc.metadata["post_id"]))

        logger.info(
            f"Ingesting {len(docs_to_embed)} documents to Pinecone for chunk {chunk_description}"
        )

        vector_store.add_documents(documents=docs_to_embed, ids=batch_ids)

        successfully_ingested_post_ids = [
            doc.metadata["post_id"] for doc in processed_docs
        ]

        logger.info(
            f"Successfully ingested {len(docs_to_embed)} documents for chunk {chunk_description}"
        )

        if successfully_ingested_post_ids:
            update_ingested_status(successfully_ingested_post_ids)

    except Exception as e:
        logger.error(f"Error ingesting chunk {chunk_description} to Pinecone: {e}")
        raise

    logger.info(f"Chunk {chunk_description} processing completed successfully")
