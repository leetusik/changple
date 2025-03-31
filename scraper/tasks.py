import asyncio
import logging
import os
import sys
from typing import Optional

from django.conf import settings
from django_rq import job
from rq import get_current_job

from chatbot.tasks import run_ingest_task
from scraper.services.crawler import main as crawler_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scheduled_scraper.log"),
        logging.StreamHandler(
            sys.stdout
        ),  # Ensure output goes to stdout for worker visibility
    ],
)
logger = logging.getLogger(__name__)


@job
def run_scheduled_crawler(
    start_id: Optional[int] = None, end_id: Optional[int] = None, batch_size: int = 100
):
    """
    RQ job to run the crawler with the given parameters.
    This will be scheduled to run at specific intervals.

    Args:
        start_id: Starting post ID (optional)
        end_id: Ending post ID (optional)
        batch_size: Number of posts to collect before saving to database (default: 100)
    """
    # Get the current job ID safely
    current_job = get_current_job()
    job_id = current_job.id if current_job else "unknown"

    range_info = f"from {start_id or 'last post'} to {end_id or 'latest'} with batch size {batch_size}"

    logger.info(f"===== JOB {job_id} START =====")
    logger.info(f"Starting scheduled crawler job. Range: {range_info}")
    print(f"\n▶️ [Job {job_id}] Starting crawler {range_info}\n")

    try:
        # Need to run async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the crawler
        loop.run_until_complete(crawler_main(start_id, end_id, batch_size))
        loop.close()

        logger.info(f"Scheduled crawler job completed successfully")
        print(f"\n✅ [Job {job_id}] Crawler job completed successfully\n")

        # Trigger the ingestion process to vectorize new data
        logger.info("Triggering document ingestion task to vectorize new data...")
        ingest_job = run_ingest_task.delay()
        logger.info(f"Ingestion task queued with job ID: {ingest_job.id}")
        print(
            f"\n🔄 [Job {job_id}] Vectorization task queued (Job ID: {ingest_job.id})\n"
        )

        return True
    except Exception as e:
        logger.error(f"Error in scheduled crawler job: {e}")
        logger.exception(e)
        print(f"\n❌ [Job {job_id}] Error: {str(e)}\n")
        return False
    finally:
        logger.info(f"===== JOB {job_id} END =====")
        print(f"\n🏁 [Job {job_id}] Job finished\n")
