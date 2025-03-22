import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from ..signals import log_email

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_plain_email(subject, message, recipients, from_email=None):
        """Send a plain text email"""
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL

        try:
            email = EmailMultiAlternatives(
                subject=subject, body=message, from_email=from_email, to=recipients
            )
            result = email.send()
            log_email(email, "sent")
            return result
        except Exception as e:
            logger.error(f"Error sending plain email: {str(e)}")
            if email:
                log_email(email, "failed", str(e))
            raise

    @staticmethod
    def send_template_email(subject, template, context, recipients, from_email=None):
        """Send an HTML email using a template"""
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL

        try:
            html_content = render_to_string(template, context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject, text_content, from_email, recipients
            )
            email.attach_alternative(html_content, "text/html")
            result = email.send()
            log_email(email, "sent")
            return result
        except Exception as e:
            logger.error(f"Error sending template email: {str(e)}")
            if "email" in locals():
                log_email(email, "failed", str(e))
            raise
