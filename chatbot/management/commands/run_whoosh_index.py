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
            # 인덱스 디렉토리 생성
            self.stdout.write('Creating index directory...')
            
            # 스키마 생성
            self.stdout.write('Creating schema...')
            
            # 문서 인덱싱
            self.stdout.write('Indexing documents...')
            
            # Whoosh 인덱스 생성 - 매개변수 없이 호출
            create_whoosh_index()
            
            self.stdout.write(self.style.SUCCESS('Successfully created Whoosh index'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating index: {str(e)}'))
