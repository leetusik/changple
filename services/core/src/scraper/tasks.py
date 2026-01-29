"""
Celery tasks for scraper app.
"""

import logging
from typing import List, Optional

from celery import group, shared_task
from django.utils import timezone

from src.scraper.ingest.ingest import (
    cleanup_pinecone_vectors,
    get_posts_to_ingest_ids,
    ingest_docs_chunk_sync,
)
from src.scraper.models import AllowedAuthor, BatchJob, NaverCafeData

logger = logging.getLogger(__name__)

# Configuration constants
CHUNK_SIZE = 1000
MAX_BATCH_SIZE = 100


@shared_task(
    bind=True,
    name="src.scraper.tasks.scheduled_scraping_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
    retry_backoff=True,
    retry_jitter=True,
)
def scheduled_scraping_task(self, batch_size: int = 100, auto_ingest: bool = True):
    """
    Celery task for scheduled incremental scraping.

    This task scrapes new posts from the last saved post ID to the latest.
    """
    # Note: Scraping logic will be implemented separately
    # This is a placeholder that triggers ingest after scraping
    logger.info(f"Starting scheduled scraping task with batch_size={batch_size}")

    # TODO: Implement scraping logic using Playwright
    # For now, just trigger ingest if auto_ingest is True

    if auto_ingest:
        logger.info("Triggering automatic document ingestion after scraping")
        try:
            ingest_task = ingest_docs_task.delay()
            logger.info(f"Automatic ingest task started with ID: {ingest_task.id}")
        except Exception as ingest_error:
            logger.error(f"Failed to start automatic ingest task: {ingest_error}")


@shared_task(
    bind=True,
    name="src.scraper.tasks.ingest_docs_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 1, "countdown": 30},
    retry_backoff=True,
    retry_jitter=True,
)
def ingest_docs_task(self, *args, **kwargs):
    """
    Coordinator task for chunked document ingestion.

    This task:
    1. Cleans up Pinecone vectors
    2. Splits documents into chunks
    3. Processes chunks in parallel
    """
    try:
        logger.info("Starting document ingestion coordinator")

        # Cleanup Pinecone vectors
        logger.info("Running Pinecone cleanup before chunked ingestion...")
        cleanup_result = cleanup_pinecone_vectors()
        logger.info(f"Pinecone cleanup completed: {cleanup_result}")

        # Get all post IDs that need processing
        all_post_ids = get_posts_to_ingest_ids()

        if not all_post_ids:
            logger.info("No documents to ingest after cleanup")
            return {
                "total_posts": 0,
                "chunks_created": 0,
                "cleanup_result": cleanup_result,
                "message": "No documents to ingest after cleanup",
            }

        total_posts = len(all_post_ids)
        logger.info(f"Found {total_posts} posts that need processing")

        # Create chunks
        chunk_size = MAX_BATCH_SIZE
        total_chunks = (total_posts - 1) // chunk_size + 1

        logger.info(f"Creating {total_chunks} chunks for {total_posts} documents")

        chunk_tasks = []
        for i in range(total_chunks):
            start_idx = i * chunk_size
            end_idx = min(start_idx + chunk_size, total_posts)
            chunk_post_ids = all_post_ids[start_idx:end_idx]

            unique_task_id = f"ingest_chunk_ids_{start_idx}_{end_idx}"
            task = ingest_docs_chunk_task.s(post_ids=chunk_post_ids).set(
                task_id=unique_task_id
            )
            chunk_tasks.append(task)

        # Execute all chunks in parallel
        job = group(chunk_tasks)
        result = job.apply_async()

        logger.info(
            f"Document ingestion coordinator completed. Created {len(chunk_tasks)} chunk tasks"
        )

        return {
            "total_posts": total_posts,
            "chunks_created": len(chunk_tasks),
            "chunk_size": chunk_size,
            "cleanup_result": cleanup_result,
            "job_id": str(result.id),
            "message": f"Created {len(chunk_tasks)} chunk tasks for {total_posts} documents",
        }

    except Exception as e:
        logger.error(f"Document ingestion coordinator failed: {e}")
        raise


@shared_task(
    bind=True,
    name="src.scraper.tasks.ingest_docs_chunk_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 60},
    retry_backoff=True,
    retry_jitter=True,
)
def ingest_docs_chunk_task(
    self, offset: int = 0, limit: int = 100, post_ids: list = None
):
    """
    Celery task for ingesting a chunk of documents into Pinecone.
    """
    try:
        if post_ids:
            chunk_description = (
                f"IDs {post_ids[:3]}...{post_ids[-3:]} ({len(post_ids)} posts)"
            )
            logger.info(f"Starting document ingestion chunk task: {chunk_description}")
            ingest_docs_chunk_sync(post_ids=post_ids)
        else:
            logger.info(
                f"Starting document ingestion chunk task: {offset}-{offset+limit}"
            )
            ingest_docs_chunk_sync(offset, limit)

        logger.info("Document ingestion chunk task completed successfully")

    except Exception as e:
        logger.error(f"Document ingestion chunk task failed: {e}")
        raise


# ============================================================================
# Batch API Tasks (50% cost savings)
# ============================================================================


