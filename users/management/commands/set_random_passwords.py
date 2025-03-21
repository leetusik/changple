import logging
import secrets
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import is_password_usable
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set random passwords for social users who have unusable passwords"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Set random passwords for all social users, not just ones with unusable passwords",
        )

    def handle(self, *args, **options):
        # Get social users
        if options["all"]:
            users = User.objects.filter(user_type="social")
            self.stdout.write(f"Found {users.count()} total social users.")
        else:
            # Only get users with unusable passwords
            users = []
            for user in User.objects.filter(user_type="social"):
                if not is_password_usable(user.password):
                    users.append(user)
            self.stdout.write(
                f"Found {len(users)} social users with unusable passwords."
            )

        if not users:
            self.stdout.write(self.style.SUCCESS("No users need password updates."))
            return

        try:
            with transaction.atomic():
                updated_count = 0
                for user in users:
                    # Generate a secure random password
                    alphabet = string.ascii_letters + string.digits + string.punctuation
                    password = "".join(secrets.choice(alphabet) for _ in range(20))

                    # Set the password
                    user.set_password(password)
                    user.save()

                    updated_count += 1
                    logger.info(
                        f"Set random password for user {user.username} (ID: {user.id})"
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully set random passwords for {updated_count} users."
                    )
                )
        except Exception as e:
            logger.error(f"Error setting random passwords: {e}")
            self.stdout.write(self.style.ERROR(f"Error setting random passwords: {e}"))
