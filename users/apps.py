from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "User Management"

    def ready(self):
        """
        Import and initialize tasks when Django starts
        """
        # Avoid circular imports
        # Schedule the daily query reset task
        # Only do this in the main process (not in Django's auto-reloader)
        import os

        import users.tasks

        if os.environ.get("RUN_MAIN") != "true":
            try:
                users.tasks.schedule_daily_query_limit_reset()
            except Exception as e:
                # Log but don't crash on startup
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to schedule daily query reset: {e}")
