"""
Asynchronous tasks for the chatbot application.
This module contains celery/rq tasks for background processing.
"""

import logging

import django_rq
from django.core import management

logger = logging.getLogger(__name__)


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
