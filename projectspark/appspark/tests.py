import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

try:
    # Keep the test/future worker task without making Celery required.
    from celery import shared_task
except ImportError:  # pragma: no cover
    def shared_task(*args, **kwargs):
        def decorator(function):
            return function
        return decorator

logger = logging.getLogger(__name__)


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
        html_body = render_to_string('emails/notification.html', {
            'subject': subject,
            'message': message,
        })
        email = EmailMultiAlternatives(subject, message, settings.EMAIL_HOST_USER, [to_email])
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Email send failed for %s", to_email)
        if settings.USE_CELERY:
            # Only retry through Celery's own queue when a worker/broker is
            # actually running - retrying without one would just raise a
            # second, unrelated "can't connect to broker" error.
            raise self.retry(exc=exc)


from django.test import TestCase

# Create your tests here.
