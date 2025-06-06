import logging

import django_rq

from .services.email_service import EmailService

logger = logging.getLogger(__name__)


@django_rq.job("default", timeout=60)
def send_notification_email(
    user_email, subject, message, template="notifications/email/notification.html"
):
    """Send generic notification email"""
    try:
        logger.info(f"Sending notification email to {user_email}: {subject}")
        return EmailService.send_template_email(
            subject=subject,
            template=template,
            context={"message": message},
            recipients=[user_email],
        )
    except Exception as e:
        logger.error(f"Failed to send notification email to {user_email}: {str(e)}")
        raise


@django_rq.job("default", timeout=60)
def send_password_reset_email(user_email, reset_link):
    """Send password reset email"""
    try:
        logger.info(f"Sending password reset email to {user_email}")
        return EmailService.send_template_email(
            subject="Reset Your Password",
            template="notifications/email/password_reset.html",
            context={"reset_link": reset_link},
            recipients=[user_email],
        )
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")
        raise


@django_rq.job("default", timeout=60)
def send_subscription_confirmation_email(
    user_email, user_name, plan_name, plan_details
):
    """Send subscription confirmation email"""
    try:
        logger.info(f"Sending subscription confirmation email to {user_email}")
        return EmailService.send_template_email(
            subject="Subscription Confirmation",
            template="notifications/email/subscription_confirmation.html",
            context={
                "user_name": user_name,
                "plan_name": plan_name,
                "plan_details": plan_details,
            },
            recipients=[user_email],
        )
    except Exception as e:
        logger.error(
            f"Failed to send subscription confirmation email to {user_email}: {str(e)}"
        )
        raise


@django_rq.job("default", timeout=60)
def send_consultation_request_email(
    host_email, user_email, chat_history, additional_message=""
):
    """Send 1:1 consultation request email with chat history to host"""
    try:
        logger.info(f"Sending consultation request from {user_email} to {host_email}")
        subject = f"1:1 상담 요청 - {user_email}"

        return EmailService.send_template_email(
            subject=subject,
            template="notifications/email/consultation_request.html",
            context={
                "user_email": user_email,
                "chat_history": chat_history,
                "additional_message": additional_message,
            },
            recipients=[host_email],
        )
    except Exception as e:
        logger.error(f"Failed to send consultation request email: {str(e)}")
        raise
