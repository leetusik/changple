from django.core.management.base import BaseCommand
from redis import Redis
from rq import Queue

from scraper.tasks import run_sync_db_with_cafe_data


class Command(BaseCommand):
    help = "Enqueue the cafe data sync RQ job"

    def handle(self, *args, **options):
        redis_conn = Redis()
        q = Queue("default", connection=redis_conn)
        job = q.enqueue(run_sync_db_with_cafe_data, job_timeout=36000)
        self.stdout.write(self.style.SUCCESS(f"Enqueued job with ID: {job.id}"))
