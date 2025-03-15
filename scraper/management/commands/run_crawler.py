import asyncio

from django.core.management.base import BaseCommand

from scraper.services.crawler import main


class Command(BaseCommand):
    help = "Runs the Naver Cafe crawler"

    def handle(self, *args, **options):
        self.stdout.write("Starting the crawler...")
        asyncio.run(main())
        self.stdout.write(self.style.SUCCESS("Crawler finished successfully"))
