"""
Asynchronous tasks for the chatbot application.
This module contains celery/rq tasks for background processing.
"""

import logging

from django_rq import job

from chatbot.services.ingest import ingest_docs

logger = logging.getLogger(__name__)


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
