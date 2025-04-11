"""
Asynchronous tasks for the users application.
This module contains tasks for background processing related to user accounts.
"""

import logging

import django_rq
from django.utils import timezone
from rq_scheduler import Scheduler

from users.models import User

logger = logging.getLogger(__name__)


def reset_daily_query_limits():
    """
    Reset daily_queries_used to 0 for all users and update the last_query_reset timestamp.
    This task should be scheduled to run daily at 15:00 UTC.
    """
    try:
        count = User.objects.update(
            daily_queries_used=0, last_query_reset=timezone.now()
        )
        logger.info(f"Reset daily query limits for {count} users")
        return count
    except Exception as e:
        logger.error(f"Error resetting daily query limits: {e}")
        raise


def schedule_daily_query_limit_reset():
    """
    Schedule the daily query limit reset task to run at 15:00 UTC every day.
    This function should be called once during application startup.
    """
    scheduler = Scheduler(connection=django_rq.get_connection("default"))

    # Remove any existing scheduled jobs with the same function
    for job in scheduler.get_jobs():
        if job.func_name == "users.tasks.reset_daily_query_limits":
            scheduler.cancel(job)

    # Schedule the task to run daily at 15:00 UTC
    scheduler.cron(
        "0 15 * * *",  # Cron syntax: minute hour day_of_month month day_of_week
        func=reset_daily_query_limits,
        repeat=None,  # Run indefinitely
        queue_name="default",
    )

    logger.info("Scheduled daily query limit reset task to run at 15:00 UTC")
