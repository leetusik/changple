import logging
from datetime import datetime

from django.core.management.base import BaseCommand

from scraper.services.scheduler import (
    cancel_all_jobs,
    get_queue_status,
    get_scheduler,
    list_scheduled_jobs,
    schedule_crawler,
    schedule_custom_crawler,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manage scheduled crawler jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            type=str,
            choices=["start", "list", "cancel", "custom", "status"],
            help="Action to perform (start, list, cancel, custom, status)",
        )

        # Arguments for daily schedule
        parser.add_argument(
            "--hour",
            type=int,
            default=3,
            help="Hour of day to run daily crawler in UTC (0-23, default: 3)",
        )
        parser.add_argument(
            "--minute",
            type=int,
            default=0,
            help="Minute of hour to run daily crawler in UTC (0-59, default: 0)",
        )

        # Arguments for custom schedule
        parser.add_argument(
            "--start-id",
            type=int,
            help="Starting post ID for custom crawler",
        )
        parser.add_argument(
            "--end-id",
            type=int,
            help="Ending post ID for custom crawler",
        )
        parser.add_argument(
            "--interval",
            type=int,
            help="Interval in seconds for repeating custom jobs",
        )
        parser.add_argument(
            "--now",
            action="store_true",
            help="Run the custom crawler job immediately (don't schedule)",
        )

    def handle(self, *args, **options):
        action = options["action"]

        try:
            if action == "start":
                hour = options["hour"]
                minute = options["minute"]
                job = schedule_crawler(hour=hour, minute=minute)

                # Find when the first run will happen from the job metadata
                first_run = "unknown"
                if hasattr(job, "scheduled_at") and job.scheduled_at:
                    first_run = job.scheduled_at.isoformat()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully scheduled daily crawler job (ID: {job.id})\n"
                        f"- Will run at {hour:02d}:{minute:02d} UTC every day\n"
                        f"- First execution scheduled for: {first_run} UTC"
                    )
                )

            elif action == "custom":
                start_id = options.get("start_id")
                end_id = options.get("end_id")
                interval = options.get("interval")
                immediate = options.get("now", False)

                job = schedule_custom_crawler(
                    start_id=start_id,
                    end_id=end_id,
                    interval=interval,
                    immediate=immediate,
                )

                if immediate:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Custom crawler job enqueued for immediate execution (ID: {job.id})\n"
                            f"- Crawling posts from ID {start_id or 'last'} to {end_id or 'latest'}\n"
                            f"- Check worker output for progress"
                        )
                    )
                else:
                    interval_text = (
                        f" (repeating every {interval} seconds)" if interval else ""
                    )

                    run_time = "unknown"
                    if hasattr(job, "scheduled_at") and job.scheduled_at:
                        run_time = job.scheduled_at.isoformat()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Custom crawler job scheduled (ID: {job.id}){interval_text}\n"
                            f"- Will crawl posts from ID {start_id or 'last'} to {end_id or 'latest'}\n"
                            f"- Scheduled to run at: {run_time} UTC"
                        )
                    )

            elif action == "list":
                scheduler = get_scheduler()
                jobs = list_scheduled_jobs()

                if not jobs:
                    self.stdout.write("No scheduled jobs found.")
                else:
                    self.stdout.write(f"Found {len(jobs)} scheduled jobs:")
                    for job in jobs:
                        job_name = job.meta.get("job_name", "unnamed_job")

                        # Get the scheduled time using rq-scheduler's API
                        try:
                            # Try to get scheduled time from the scheduler's API
                            scheduled_time = scheduler.get_scheduled_time(job)
                            schedule_time = (
                                scheduled_time.isoformat()
                                if scheduled_time
                                else "unknown"
                            )
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

                        self.stdout.write(f"Job ID: {job.id}")
                        self.stdout.write(f"- Name: {job_name}")
                        self.stdout.write(f"- Scheduled: {schedule_time} UTC")

            elif action == "cancel":
                count = cancel_all_jobs()
                self.stdout.write(
                    self.style.SUCCESS(f"Canceled {count} scheduled jobs")
                )

            elif action == "status":
                status = get_queue_status()

                self.stdout.write(self.style.SUCCESS(f"RQ Queue Status Summary:"))
                self.stdout.write(f"- Queued jobs: {status['queued']}")
                self.stdout.write(f"- Scheduled jobs: {status['scheduled']}")
                self.stdout.write(f"- Failed jobs: {status['failed']}")
                self.stdout.write(f"- Total jobs: {status['total']}")

                if status["total"] > 0:
                    self.stdout.write("\nDetailed Job Information:")

                    for job in status["jobs"]:
                        self.stdout.write(
                            f"Job ID: {job['id']}\n"
                            f"- Status: {job['status']}\n"
                            f"- Name: {job['name']}\n"
                            f"- Created: {job['created_at']}"
                        )

                        # Add failure info if available
                        if job["status"] == "failed" and "exc_info" in job:
                            self.stdout.write(f"- Error: {job['exc_info'][:100]}...")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            logger.exception(e)
