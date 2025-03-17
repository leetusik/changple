import asyncio
import logging

from django.core.management.base import BaseCommand

from scraper.services.crawler import main


class Command(BaseCommand):
    help = "Run the Naver Cafe crawler"

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-id",
            type=int,
            help="Starting post ID to crawl from (overrides the last post ID in database)",
        )
        parser.add_argument(
            "--end-id",
            type=int,
            help="Ending post ID to crawl to (inclusive)",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of posts to collect before saving to database (default: 100)",
        )

    def handle(self, *args, **options):
        # Configure logging based on verbosity
        log_level = logging.DEBUG if options["debug"] else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("naver_cafe_scraper.log"),
                logging.StreamHandler(),
            ],
        )

        # Set custom parameters for the crawler
        params = {}
        if options["start_id"] is not None:
            params["start_id"] = options["start_id"]
        if options["end_id"] is not None:
            params["end_id"] = options["end_id"]
        if options["batch_size"] is not None:
            params["batch_size"] = options["batch_size"]

        # Run the crawler
        self.stdout.write(self.style.SUCCESS("Starting Naver Cafe crawler..."))
        if params:
            self.stdout.write(f"Using custom parameters: {params}")

        asyncio.run(main(**params))

        self.stdout.write(self.style.SUCCESS("Crawler finished"))
