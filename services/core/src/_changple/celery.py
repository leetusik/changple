"""
Celery configuration for Changple Core service.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src._changple.settings")

app = Celery("changple")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Configure task routing for different queues
app.conf.task_routes = {
    # Scraper tasks - resource intensive, can handle longer processing
    "src.scraper.tasks.scheduled_scraping_task": {"queue": "scraper"},
    "src.scraper.tasks.full_rescan_task": {"queue": "scraper"},
    "src.scraper.tasks.chunked_full_rescan_coordinator": {"queue": "scraper"},
    "src.scraper.tasks.ingest_docs_task": {"queue": "scraper"},
    "src.scraper.tasks.ingest_docs_chunk_task": {"queue": "scraper"},
    # Batch API tasks
    "src.scraper.tasks.submit_batch_jobs_task": {"queue": "scraper"},
    "src.scraper.tasks.poll_batch_status_task": {"queue": "scraper"},
    "src.scraper.tasks.ingest_completed_batches_task": {"queue": "scraper"},
    # Default queue for other tasks
    "*": {"queue": "default"},
}

# Configure queue priorities
app.conf.task_default_queue = "default"
app.conf.task_create_missing_queues = True

# Optimize task execution settings for reliability
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1  # Process one task at a time
app.conf.task_reject_on_worker_lost = True

# Retry configuration for failed tasks
app.conf.task_retry_jitter = True
app.conf.task_retry_jitter_max = 60
app.conf.task_default_retry_delay = 60

# Task deduplication settings
app.conf.task_ignore_result = False
app.conf.result_expires = 3600  # Results expire after 1 hour

# Worker settings for isolation
app.conf.worker_disable_rate_limits = False
app.conf.worker_max_tasks_per_child = 10  # Restart worker after 10 tasks

# Prevent task duplication by ensuring proper serialization
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_accept_content = ["json"]


# Celery Beat schedule configuration
app.conf.beat_schedule = {
    # Phase 1: Submit batch jobs at 4:00 AM daily
    "daily-batch-submit": {
        "task": "src.scraper.tasks.submit_batch_jobs_task",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {"batch_size": 100, "use_batch_api": True},
    },
    # Phase 2: Poll batch status every 30 minutes
    "poll-batch-status": {
        "task": "src.scraper.tasks.poll_batch_status_task",
        "schedule": crontab(minute="*/30"),
    },
}
app.conf.timezone = "Asia/Seoul"
