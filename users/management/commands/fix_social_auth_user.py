"""
Management command to safely update social auth users without violating foreign key constraints.
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from social_django.models import UserSocialAuth

from users.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Safely update a social auth user"

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int, help="ID of user to update")
        parser.add_argument("--name", type=str, help="New name for user")
        parser.add_argument("--nickname", type=str, help="New nickname for user")
        parser.add_argument("--email", type=str, help="New email for user")
        parser.add_argument("--mobile", type=str, help="New mobile for user")
        parser.add_argument(
            "--daily_query_limit", type=int, help="New daily query limit"
        )
        parser.add_argument("--is_premium", type=bool, help="Premium status")

    def handle(self, *args, **options):
        user_id = options["user_id"]

        try:
            with transaction.atomic():
                # Get the user
                user = User.objects.get(id=user_id)
                self.stdout.write(
                    f"Updating user {user_id} - current name: {user.name}"
                )

                # Update user fields if provided
                if options.get("name"):
                    user.name = options["name"]
                if options.get("nickname"):
                    user.nickname = options["nickname"]
                if options.get("email"):
                    user.email = options["email"]
                if options.get("mobile"):
                    user.mobile = options["mobile"]
                if options.get("daily_query_limit") is not None:
                    user.daily_query_limit = options["daily_query_limit"]
                if options.get("is_premium") is not None:
                    user.is_premium = options["is_premium"]

                # Save the user without triggering cascading effects
                User.objects.filter(id=user_id).update(
                    name=user.name,
                    nickname=user.nickname,
                    email=user.email,
                    mobile=user.mobile,
                    daily_query_limit=user.daily_query_limit,
                    is_premium=user.is_premium,
                )

                self.stdout.write(
                    self.style.SUCCESS(f"Successfully updated user {user_id}")
                )

        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"User with ID {user_id} does not exist")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error updating user: {str(e)}"))
