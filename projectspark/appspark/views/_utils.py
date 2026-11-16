"""
Shared utilities used by all view modules:
 - decorators (company_required, workhand_required)
 - email dispatch helper
 - category icon mapper
 - email message builders
 - OTP / password-reset helpers
"""
import logging
import datetime
import secrets
import threading
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.core.cache import cache
from django.shortcuts import redirect

from ..models import Company, Workhand
from ..tasks import send_notification_email_now

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role-enforcement decorators
# ---------------------------------------------------------------------------

def company_required(view_func):
    """
    Like @login_required, but also checks the logged-in user has a Company
    account. Without this, a workhand hitting a company-only URL crashes into
    an ugly unhandled error instead of being redirected somewhere sensible.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not Company.objects.filter(user=request.user).exists():
            messages.error(request, "That page is only available to company accounts.")
            return redirect('index')
        return view_func(request, *args, **kwargs)
    return wrapper


def workhand_required(view_func):
    """Same idea as company_required, for workhand-only pages."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not Workhand.objects.filter(user=request.user).exists():
            messages.error(request, "That page is only available to workhand accounts.")
            return redirect('index')
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Email dispatch — fire-and-forget background thread
# ---------------------------------------------------------------------------

def send_notification_email(subject, template_message, to_email):
    """Send email outside the request without requiring Celery."""
    def deliver():
        try:
            send_notification_email_now(subject, template_message, to_email)
        except Exception:
            logger.exception("Email send failed for %s", to_email)

    threading.Thread(target=deliver, name='notification-email', daemon=True).start()


# ---------------------------------------------------------------------------
# Category icon map — gives each event card a distinct Bootstrap icon
# ---------------------------------------------------------------------------

CATEGORY_ICONS = {
    "Wedding": "bi-heart-fill",
    "Birthday Party": "bi-cake2-fill",
    "Corporate Event": "bi-briefcase-fill",
    "Concert": "bi-music-note-beamed",
    "Conference": "bi-mic-fill",
    "Exhibition": "bi-easel-fill",
    "Product Launch": "bi-rocket-takeoff-fill",
    "Anniversary": "bi-gift-fill",
    "Baby Shower": "bi-balloon-heart-fill",
    "Graduation Party": "bi-mortarboard-fill",
    "Religious Ceremony": "bi-book-fill",
    "Sports Event": "bi-trophy-fill",
    "Festival": "bi-stars",
}


def attach_category_icons(events):
    """Attaches a `.category_icon` attribute to each event for template use."""
    for event in events:
        category_name = str(event.event_category) if event.event_category_id else None
        event.category_icon = CATEGORY_ICONS.get(category_name, "bi-calendar-event-fill")
    return events


# ---------------------------------------------------------------------------
# Email message builders
# ---------------------------------------------------------------------------

def welcome_message(name, role_line):
    return (
        f"Hi {name},\n\n"
        f"Welcome aboard! Your SparkyEvents account has been created successfully, "
        f"and you're all set to get started.\n\n"
        f"{role_line}\n\n"
        f"If you ever run into any issues or have questions along the way, feel free "
        f"to reach out to us anytime — we're happy to help.\n\n"
        f"Welcome to the community!\n\n"
        f"Warm regards,\n"
        f"The SparkyEvents Team"
    )


def login_alert_message(name):
    return (
        f"Hi {name},\n\n"
        f"We noticed a new login to your SparkyEvents account just now.\n\n"
        f"If this was you, there's nothing else you need to do. If you don't "
        f"recognize this activity, we recommend changing your password right away "
        f"from your profile settings to keep your account secure.\n\n"
        f"Stay safe,\n"
        f"The SparkyEvents Team"
    )


def application_approved_message(workhand_name, event_name, company_name):
    return (
        f"Hi {workhand_name},\n\n"
        f"Great news — {company_name} has reviewed and approved your application "
        f"for \"{event_name}\"!\n\n"
        f"Log in to your dashboard to view the full event details, including dates, "
        f"location, and payment information, so you're all set for the day.\n\n"
        f"Congratulations, and good luck!\n\n"
        f"Warm regards,\n"
        f"The SparkyEvents Team"
    )


def otp_message(name, otp):
    return (
        f"Hi {name},\n\n"
        f"Your SparkyEvents verification code is:\n\n"
        f"{otp}\n\n"
        f"This code expires in {OTP_EXPIRY_MINUTES} minutes. If you didn't request "
        f"this, you can safely ignore this email.\n\n"
        f"Warm regards,\n"
        f"The SparkyEvents Team"
    )


def password_reset_message(name, link):
    return (
        f"Hi {name},\n\n"
        f"We received a request to reset your SparkyEvents password. "
        f"Use the link below to choose a new one:\n\n"
        f"{link}\n\n"
        f"This link expires in {PASSWORD_RESET_MAX_AGE_SECONDS // 60} minutes and can only be used once. "
        f"If you didn't ask for this, you can safely ignore this email \u2014 your password won't change.\n\n"
        f"Warm regards,\n"
        f"The SparkyEvents Team"
    )


def password_changed_message(name):
    return (
        f"Hi {name},\n\n"
        f"The password on your SparkyEvents account was just changed.\n\n"
        f"If this was you, there's nothing else to do. If it wasn't, reset your "
        f"password right away using the \"Forgot password?\" link on the login page "
        f"and consider who else may have access to your email.\n\n"
        f"Stay safe,\n"
        f"The SparkyEvents Team"
    )


# ---------------------------------------------------------------------------
# OTP constants & helpers
# ---------------------------------------------------------------------------

OTP_EXPIRY_MINUTES = 15
OTP_RESEND_COOLDOWN_SECONDS = 60
MAX_OTP_ATTEMPTS = 5


def generate_otp():
    """Generate a cryptographically secure 6-digit numeric OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


# ---------------------------------------------------------------------------
# Password reset constants & helpers
# ---------------------------------------------------------------------------

PASSWORD_RESET_MAX_AGE_SECONDS = 60 * 60
PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS = 60
_PASSWORD_RESET_SALT = 'appspark.password-reset'


def make_reset_token(user, role):
    return signing.dumps(
        {'u': user.pk, 'r': role, 'p': user.password[-12:]},
        salt=_PASSWORD_RESET_SALT,
    )


def read_reset_token(token, role):
    """Return the User this token belongs to, or None if invalid/expired/used."""
    try:
        data = signing.loads(token, salt=_PASSWORD_RESET_SALT, max_age=PASSWORD_RESET_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data.get('u'), is_active=True).first()
    if user is None or data.get('r') != role or user.password[-12:] != data.get('p'):
        return None
    return user


# ---------------------------------------------------------------------------
# Role-agnostic auth helpers shared by workhand and company flows
# ---------------------------------------------------------------------------

def authenticate_role_user(identifier, password, role_model):
    """
    Authenticate by username or email, then enforce the account role.
    Returns (user_or_None, wrong_role_flag).
    """
    from django.db.models import Q
    identifier = identifier.strip()
    user = (User.objects
            .filter(Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True)
            .first())

    if user and user.check_password(password):
        if role_model.objects.filter(user=user).exists():
            return user, False
        return None, True

    return None, False
