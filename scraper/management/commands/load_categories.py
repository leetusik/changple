from django.core.management.base import BaseCommand
from django.db import transaction

from scraper.models import AllowedCategory


class Command(BaseCommand):
    help = "Loads all categories from the Naver Cafe sidebar into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing categories before loading new ones",
        )

    def handle(self, *args, **options):
        # Categories from the Naver Cafe sidebar with their groups
        categories_by_group = {
            "창플지기_칼럼": [
                "창플지기 에세이",
                "초보창업자 전용 에세이",
                "예비사업가 전용 에세이",
                "초보들이 봐야 할 프랜차이즈 관련 에세이",
                "영상제작완료 에세이",
                "창업선배들 이야기",
            ],
            "창플_이야기": [
                "창플팀이 하는 일",
                "창플을 만드는 사람들",
                "창플 팀비즈(프랜차이즈)를 만드는 사람들",
                "창플과 함께하는 사람들",
                "창플 일상이야기",
                "창플 신규 프로젝트",
                "창플 백반기행",
                "창플 평냉로드",
                "창플 고성스테이",
                "창플 자영업자 마케팅",
            ],
            "창플_아키": [
                "창플 아키란?",
                "아키's Story",
                "Portfolio History",
                "Thanks to 아키",
                "Q&A",
            ],
            "창플_프랜차이즈": [
                "창플 프랜차이즈란?",
                "(주)키즈더웨이브",
                "(주)칸스",
                "(주)동백",
                "(주)평상집",
            ],
            "창플_팀비즈니스": [
                "창플 팀비즈니스 에세이",
                "칸스",
                "동백본가",
                "키즈더웨이브",
                "평상집",
                "김태용의 섬집",
                "압도",
                "명동닭튀김",
                "빙플",
                "수컷웅",
                "라라와케이",
                "태권치킨",
                "닭있소",
                "만달곰집",
                "753베이글비스트로",
                "크런디",
                "봄내농원",
                "오키나와펍 시사",
                "도림항",
                "오사카멘치",
                "어부장",
                "미락",
            ],
            "창플_파트너스": [
                "큐알로더",
                "유튜디오",
                "세무회계 함백",
                "법무법인 성지파트너스",
                "TSMIN 인테리어",
                "미엘 인테리어",
                "삼진키친",
                "[CanGo]Jeannie Lee대표",
                "한국기업컨설턴트협회",
                "라우드소싱",
            ],
            "알아두면_좋은_이야기": [
                "마케팅",
                "사장들의 이야기",
                "알아두면 좋은 이야기",
                "로스터현의 커피이야기",
                "의류디지털프린팅 창업",
            ],
            "창플_Youtube영상": [
                "창업과 자영업 이야기",
                "창플TV(제작)",
                "창플비즈니스TV(제작)",
            ],
            "창플인터뷰": [
                "사장들의인터뷰",
            ],
            "창플지기_상담": [
                "창플지기 상담후기",
                "창플지기 상담문의",
            ],
            "처음왔어요": [
                "가입인사",
                "창업 무엇부터?",
                "무엇이든 물어보세요!",
            ],
            "창플_커뮤니티": [
                "※공지사항",
                "출석체크",
                "식사하셨어요?",
                "어제오늘 어떠셨나요?",
                "자유 게시판",
            ],
            "창플카페_이용방법": [
                "창플설명서",
                "창플카페 이용Tip",
                "등업방법",
                "등업신청 게시판",
            ],
        }

        with transaction.atomic():
            # Reset if requested
            if options["reset"]:
                self.stdout.write("Deleting all existing categories...")
                AllowedCategory.objects.all().delete()
                self.stdout.write(self.style.SUCCESS("All categories deleted."))

            # Count existing categories to avoid duplicates
            existing_count = AllowedCategory.objects.count()
            created_count = 0
            skipped_count = 0

            # Create categories with their respective groups
            for group, categories in categories_by_group.items():
                for category in categories:
                    # Check if category already exists
                    if AllowedCategory.objects.filter(name=category).exists():
                        skipped_count += 1
                        continue

                    # Create the category
                    AllowedCategory.objects.create(
                        name=category, category_group=group, is_active=True
                    )
                    created_count += 1

            # Print summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"Categories loaded successfully: {created_count} created, {skipped_count} skipped, {existing_count} already existed."
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Total categories in database: {AllowedCategory.objects.count()}"
                )
            )
