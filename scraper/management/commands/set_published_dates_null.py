from django.core.management.base import BaseCommand
from django.db import transaction

from scraper.models import NaverCafeData


class Command(BaseCommand):
    help = "Sets all published_date fields to NULL in NaverCafeData table"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("Starting to update published_date fields...")
        )

        try:
            with transaction.atomic():
                # Count records before update
                total_records = NaverCafeData.objects.count()
                self.stdout.write(f"Found {total_records} records to update")

                # Update all records - set published_date to NULL
                updated_count = NaverCafeData.objects.update(published_date=None)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully set {updated_count} published_date fields to NULL"
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        "These posts will be re-scraped when the crawler runs to get the actual published dates"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error updating published_date fields: {e}")
            )
