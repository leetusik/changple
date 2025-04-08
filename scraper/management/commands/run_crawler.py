import asyncio
import logging

from django.core.management.base import BaseCommand

from chatbot.services.ingest import ingest_docs

# Import crawler and ingestion functions
from scraper.services.crawler import main as run_crawler_main

# from chatbot.services.whoosh_service import create_whoosh_index


class Command(BaseCommand):
    help = "Run the Naver Cafe crawler, then update Whoosh index and Pinecone vectors"

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
        parser.add_argument(
            "--only-error",
            action="store_true",
            help="Only attempt to scrape posts with ERROR status",
        )
        parser.add_argument(
            "--skip-ingest",
            action="store_true",
            help="Skip the Whoosh and Pinecone ingestion steps after crawling",
        )

    def handle(self, *args, **options):
        # Configure logging based on verbosity
        log_level = logging.DEBUG if options["debug"] else logging.INFO
        # Ensure root logger is configured correctly
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Added logger name
            handlers=[
                logging.FileHandler("crawler_ingest.log"),  # Combined log file
                logging.StreamHandler(),
            ],
            force=True,  # Force reconfiguration in case other parts of Django setup logging
        )
        logger = logging.getLogger(__name__)  # Get logger for this module

        # Set custom parameters for the crawler
        crawler_params = {}
        if options["start_id"] is not None:
            crawler_params["start_id"] = options["start_id"]
        if options["end_id"] is not None:
            crawler_params["end_id"] = options["end_id"]
        if options["batch_size"] is not None:
            crawler_params["batch_size"] = options["batch_size"]
        if options["only_error"]:
            crawler_params["only_error"] = True

        # Run the crawler
        self.stdout.write(self.style.SUCCESS("Starting Naver Cafe crawler..."))
        logger.info("Starting Naver Cafe crawler...")
        if crawler_params:
            self.stdout.write(f"Using custom crawler parameters: {crawler_params}")
            logger.info(f"Using custom crawler parameters: {crawler_params}")

        try:
            asyncio.run(run_crawler_main(**crawler_params))
            self.stdout.write(self.style.SUCCESS("Crawler finished successfully."))
            logger.info("Crawler finished successfully.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Crawler failed: {e}"))
            logger.error(f"Crawler failed: {e}", exc_info=True)
            # Optionally decide whether to proceed with ingestion even if crawler fails
            # For now, we will stop if crawler fails.
            return

        # Check if ingestion should be skipped
        if options["skip_ingest"]:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping Whoosh and Pinecone ingestion steps as requested."
                )
            )
            logger.info("Skipping Whoosh and Pinecone ingestion steps as requested.")
            # else:
            #     # Run Whoosh Indexing
            #     self.stdout.write(self.style.SUCCESS("Starting Whoosh indexing..."))
            #     logger.info("Starting Whoosh indexing...")
            #     try:
            #         create_whoosh_index()
            #         self.stdout.write(
            #             self.style.SUCCESS("Whoosh indexing finished successfully.")
            #         )
            #         logger.info("Whoosh indexing finished successfully.")
            #     except Exception as e:
            #         self.stdout.write(self.style.ERROR(f"Whoosh indexing failed: {e}"))
            #         logger.error(f"Whoosh indexing failed: {e}", exc_info=True)
            #         # Decide if Pinecone ingestion should proceed if Whoosh fails
            #         # For now, we will attempt Pinecone even if Whoosh fails.

            # Run Pinecone Ingestion
            self.stdout.write(self.style.SUCCESS("Starting Pinecone ingestion..."))
            logger.info("Starting Pinecone ingestion...")
            try:
                ingest_docs()
                self.stdout.write(
                    self.style.SUCCESS("Pinecone ingestion finished successfully.")
                )
                logger.info("Pinecone ingestion finished successfully.")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Pinecone ingestion failed: {e}"))
                logger.error(f"Pinecone ingestion failed: {e}", exc_info=True)

        self.stdout.write(self.style.SUCCESS("Command finished."))
        logger.info("Command finished.")