@shared_task(
    bind=True,
    name="src.scraper.tasks.submit_batch_jobs_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 60},
)
def submit_batch_jobs_task(
    self, batch_size: int = 100, use_batch_api: bool = True
):
    """
    Phase 1: Submit batch jobs to provider APIs.

    This task:
    1. Scrapes new posts (if needed)
    2. Submits summarization batch to Gemini
    3. Creates BatchJob record for tracking
    """
    from django.db.models.functions import Length

    from src.scraper.ingest.batch_summarize import submit_summarization_batch

    logger.info("Starting batch job submission task")

    # Get active authors
    active_authors = list(
        AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
    )
    if not active_authors:
        active_authors = ["창플"]

    # Get posts that need processing
    posts = list(
        NaverCafeData.objects.annotate(content_length=Length("content"))
        .filter(
            author__in=active_authors,
            content_length__gt=1000,
            ingested=False,
            summary__isnull=True,  # Only posts without summary
        )
        .order_by("post_id")[:batch_size]
    )

    if not posts:
        logger.info("No posts need processing")
        return {"message": "No posts to process", "batch_jobs_created": 0}

    logger.info(f"Found {len(posts)} posts for batch processing")

    if not use_batch_api:
        # Fallback to regular processing
        logger.info("Using regular processing (batch API disabled)")
        ingest_docs_task.delay()
        return {"message": "Triggered regular ingestion", "posts": len(posts)}

    # Submit to Gemini Batch API
    post_ids = [p.post_id for p in posts]
    job_name = submit_summarization_batch(posts)

    if not job_name:
        logger.error("Failed to submit Gemini batch job")
        return {"error": "Failed to submit batch job", "posts": len(posts)}

    # Create BatchJob record
    batch_job = BatchJob.objects.create(
        job_type="summarize",
        provider="gemini",
        job_id=job_name,
        status="submitted",
        post_ids=post_ids,
        submitted_at=timezone.now(),
    )

    logger.info(f"Created BatchJob {batch_job.id} with job_id {job_name}")

    return {
        "message": "Batch job submitted successfully",
        "batch_job_id": batch_job.id,
        "job_name": job_name,
        "posts_count": len(posts),
    }


@shared_task(
    bind=True,
    name="src.scraper.tasks.poll_batch_status_task",
)
def poll_batch_status_task(self):
    """
    Phase 2: Poll batch job status and process results.

    This task runs every 30 minutes to check:
    1. Summarization jobs -> If complete, submit embedding batch
    2. Embedding jobs -> If complete, ingest to Pinecone
    """
    from src.scraper.ingest.batch_embed import (
        check_embedding_batch,
        ingest_embeddings_to_pinecone,
        submit_embedding_batch,
    )
    from src.scraper.ingest.batch_summarize import (
        check_summarization_batch,
        process_summarization_results,
    )

    logger.info("Polling batch job status")

    # Check submitted/processing summarization jobs
    summarize_jobs = BatchJob.objects.filter(
        job_type="summarize",
        status__in=["submitted", "processing"],
    )

    for job in summarize_jobs:
        logger.info(f"Checking summarization job {job.id} ({job.job_id})")

        status, results = check_summarization_batch(job.job_id)

        if status == "completed" and results:
            logger.info(f"Summarization job {job.id} completed")
            process_summarization_results(job, results)

            # Submit embedding batch
            posts = NaverCafeData.objects.filter(post_id__in=job.post_ids)
            texts = []
            custom_ids = []

            for post in posts:
                if post.summary:
                    keywords_str = ",".join(post.keywords or [])
                    questions_str = ",".join(post.possible_questions or [])
                    text = f"제목:'{post.title}',키워드:'{keywords_str}',요약:'{post.summary}',질문:'{questions_str}'"
                    texts.append(text)
                    custom_ids.append(str(post.post_id))

            if texts:
                batch_id = submit_embedding_batch(texts, custom_ids)
                if batch_id:
                    BatchJob.objects.create(
                        job_type="embed",
                        provider="openai",
                        job_id=batch_id,
                        status="submitted",
                        post_ids=job.post_ids,
                        submitted_at=timezone.now(),
                    )
                    logger.info(f"Submitted embedding batch: {batch_id}")

        elif status == "failed":
            job.status = "failed"
            job.error_message = "Batch job failed"
            job.save()
            logger.error(f"Summarization job {job.id} failed")

        elif status == "processing":
            job.status = "processing"
            job.save()

    # Check submitted/processing embedding jobs
    embed_jobs = BatchJob.objects.filter(
        job_type="embed",
        status__in=["submitted", "processing"],
    )

    for job in embed_jobs:
        logger.info(f"Checking embedding job {job.id} ({job.job_id})")

        status, embeddings = check_embedding_batch(job.job_id)

        if status == "completed" and embeddings:
            logger.info(f"Embedding job {job.id} completed")
            ingest_embeddings_to_pinecone(job, embeddings)

        elif status == "failed":
            job.status = "failed"
            job.error_message = "Batch job failed"
            job.save()
            logger.error(f"Embedding job {job.id} failed")

        elif status == "processing":
            job.status = "processing"
            job.save()

    return {
        "summarize_jobs_checked": summarize_jobs.count(),
        "embed_jobs_checked": embed_jobs.count(),
    }


@shared_task(
    bind=True,
    name="src.scraper.tasks.full_rescan_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def full_rescan_task(
    self,
    start_id: int = 1,
    end_id: Optional[int] = None,
    batch_size: int = 100,
    force_update: bool = True,
):
    """
    Celery task for full rescan scraping.

    Note: This is a placeholder. Actual scraping logic needs to be implemented.
    """
    logger.info(
        f"Starting full rescan task from {start_id} to {end_id}, "
        f"batch_size={batch_size}, force_update={force_update}"
    )

    # TODO: Implement scraping logic using Playwright
    # For now, just log the request

    logger.info("Full rescan task completed (placeholder)")
