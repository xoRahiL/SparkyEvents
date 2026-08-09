import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_notification_email_now(subject, message, to_email):
    """Send an email directly in the current web request.

    This is used on the free Render service, where no Celery worker or Redis
    broker is available.
    """
    html_body = render_to_string('emails/notification.html', {
        'subject': subject,
        'message': message,
    })
    email = EmailMultiAlternatives(subject, message, settings.EMAIL_HOST_USER, [to_email])
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_notification_email_task(self, subject, message, to_email):
    """
    Runs on the Celery worker process, not the request thread.
    Sends a branded HTML email with a plain-text fallback (for email clients
    that don't render HTML), instead of a bare plain-text message.
    If SMTP hiccups, Celery retries up to 3 times (30s apart) before giving up,
    instead of failing the user's request or silently dropping the email.
    """
    try:
        send_notification_email_now(subject, message, to_email)
    except Exception as exc:
        logger.exception("Email send failed for %s, retrying...", to_email)
        raise self.retry(exc=exc)
