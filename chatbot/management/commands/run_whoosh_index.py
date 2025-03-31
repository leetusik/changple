from django.core.management.base import BaseCommand
from chatbot.services.whoosh_service import create_whoosh_index
from scraper.models import NaverCafeData
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Initialize and build Whoosh index'

    def handle(self, *args, **options):
        self.stdout.write('Starting Whoosh indexing...')
        try:
            # create index directory
            self.stdout.write('Creating index directory...')
            
            # create schema
            self.stdout.write('Creating schema...')
            
            # index documents
            self.stdout.write('Indexing documents...')
            
            # create Whoosh index - call without parameters
            create_whoosh_index()
            
            self.stdout.write(self.style.SUCCESS('Successfully created Whoosh index'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating index: {str(e)}'))
