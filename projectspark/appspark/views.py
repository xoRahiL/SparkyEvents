import logging
import datetime
import random
import threading
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    WorkhandRegisterForm, CompanyRegisterForm, LoginForm,
    WorkhandProfileForm, CompanyProfileForm, EventForm, FeedbackForm,
)
from .models import (
    Workhand, WorkhandCategory, Company, Event, EventsCategory,
    WorkhandApplications, EventHistory, Feedback,
)
from .tasks import send_notification_email_now, send_notification_email_task

logger = logging.getLogger(__name__)

# Maps known event category names to a Bootstrap Icon class, used to give
# each event card a distinct visual identity instead of a plain text badge.
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
    """Attaches a `.category_icon` attribute to each event for template use.
    Falls back to a generic calendar icon for any category not in the map."""
    for event in events:
        category_name = str(event.event_category) if event.event_category_id else None
        event.category_icon = CATEGORY_ICONS.get(category_name, "bi-calendar-event-fill")
    return events


def company_required(view_func):
    """
    Like @login_required, but also checks the logged-in user actually has a
    Company account. Without this, a workhand hitting a company-only URL
    (or vice versa) crashes into an ugly, unhandled error instead of being
    redirected somewhere sensible.
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
# Small helpers.
# The free Render service has no Celery worker or Redis broker, so notification
# emails are sent directly in the current request.
# ---------------------------------------------------------------------------
def send_notification_email(subject, template_message, to_email):
    """Queue email work so external email latency never blocks a page load.

    Celery is used when configured. Render's single web service commonly has
    no worker, so use a short-lived background thread there as a graceful
    fallback. The request can redirect immediately while the email is sent.
    """
    if settings.USE_CELERY:
        send_notification_email_task.delay(subject, template_message, to_email)
        return

    def deliver():
        try:
            send_notification_email_now(subject, template_message, to_email)
        except Exception:
            logger.exception("Email send failed for %s", to_email)

    threading.Thread(target=deliver, name='notification-email', daemon=True).start()


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


OTP_EXPIRY_MINUTES = 15
OTP_RESEND_COOLDOWN_SECONDS = 60


def generate_otp():
    return str(random.randint(100000, 999999))


def authenticate_role_user(identifier, password, role_model):
    """Authenticate by username or email, then enforce the account role."""
    identifier = identifier.strip()
    user = (User.objects
            .filter(Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True)
            .first())
    if user and user.check_password(password) and role_model.objects.filter(user=user).exists():
        return user
    return None


def index(request):
    return render(request, 'index.html')


# ===========================================================================
# WORKHAND SIDE
# ===========================================================================
def workhand_register(request):
    cat = WorkhandCategory.objects.all()
    register_form = WorkhandRegisterForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if register_form.is_valid():
            data = register_form.cleaned_data
            propic_path = None
            if data.get('propic'):
                propic_path = default_storage.save(
                    f"pending_uploads/{data['username']}_{data['propic'].name}", data['propic']
                )

            otp = generate_otp()
            now = timezone.now()
            request.session['pending_workhand_registration'] = {
                'username': data['username'], 'email': data['email'], 'password': data['password'],
                'fname': data['fname'], 'lname': data['lname'], 'category_id': data['category'].id,
                'state': data.get('state', ''), 'city': data.get('city', ''),
                'propic_path': propic_path,
                'otp': otp,
                'expires_at': (now + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat(),
                'last_sent_at': now.isoformat(),
            }
            send_notification_email(
                "Your SparkyEvents verification code",
                otp_message(data['fname'], otp),
                data['email'],
            )
            messages.success(request, f"We've sent a 6-digit code to {data['email']}.")
            return redirect('verifyworkhandotp')
        else:
            for field_errors in register_form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

    return render(request, 'workdas/workhand_login.html', {'cat': cat, 'register_form': register_form})


def verify_workhand_otp(request):
    pending = request.session.get('pending_workhand_registration')
    if not pending:
        messages.error(request, "No pending registration found. Please register again.")
        return redirect('workhandregister')

    if request.method == 'POST':
        entered = request.POST.get('otp', '').strip()
        expires_at = datetime.datetime.fromisoformat(pending['expires_at'])
        if timezone.now() > expires_at:
            messages.error(request, "That code has expired. Request a new one below.")
        elif entered == pending['otp']:
            category = get_object_or_404(WorkhandCategory, id=pending['category_id'])
            myuser = User.objects.create_user(
                username=pending['username'], email=pending['email'], password=pending['password'],
                first_name=pending['fname'], last_name=pending['lname'],
            )
            Workhand.objects.create(
                user=myuser, workhand_category=category,
                state=pending.get('state', ''), city=pending.get('city', ''),
                profile_pic=pending.get('propic_path') or Workhand._meta.get_field('profile_pic').default,
            )
            send_notification_email(
                "Welcome to Sparky Events!",
                welcome_message(myuser.first_name, "You can now start applying for events as a WorkHand."),
                myuser.email,
            )
            del request.session['pending_workhand_registration']
            messages.success(request, 'Email verified! Your account is ready — please log in.')
            return redirect('workhandlogin')
        else:
            messages.error(request, "Incorrect code, please try again.")

    return render(request, 'workdas/verify_otp.html', {'email': pending['email']})


def resend_workhand_otp(request):
    pending = request.session.get('pending_workhand_registration')
    if not pending:
        messages.error(request, "No pending registration found.")
        return redirect('workhandregister')

    last_sent = datetime.datetime.fromisoformat(pending['last_sent_at'])
    if (timezone.now() - last_sent).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
        messages.error(request, "Please wait a bit before requesting another code.")
        return redirect('verifyworkhandotp')

    otp = generate_otp()
    now = timezone.now()
    pending['otp'] = otp
    pending['expires_at'] = (now + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
    pending['last_sent_at'] = now.isoformat()
    request.session['pending_workhand_registration'] = pending

    send_notification_email("Your SparkyEvents verification code", otp_message(pending['fname'], otp), pending['email'])
    messages.success(request, "A new code has been sent.")
    return redirect('verifyworkhandotp')


def workhand_login(request):
    cat = WorkhandCategory.objects.all()
    login_form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if login_form.is_valid():
            identifier = login_form.cleaned_data['username'].strip()
            password = login_form.cleaned_data['password']

            myuser = authenticate_role_user(identifier, password, Workhand)
            if myuser is not None:
                login(request, myuser)
                messages.success(request, "Successfully logged in!")
                send_notification_email(
                    "Login Alert", login_alert_message(myuser.first_name), myuser.email,
                )
                return redirect('workhanddashboard')

            messages.error(request, 'Invalid username or password!')

    return render(request, 'workdas/workhand_login.html', {'cat': cat, 'login_form': login_form})


def workhand_forget(request):
    return render(request, 'workdas/workhand_forget.html')


@workhand_required
def workhand_dashboard(request):
    wu = get_object_or_404(Workhand.objects.select_related('user', 'workhand_category'), user=request.user)

    eh = (EventHistory.objects
          .filter(workhand_id=wu)
          .select_related('event_category', 'workhand_category', 'company_id__user')[:5])
    attach_category_icons(eh)

    ap = WorkhandApplications.objects.filter(workhand=wu).select_related('event', 'to_company__user')
    pending_count = ap.filter(status=False).count()

    upcoming_gigs = (WorkhandApplications.objects
                      .filter(workhand=wu, status=True, event__start_date__gte=datetime.date.today())
                      .select_related('event__event_category', 'to_company__user')
                      .order_by('event__start_date')[:5])
    attach_category_icons([g.event for g in upcoming_gigs if g.event_id])

    total_earnings = EventHistory.objects.filter(workhand_id=wu).aggregate(total=Sum('payment_range'))['total'] or 0

    return render(request, 'workdas/workhand_dashboard.html', {
        'wu': wu, 'eh': eh, 'ap': ap, 'pending_count': pending_count,
        'upcoming_gigs': upcoming_gigs, 'total_earnings': total_earnings,
    })


@workhand_required
def workhand_profile(request):
    wu = get_object_or_404(Workhand.objects.select_related('user'), user=request.user)
    category = WorkhandCategory.objects.all().order_by('category')

    if request.method == 'POST':
        form = WorkhandProfileForm(request.POST, request.FILES, instance=wu)
        if form.is_valid():
            user = request.user
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['fname']
            user.last_name = form.cleaned_data['lname']
            user.email = form.cleaned_data['email']
            user.save()
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('workhandprofile')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    else:
        form = WorkhandProfileForm(instance=wu, initial={
            'username': wu.user.username, 'fname': wu.user.first_name,
            'lname': wu.user.last_name, 'email': wu.user.email,
        })

    return render(request, 'workdas/workhand_profile.html', {'wu': wu, 'cat': category, 'form': form})


@workhand_required
def workhand_change_password(request):
    get_object_or_404(Workhand, user=request.user)  # confirms this is a workhand account
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    return redirect(reverse('workhandprofile') + '#profile-change-password')


@workhand_required
def search_events(request):
    wu = get_object_or_404(Workhand, user=request.user)
    events = Event.objects.select_related('event_category', 'workhand_category', 'company_id__user').order_by('-id')

    selected_category = request.GET.get('category', '').strip()
    selected_city = request.GET.get('city', '').strip()

    if selected_category:
        events = events.filter(event_category_id=selected_category)
    if selected_city:
        events = events.filter(city__icontains=selected_city)

    paginator = Paginator(events, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    attach_category_icons(page_obj)

    applied_event_ids = set(
        WorkhandApplications.objects.filter(workhand=wu).values_list('event_id', flat=True)
    )

    return render(request, 'workdas/search_events.html', {
        'page_obj': page_obj, 'wu': wu, 'applied_event_ids': applied_event_ids,
        'categories': EventsCategory.objects.all(),
        'selected_category': selected_category, 'selected_city': selected_city,
    })


@workhand_required
def apply_for_event(request, id):
    wu = get_object_or_404(Workhand, user=request.user)
    applied_event = get_object_or_404(Event, id=id)

    required_fields = {
        'Contact number': wu.contact, 'Address': wu.address,
        'State': wu.state, 'City': wu.city,
    }
    missing = [label for label, value in required_fields.items() if not value]
    if missing:
        messages.error(
            request,
            f"Complete your profile before applying — missing: {', '.join(missing)}.",
        )
        return redirect('workhandprofile')

    try:
        with transaction.atomic():
            WorkhandApplications.objects.create(
                workhand=wu, to_company=applied_event.company_id, event=applied_event,
            )
    except IntegrityError:
        # The unique constraint on (workhand, event) caught a duplicate —
        # either this user double-clicked, or a near-simultaneous request
        # already created the application first. Either way, no duplicate
        # was created, and we tell the user the true current state.
        messages.error(request, 'Already applied — check your Approved Applications for status.')
        return redirect('searchevents')

    messages.success(request, "Successfully applied! Check status under Approved Applications.")
    return redirect('searchevents')


@workhand_required
def approved(request):
    wu = get_object_or_404(Workhand, user=request.user)
    applications = WorkhandApplications.objects.filter(workhand=wu).select_related(
        'event__event_category', 'to_company__user'
    ).order_by('-id')
    paginator = Paginator(applications, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    attach_category_icons([a.event for a in page_obj if a.event_id])
    return render(request, 'workdas/approved_applications.html', {'page_obj': page_obj, 'wu': wu})


@company_required
@require_POST
def mark_event_completed(request, id):
    company = get_object_or_404(Company, user=request.user)
    # Ownership check: only the company that owns this event can close it out.
    e = get_object_or_404(Event, id=id, company_id=company)

    approved_applications = WorkhandApplications.objects.filter(event=e, status=True).select_related('workhand')

    # Create one EventHistory record per approved workhand, so everyone who
    # actually worked the event keeps a real record of it (and can receive
    # feedback) - not just whichever person happened to close it out.
    for application in approved_applications:
        EventHistory.objects.create(
            event_name=e.event_name, description=e.description,
            start_date=e.start_date, end_date=e.end_date,
            event_category=e.event_category, workhand_category=e.workhand_category,
            workhand_needed=e.workhand_needed, payment_range=e.payment_range,
            address=e.address, state=e.state, city=e.city,
            company_id=e.company_id, workhand_id=application.workhand,
        )

    WorkhandApplications.objects.filter(event=e).delete()
    e.delete()

    messages.success(request, f"Event marked completed. {approved_applications.count()} workhand(s) recorded to history.")
    return redirect('manageevent')


@workhand_required
def workhand_logout(request):
    logout(request)
    messages.success(request, "Successfully logged out")
    return redirect('index')


# ===========================================================================
# COMPANY SIDE
# ===========================================================================
def company_register(request):
    register_form = CompanyRegisterForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if register_form.is_valid():
            data = register_form.cleaned_data
            propic_path = None
            if data.get('propic'):
                propic_path = default_storage.save(
                    f"pending_uploads/{data['username']}_{data['propic'].name}", data['propic']
                )

            otp = generate_otp()
            now = timezone.now()
            request.session['pending_company_registration'] = {
                'username': data['username'], 'email': data['email'], 'password': data['password'],
                'cname': data['cname'], 'state': data.get('state', ''), 'city': data.get('city', ''),
                'propic_path': propic_path,
                'otp': otp,
                'expires_at': (now + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat(),
                'last_sent_at': now.isoformat(),
            }
            send_notification_email(
                "Your SparkyEvents verification code",
                otp_message(data['cname'], otp),
                data['email'],
            )
            messages.success(request, f"We've sent a 6-digit code to {data['email']}.")
            return redirect('verifycompanyotp')
        else:
            for field_errors in register_form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

    return render(request, 'comdas/company_login.html', {'register_form': register_form})


def verify_company_otp(request):
    pending = request.session.get('pending_company_registration')
    if not pending:
        messages.error(request, "No pending registration found. Please register again.")
        return redirect('companyregister')

    if request.method == 'POST':
        entered = request.POST.get('otp', '').strip()
        expires_at = datetime.datetime.fromisoformat(pending['expires_at'])
        if timezone.now() > expires_at:
            messages.error(request, "That code has expired. Request a new one below.")
        elif entered == pending['otp']:
            myuser = User.objects.create_user(
                username=pending['username'], email=pending['email'], password=pending['password'],
                first_name=pending['cname'],
            )
            Company.objects.create(
                user=myuser, company_name=pending['cname'],
                state=pending.get('state', ''), city=pending.get('city', ''),
                profile_pic=pending.get('propic_path') or Company._meta.get_field('profile_pic').default,
            )
            send_notification_email(
                "Welcome to Sparky Events!",
                welcome_message(myuser.first_name, "Start posting events and get them staffed faster."),
                myuser.email,
            )
            del request.session['pending_company_registration']
            messages.success(request, 'Email verified! Your account is ready — please log in.')
            return redirect('companylogin')
        else:
            messages.error(request, "Incorrect code, please try again.")

    return render(request, 'comdas/verify_otp.html', {'email': pending['email']})


def resend_company_otp(request):
    pending = request.session.get('pending_company_registration')
    if not pending:
        messages.error(request, "No pending registration found.")
        return redirect('companyregister')

    last_sent = datetime.datetime.fromisoformat(pending['last_sent_at'])
    if (timezone.now() - last_sent).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
        messages.error(request, "Please wait a bit before requesting another code.")
        return redirect('verifycompanyotp')

    otp = generate_otp()
    now = timezone.now()
    pending['otp'] = otp
    pending['expires_at'] = (now + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
    pending['last_sent_at'] = now.isoformat()
    request.session['pending_company_registration'] = pending

    send_notification_email("Your SparkyEvents verification code", otp_message(pending['cname'], otp), pending['email'])
    messages.success(request, "A new code has been sent.")
    return redirect('verifycompanyotp')


def company_login(request):
    login_form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if login_form.is_valid():
            identifier = login_form.cleaned_data['username'].strip()
            password = login_form.cleaned_data['password']

            myuser = authenticate_role_user(identifier, password, Company)
            if myuser is not None:
                login(request, myuser)
                messages.success(request, "Login successful!")
                send_notification_email(
                    "Login Alert", login_alert_message(myuser.first_name), myuser.email,
                )
                return redirect('companydashboard')

            messages.error(request, 'Invalid username or password!')

    return render(request, 'comdas/company_login.html', {'login_form': login_form})


def company_forget(request):
    return render(request, 'comdas/company_forget.html')


@company_required
def company_dashboard(request):
    company = get_object_or_404(Company, user=request.user)
    events = (Event.objects
              .filter(company_id=company)
              .select_related('event_category', 'workhand_category')
              .annotate(approved_count=Count('workhandapplications', filter=Q(workhandapplications__status=True)))[:5])
    attach_category_icons(events)

    eh = EventHistory.objects.filter(company_id=company).select_related('workhand_id__user', 'event_category')[:5]
    attach_category_icons(eh)

    pending_count = WorkhandApplications.objects.filter(to_company=company, status=False).count()

    total_spend = EventHistory.objects.filter(company_id=company).aggregate(total=Sum('payment_range'))['total'] or 0

    upcoming_events = (Event.objects
                        .filter(company_id=company, start_date__gte=datetime.date.today())
                        .select_related('event_category')
                        .order_by('start_date')[:5])
    attach_category_icons(upcoming_events)

    return render(request, 'comdas/company_dashboard.html', {
        'events': events, 'c': company, 'eh': eh,
        'pending_count': pending_count, 'upcoming_events': upcoming_events, 'total_spend': total_spend,
    })


@company_required
def company_profile(request):
    cog = get_object_or_404(Company.objects.select_related('user'), user=request.user)

    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES, instance=cog)
        if form.is_valid():
            user = request.user
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['company_name']
            user.email = form.cleaned_data['email']
            user.save()
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('companyprofile')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    else:
        form = CompanyProfileForm(instance=cog, initial={
            'username': cog.user.username, 'company_name': cog.user.first_name, 'email': cog.user.email,
        })

    return render(request, 'comdas/company_profile.html', {'c': cog, 'form': form})


@company_required
def company_change_password(request):
    get_object_or_404(Company, user=request.user)  # confirms this is a company account
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keeps them logged in after the change
            messages.success(request, "Password changed successfully.")
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    return redirect(reverse('companyprofile') + '#profile-change-password')


@company_required
def post_event(request):
    ec = EventsCategory.objects.all().order_by('category')
    wc = WorkhandCategory.objects.all().order_by('category')
    company = get_object_or_404(Company, user=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.company_id = company
            event.save()
            messages.success(request, "Event posted successfully.")
            return redirect('manageevent')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    else:
        form = EventForm()

    return render(request, 'comdas/post_event.html', {'ec': ec, 'wc': wc, 'c': company, 'form': form})


@company_required
def update_event(request, id):
    ec = EventsCategory.objects.all()
    wc = WorkhandCategory.objects.all()
    company = get_object_or_404(Company, user=request.user)
    # Ownership check: only the company that owns this event can edit it.
    ed = get_object_or_404(Event, id=id, company_id=company)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=ed)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully.")
            return redirect('manageevent')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    else:
        form = EventForm(instance=ed)

    return render(request, 'comdas/update_event.html', {'ec': ec, 'wc': wc, 'ed': ed, 'c': company, 'form': form})


@company_required
@require_POST
def delete_event(request, id):
    company = get_object_or_404(Company, user=request.user)
    # Ownership check: prevents any company from deleting another company's event by ID-guessing.
    event = get_object_or_404(Event, id=id, company_id=company)
    event.delete()
    messages.success(request, "Event deleted.")
    return redirect("manageevent")


@company_required
def manage_event(request):
    company = get_object_or_404(Company, user=request.user)
    events = (Event.objects
              .filter(company_id=company)
              .select_related('event_category', 'workhand_category')
              .annotate(approved_count=Count('workhandapplications', filter=Q(workhandapplications__status=True)))
              .order_by('-id'))
    paginator = Paginator(events, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    attach_category_icons(page_obj)
    return render(request, 'comdas/manage.html', {'page_obj': page_obj, 'c': company})


@company_required
def approve_applications(request):
    company = get_object_or_404(Company, user=request.user)
    applications = (WorkhandApplications.objects
                     .filter(to_company=company)
                     .select_related('workhand__user', 'event__event_category')
                     .order_by('-id'))
    paginator = Paginator(applications, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    attach_category_icons([a.event for a in page_obj if a.event_id])
    return render(request, 'comdas/approve_applications.html', {'page_obj': page_obj, 'c': company})


@company_required
@require_POST
def approve_app(request, id):
    company = get_object_or_404(Company, user=request.user)

    with transaction.atomic():
        # select_for_update locks this application's event row until the
        # transaction commits, so two approvals racing for the last slot
        # are forced to happen one after another, not both at once.
        application = get_object_or_404(
            WorkhandApplications.objects.select_for_update(), id=id, to_company=company
        )
        event = get_object_or_404(Event.objects.select_for_update(), id=application.event_id)

        approved_count = WorkhandApplications.objects.filter(event=event, status=True).count()
        if approved_count >= event.workhand_needed:
            messages.error(request, f"All {event.workhand_needed} slot(s) for this event are already filled.")
            return redirect('approveapplications')

        application.status = True
        application.save(update_fields=['status'])

    send_notification_email(
        f"Application Approved - {event.event_name}",
        application_approved_message(
            application.workhand.user.first_name, event.event_name, company.user.first_name,
        ),
        application.workhand.user.email,
    )
    return redirect('approveapplications')


@company_required
@require_POST
def reject_app(request, id):
    company = get_object_or_404(Company, user=request.user)
    application = get_object_or_404(WorkhandApplications, id=id, to_company=company)
    application.delete()
    return redirect('approveapplications')


@company_required
def workhand_details(request, id):
    company = get_object_or_404(Company, user=request.user)
    wu = get_object_or_404(Workhand.objects.select_related('user', 'workhand_category'), id=id)
    return render(request, 'comdas/workhand_details.html', {'wu': wu, 'c': company})


@company_required
def company_logout(request):
    logout(request)
    messages.success(request, "Successfully logged out")
    return redirect('index')


@workhand_required
def workhand_event_history(request):
    wu = get_object_or_404(Workhand, user=request.user)
    eh = EventHistory.objects.filter(workhand_id=wu).select_related('company_id__user', 'event_category').order_by('-id')
    paginator = Paginator(eh, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    attach_category_icons(page_obj)
    return render(request, 'workdas/history.html', {'page_obj': page_obj, 'wu': wu})


@company_required
def company_event_history(request):
    company = get_object_or_404(Company, user=request.user)
    eh = EventHistory.objects.filter(company_id=company).select_related('workhand_id__user', 'event_category').order_by('-id')
    paginator = Paginator(eh, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    attach_category_icons(page_obj)
    return render(request, 'comdas/event_history.html', {'page_obj': page_obj, 'c': company})


@company_required
def company_feedback(request, id):
    company = get_object_or_404(Company, user=request.user)

    if request.method == 'POST':
        # Ownership check: the event-history record must belong to this company.
        eh = get_object_or_404(EventHistory, id=id, company_id=company)
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.date = datetime.date.today()
            feedback.event_id = eh
            feedback.workhand_id = eh.workhand_id
            feedback.company_id = company
            feedback.save()
            messages.success(request, "Feedback submitted.")
            return redirect('companyeventhistory')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    else:
        form = FeedbackForm()

    return render(request, 'comdas/feedback.html', {'id': id, 'c': company, 'form': form})


@workhand_required
def workhand_feedback(request, eid):
    wu = get_object_or_404(Workhand, user=request.user)
    # Ownership check: only view feedback tied to your own completed event.
    eh = get_object_or_404(EventHistory, id=eid, workhand_id=wu)

    try:
        fb = Feedback.objects.select_related('company_id__user').get(event_id=eh)
    except Feedback.DoesNotExist:
        messages.error(request, "No feedback received for this event yet!")
        return redirect('workhandeventhistory')

    return render(request, 'workdas/feedback_details.html', {'fb': fb})
