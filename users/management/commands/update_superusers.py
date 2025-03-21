from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import User


class Command(BaseCommand):
    help = "Update existing superusers to have admin user_type"

    def handle(self, *args, **options):
        with transaction.atomic():
            # Find all superusers that don't have admin user_type
            superusers = User.objects.filter(is_superuser=True, user_type="social")
            count = superusers.count()

            if count == 0:
                self.stdout.write(self.style.SUCCESS("No superusers need updating"))
                return

            # Update all of them to admin user_type
            superusers.update(user_type="admin")

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated {count} superusers to admin user_type"
                )
            )
