import logging

from django.core.management.base import BaseCommand, CommandError

from chatbot.services.ingest import ingest_docs

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the document ingestion process to Pinecone for allowed authors' non-vectorized posts"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting document ingestion process..."))

        try:
            ingest_docs()
            self.stdout.write(
                self.style.SUCCESS("Successfully completed document ingestion process")
            )
        except Exception as e:
            logger.error(f"Error during document ingestion: {e}")
            raise CommandError(f"Document ingestion failed: {e}")
