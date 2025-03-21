import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete all social users from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force deletion without confirmation prompt",
        )

    def handle(self, *args, **options):
        # Get the total count of social users
        social_user_count = User.objects.filter(user_type="social").count()

        if social_user_count == 0:
            self.stdout.write(
                self.style.WARNING("No social users found in the database.")
            )
            return

        self.stdout.write(
            self.style.WARNING(f"Found {social_user_count} social users to delete.")
        )

        # If not forced, ask for confirmation
        if not options["force"]:
            confirm = input(
                f"Are you sure you want to delete all {social_user_count} social users? "
                "This action cannot be undone. [y/N]: "
            )
            if confirm.lower() != "y":
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return

        try:
            with transaction.atomic():
                # Get list of usernames for logging (before deletion)
                usernames = list(
                    User.objects.filter(user_type="social").values_list(
                        "username", flat=True
                    )
                )

                # Delete all social users
                deleted_count, _ = User.objects.filter(user_type="social").delete()

                # Log the deletion
                for username in usernames:
                    logger.info(f"Deleted social user: {username}")

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully deleted {deleted_count} social users."
                    )
                )
        except Exception as e:
            logger.error(f"Error deleting social users: {e}")
            self.stdout.write(self.style.ERROR(f"Error deleting social users: {e}"))
