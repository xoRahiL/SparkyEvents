import logging
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.template.loader import render_to_string

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

    This is used on the free Render service, where SMTP is blocked. Brevo's
    HTTPS API sends the message without Celery, Redis, or Gmail SMTP.
    """
    html_body = render_to_string('emails/notification.html', {
        'subject': subject,
        'message': message,
    })
    if not settings.BREVO_API_KEY:
        logger.error(
            'Email not sent: BREVO_API_KEY is not configured. '
            'Add it to the Render environment variables.'
        )
        return False

    if not settings.BREVO_FROM_EMAIL:
        raise RuntimeError('BREVO_FROM_EMAIL is not configured.')

    payload = json.dumps({
        'sender': {
            'name': settings.BREVO_FROM_NAME,
            'email': settings.BREVO_FROM_EMAIL,
        },
        'to': [{'email': to_email}],
        'subject': subject,
        'htmlContent': html_body,
        'textContent': message,
    }).encode('utf-8')
    request = Request(
        'https://api.brevo.com/v3/smtp/email',
        data=payload,
        headers={
            'accept': 'application/json',
            'api-key': settings.BREVO_API_KEY,
            'content-type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=15) as response:
            response.read()
    except (HTTPError, URLError) as exc:
        logger.exception('Brevo email send failed for %s', to_email)
        raise RuntimeError(f'Brevo email send failed: {exc}') from exc
    return True


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_notification_email_task(self, subject, message, to_email):
    """
    Runs on the Celery worker process, not the request thread.
    Sends a branded HTML email with a plain-text fallback through Brevo.
    If the API hiccups, Celery retries up to 3 times (30s apart) before giving up,
    instead of failing the user's request or silently dropping the email.
    """
    try:
        send_notification_email_now(subject, message, to_email)
    except Exception as exc:
        logger.exception("Email send failed for %s, retrying...", to_email)
        raise self.retry(exc=exc)
