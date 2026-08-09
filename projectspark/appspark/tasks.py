import logging

from django.conf import settings
from django.template.loader import render_to_string
import resend

try:
    # Optional future integration: the web app does not require Celery.
    from celery import shared_task
except ImportError:  # pragma: no cover - used only when Celery is absent
    def shared_task(*args, **kwargs):
        def decorator(function):
            return function
        return decorator

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
    if not settings.RESEND_API_KEY:
        logger.error(
            'Email not sent: RESEND_API_KEY is not configured. '
            'Add it to the Render environment variables.'
        )
        return False

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        'from': settings.RESEND_FROM_EMAIL,
        'to': [to_email],
        'subject': subject,
        'html': html_body,
        'text': message,
    })
    return True


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_notification_email_task(self, subject, message, to_email):
    """
    Runs on the Celery worker process, not the request thread.
    Sends a branded HTML email with a plain-text fallback through Resend.
    If the API hiccups, Celery retries up to 3 times (30s apart) before giving up,
    instead of failing the user's request or silently dropping the email.
    """
    try:
        send_notification_email_now(subject, message, to_email)
    except Exception as exc:
        logger.exception("Email send failed for %s, retrying...", to_email)
        raise self.retry(exc=exc)
