from django.contrib.auth import get_user_model
from django.contrib.auth.management.commands.createsuperuser import (
    Command as SuperUserCommand,
)
from django.db import transaction

User = get_user_model()


class Command(SuperUserCommand):
    help = "Create a superuser with the admin user type"

    def handle(self, *args, **options):
        # Call the parent class's handle method to create the superuser
        super().handle(*args, **options)

        # Get the username that was just created
        username = options.get("username")
        if not username:
            username = self.username_field.verbose_name

        # Update the user type to admin
        with transaction.atomic():
            try:
                # Get the most recently created superuser
                if username:
                    user = User.objects.get(**{User.USERNAME_FIELD: username})
                else:
                    # If no username was specified, get the most recent superuser
                    user = (
                        User.objects.filter(is_superuser=True)
                        .order_by("-date_joined")
                        .first()
                    )

                if user:
                    User.objects.filter(pk=user.pk).update(user_type="admin")
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully set user type to 'admin' for {user}"
                        )
                    )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR("Failed to find the created superuser")
                )
