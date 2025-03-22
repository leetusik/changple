import logging

from .models import EmailLog

logger = logging.getLogger(__name__)


def log_email(email, status="sent", error_message=None):
    """Log an email in the database"""
    try:
        # Extract recipient from the email - take only the first recipient for logging
        recipient = email.to[0] if email.to else "unknown"

        # Create log entry
        log_entry = EmailLog.objects.create(
            recipient=recipient, subject=email.subject, status=status
        )

        if status == "sent":
            log_entry.mark_as_sent()
        elif status == "failed":
            log_entry.mark_as_failed(error_message)

        return log_entry
    except Exception as e:
        logger.error(f"Failed to log email: {str(e)}")
        return None
