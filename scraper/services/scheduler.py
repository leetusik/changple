import logging
from datetime import datetime, timedelta

import django_rq
from rq_scheduler import Scheduler

from scraper.tasks import run_scheduled_crawler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("scheduler.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_scheduler():
    """Get or create Redis scheduler instance"""
    return Scheduler(connection=django_rq.get_connection("default"))


def schedule_crawler(hour=3, minute=0):
    """
    Schedule the crawler to run daily at the specified time in UTC

    Args:
        hour: Hour of day to run in UTC (0-23, default 3 = 3 AM UTC)
        minute: Minute of hour to run (0-59, default 0)
    """
    scheduler = get_scheduler()

    # Clear any existing scheduled jobs with the same name
    for job in scheduler.get_jobs():
        if job.meta.get("job_name") == "daily_crawler":
            logger.info(f"Removing existing scheduled job: {job.id}")
            scheduler.cancel(job)

    # Calculate when the first run should happen
    now_utc = datetime.utcnow()
    target_time_utc = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If the target time for today has already passed, schedule for tomorrow
    if target_time_utc < now_utc:
        target_time_utc = target_time_utc + timedelta(days=1)

    logger.info(f"Scheduling daily crawler job to run at {hour:02d}:{minute:02d} UTC")
    job = scheduler.schedule(
        scheduled_time=target_time_utc,  # First execution time
        func=run_scheduled_crawler,  # Function to call
        args=[],  # No fixed args
        kwargs={},  # No fixed kwargs
        interval=86400,  # 24 hours in seconds
        repeat=None,  # Repeat indefinitely
        meta={"job_name": "daily_crawler"},  # Metadata for job identification
    )

    logger.info(
        f"Scheduled crawler job with ID: {job.id} - First run at {target_time_utc.isoformat()} UTC"
    )
    return job


def schedule_custom_crawler(
    start_id=None, end_id=None, schedule_time=None, interval=None, immediate=False
):
    """
    Schedule a custom crawler job

    Args:
        start_id: Starting post ID (optional)
        end_id: Ending post ID (optional)
        schedule_time: Time to run the job in UTC (default: now)
        interval: Repeat interval in seconds (default: None = no repeat)
        immediate: If True, run immediately instead of scheduling (default: False)
    """
    scheduler = get_scheduler()
    queue = django_rq.get_queue("default")
    schedule_time = schedule_time or datetime.utcnow()

    # Set up the job parameters
    kwargs = {"start_id": start_id, "end_id": end_id}
    meta = {"job_name": "custom_crawler"}

    if immediate:
        # Run immediately by enqueueing directly in the queue
        logger.info(
            f"Enqueueing custom crawler job immediately with start_id={start_id}, end_id={end_id}"
        )
        job = queue.enqueue(run_scheduled_crawler, kwargs=kwargs, meta=meta)
        logger.info(
            f"Enqueued custom crawler job with ID: {job.id} - Running immediately"
        )
    else:
        # Schedule for later execution
        logger.info(
            f"Scheduling custom crawler job with start_id={start_id}, end_id={end_id}"
        )
        job = scheduler.schedule(
            scheduled_time=schedule_time,
            func=run_scheduled_crawler,
            args=[],
            kwargs=kwargs,
            interval=interval,
            repeat=None if interval else 0,
            meta=meta,
        )
        logger.info(
            f"Scheduled custom crawler job with ID: {job.id} - Will run at {schedule_time.isoformat()} UTC"
        )

    return job


def list_scheduled_jobs():
    """List all scheduled jobs"""
    scheduler = get_scheduler()
    jobs = list(scheduler.get_jobs())  # Convert generator to list

    logger.info(f"Found {len(jobs)} scheduled jobs:")
    for job in jobs:
        job_name = job.meta.get("job_name", "unnamed_job")

        # Get the scheduled time using rq-scheduler's API
        try:
            # Try to get scheduled time from the scheduler's API
            scheduled_time = scheduler.get_scheduled_time(job)
            schedule_time = scheduled_time.isoformat() if scheduled_time else "unknown"
        except (AttributeError, ValueError):
            # Fallback method - try parsing directly from redis
            schedule_time_bytes = scheduler.connection.zscore(
                "rq:scheduler:scheduled_jobs", job.id
            )
            if schedule_time_bytes is not None:
                try:
                    schedule_time = datetime.fromtimestamp(
                        float(schedule_time_bytes)
                    ).isoformat()
                except (ValueError, TypeError):
                    schedule_time = "unknown"
            else:
                schedule_time = "unknown"

        logger.info(
            f"Job ID: {job.id}, Name: {job_name}, Scheduled: {schedule_time} UTC"
        )

    return jobs


def cancel_all_jobs():
    """Cancel all scheduled jobs"""
    scheduler = get_scheduler()
    jobs = list(scheduler.get_jobs())  # Convert to list for accurate count

    for job in jobs:
        logger.info(f"Canceling job: {job.id}")
        scheduler.cancel(job)

    logger.info(f"Canceled {len(jobs)} scheduled jobs")
    return len(jobs)


def get_queue_status():
    """
    Get the current queue status

    Returns:
        dict: Current status of the queue
    """
    queue = django_rq.get_queue("default")
    registry = queue.failed_job_registry
    scheduled_registry = queue.scheduled_job_registry

    # Get counts
    queued_jobs = queue.count
    failed_jobs = len(registry.get_job_ids())
    scheduled_jobs = len(scheduled_registry.get_job_ids())

    status = {
        "queued": queued_jobs,
        "failed": failed_jobs,
        "scheduled": scheduled_jobs,
        "total": queued_jobs + failed_jobs + scheduled_jobs,
    }

    # Get all actual jobs for more detail
    jobs = []

    # Get queued jobs
    for job_id in queue.job_ids:
        job = queue.fetch_job(job_id)
        if job:
            jobs.append(
                {
                    "id": job.id,
                    "status": "queued",
                    "name": job.meta.get("job_name", "unnamed"),
                    "created_at": (
                        job.created_at.isoformat() if job.created_at else "unknown"
                    ),
                }
            )

    # Get failed jobs
    for job_id in registry.get_job_ids():
        job = queue.fetch_job(job_id)
        if job:
            jobs.append(
                {
                    "id": job.id,
                    "status": "failed",
                    "name": job.meta.get("job_name", "unnamed"),
                    "created_at": (
                        job.created_at.isoformat() if job.created_at else "unknown"
                    ),
                    "ended_at": job.ended_at.isoformat() if job.ended_at else "unknown",
                    "exc_info": job.exc_info,
                }
            )

    # Get scheduled jobs
    for job_id in scheduled_registry.get_job_ids():
        job = queue.fetch_job(job_id)
        if job:
            jobs.append(
                {
                    "id": job.id,
                    "status": "scheduled",
                    "name": job.meta.get("job_name", "unnamed"),
                    "created_at": (
                        job.created_at.isoformat() if job.created_at else "unknown"
                    ),
                }
            )

    status["jobs"] = jobs

    return status
