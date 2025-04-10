import asyncio
import logging
import os
import sys
from typing import Optional

from django.conf import settings
from django_rq import job
from rq import get_current_job

from chatbot.services.ingest import ingest_docs

# Import crawler and ingestion/indexing functions
from scraper.services.crawler import main as crawler_main

# from chatbot.services.whoosh_service import create_whoosh_index


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Added logger name
    handlers=[
        logging.FileHandler("scheduled_task.log"),  # Combined log file for the task
        logging.StreamHandler(
            sys.stdout
        ),  # Ensure output goes to stdout for worker visibility
    ],
    force=True,  # Force reconfiguration
)
logger = logging.getLogger(__name__)  # Get logger for this module


@job("default")  # Specify the queue name explicitly
def run_scheduled_crawler(
    start_id: Optional[int] = None, end_id: Optional[int] = None, batch_size: int = 100
):
    """
    RQ job to run the crawler, then Whoosh index, then Pinecone ingest.
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
    success = True  # Track overall success

    logger.info(f"===== JOB {job_id} START =====")
    logger.info(f"Starting scheduled task. Range: {range_info}")
    print(
        f"\n▶️ [Job {job_id}] Starting scheduled task: Crawl -> Whoosh -> Pinecone ({range_info})\n"
    )

    try:
        # 1. Run Crawler
        logger.info(f"[Job {job_id}] Running crawler...")
        print(f"   [Job {job_id}] Running crawler...")
        # Need to run async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(crawler_main(start_id, end_id, batch_size))
        loop.close()
        logger.info(f"[Job {job_id}] Crawler finished successfully.")
        print(f"   [Job {job_id}] Crawler finished successfully.")

        # # 2. Run Whoosh Indexing
        # logger.info(f"[Job {job_id}] Running Whoosh indexing...")
        # print(f"   [Job {job_id}] Running Whoosh indexing...")
        # try:
        #     create_whoosh_index()
        #     logger.info(f"[Job {job_id}] Whoosh indexing finished successfully.")
        #     print(f"   [Job {job_id}] Whoosh indexing finished successfully.")
        # except Exception as whoosh_e:
        #     logger.error(
        #         f"[Job {job_id}] Whoosh indexing failed: {whoosh_e}", exc_info=True
        #     )
        #     print(f"   ❌ [Job {job_id}] Whoosh indexing failed: {str(whoosh_e)}")
        #     success = False  # Mark overall job as failed

        # 3. Run Pinecone Ingestion (Attempt even if Whoosh failed)
        logger.info(f"[Job {job_id}] Running Pinecone ingestion...")
        print(f"   [Job {job_id}] Running Pinecone ingestion...")
        try:
            ingest_docs()
            logger.info(f"[Job {job_id}] Pinecone ingestion finished successfully.")
            print(f"   [Job {job_id}] Pinecone ingestion finished successfully.")
        except Exception as pinecone_e:
            logger.error(
                f"[Job {job_id}] Pinecone ingestion failed: {pinecone_e}", exc_info=True
            )
            print(f"   ❌ [Job {job_id}] Pinecone ingestion failed: {str(pinecone_e)}")
            success = False  # Mark overall job as failed

    except Exception as e:
        # Catch errors specifically from the crawler step
        logger.error(f"[Job {job_id}] Crawler step failed: {e}", exc_info=True)
        print(f"\n❌ [Job {job_id}] Crawler step failed: {str(e)}\n")
        success = False  # Mark overall job as failed
        # If crawler fails, we typically don't proceed to index/ingest
    finally:
        logger.info(f"===== JOB {job_id} END =====")
        if success:
            print(f"\n✅ [Job {job_id}] Scheduled task completed successfully\n")
        else:
            print(f"\n❌ [Job {job_id}] Scheduled task finished with errors\n")

    # RQ considers the job successful if no exception bubbles up
    # To mark as failed in RQ, we would need to re-raise an exception.
    # For now, we log errors and return based on success flag.
    return success
