"""
Asynchronous tasks for the chatbot application.
This module contains celery/rq tasks for background processing.
"""

import logging

<<<<<<< HEAD
from django_rq import job

from chatbot.services.ingest import ingest_docs
=======
import django_rq
from django.core import management
>>>>>>> temp_hi

logger = logging.getLogger(__name__)


<<<<<<< HEAD
@job
def run_ingest_task():
    """
    RQ job to run the document ingestion process.
    This processes all non-vectorized documents from allowed authors and
    indexes them in Pinecone for retrieval by the chatbot.
    """
    logger.info("Starting automated ingestion process...")
    try:
        ingest_docs()
        logger.info("Successfully completed automated ingestion process")
        return True
    except Exception as e:
        logger.error(f"Error during automated ingestion process: {e}")
        return False
=======
@django_rq.job
def run_ingest_task():
    """
    RQ job to run the ingest command after scraping.
    This will create Whoosh index and ingest documents to Pinecone.
    """
    logger.info("Starting ingest process after scraping")
    try:
        management.call_command("run_ingest")
        logger.info("Ingest process completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in ingest process: {e}")
        logger.exception(e)
        return False


# Define your tasks here
>>>>>>> temp_hi
