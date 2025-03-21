from django.core.management.base import BaseCommand
from django.db import transaction

from scraper.models import AllowedAuthor


class Command(BaseCommand):
    help = "Loads all allowed authors into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing authors before loading new ones",
        )

    def handle(self, *args, **options):
        # Authors from the provided list with their groups
        authors_by_group = {
            "창플": [
                "창플",
                "윤현진 본부장",
                "란본부장",
                "세연팀장",
                "나라과장",
                "박과장",
                "창플 유과장",
                "창플 미연",
                "창플 편집자",
                "창플리",
                "창플 윤과장",
            ],
            "팀비즈니스_브랜드_대표": [
                "칸스",
                "동백본가",
                "키즈더웨이브",
                "김태용",
                "명동닭튀김",
                "수컷웅",
                "라라와케이",
                "태권치킨",
                "만달",
                "JbebotT",
                "만달",
                "KRUNDI",
                "봄내농원",
                "미락",
            ],
            "기타": [],
        }

        with transaction.atomic():
            # Reset if requested
            if options["reset"]:
                self.stdout.write("Deleting all existing authors...")
                AllowedAuthor.objects.all().delete()
                self.stdout.write(self.style.SUCCESS("All authors deleted."))

            # Count existing authors to avoid duplicates
            existing_count = AllowedAuthor.objects.count()
            created_count = 0
            skipped_count = 0

            # Create authors with their respective groups
            for group, authors in authors_by_group.items():
                for author in authors:
                    # Check if author already exists
                    if AllowedAuthor.objects.filter(name=author).exists():
                        skipped_count += 1
                        continue

                    # Create the author
                    AllowedAuthor.objects.create(
                        name=author, author_group=group, is_active=True
                    )
                    created_count += 1

            # Print summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"Authors loaded successfully: {created_count} created, {skipped_count} skipped, {existing_count} already existed."
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Total authors in database: {AllowedAuthor.objects.count()}"
                )
            )