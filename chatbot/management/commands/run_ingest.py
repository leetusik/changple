import logging

from django.core.management.base import BaseCommand, CommandError

from chatbot.services.ingest import ingest_docs
from chatbot.services.whoosh_service import create_whoosh_index

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Whoosh 인덱스를 생성하고 Pinecone에 문서를 인제스트하는 통합 프로세스 실행"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Whoosh 인덱스 생성 및 문서 인제스트 프로세스 시작..."))

        try:
            # 1단계: Whoosh 인덱스 생성
            self.stdout.write(self.style.SUCCESS("Whoosh 인덱스 생성 중..."))
            create_whoosh_index()
            self.stdout.write(self.style.SUCCESS("Whoosh 인덱스 생성 완료"))
            
            # 2단계: Pinecone 인제스트 실행
            self.stdout.write(self.style.SUCCESS("Pinecone 문서 인제스트 중..."))
            ingest_docs()
            self.stdout.write(self.style.SUCCESS("Pinecone 문서 인제스트 완료"))
            
            # 3단계: 두 과정이 모두 완료된 후 vectorized 플래그 업데이트
            self.stdout.write(self.style.SUCCESS("문서의 vectorized 플래그 업데이트 중..."))
            from scraper.models import AllowedAuthor, NaverCafeData
            allowed_authors = list(
                AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
            )
            updated_count = NaverCafeData.objects.filter(
                author__in=allowed_authors, vectorized=False
            ).update(vectorized=True)
            self.stdout.write(self.style.SUCCESS(f"vectorized 플래그 업데이트 완료"))
            
            self.stdout.write(
                self.style.SUCCESS("Whoosh 인덱스 생성 및 문서 인제스트 완료")
            )
        except Exception as e:
            logger.error(f"인덱싱 및 인제스트 중 오류 발생: {e}")
            raise CommandError(f"인덱싱 및 인제스트 실패: {e}")
