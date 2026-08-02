import logging
import datetime
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import (
    WorkhandRegisterForm, CompanyRegisterForm, LoginForm,
    WorkhandProfileForm, CompanyProfileForm, EventForm, FeedbackForm,
)
from .models import (
    Workhand, WorkhandCategory, Company, Event, EventsCategory,
    WorkhandApplications, EventHistory, Feedback,
)
from .tasks import send_notification_email_task

logger = logging.getLogger(__name__)


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
# send_notification_email now just hands the work to Celery (.delay()) and
# returns immediately — the actual SMTP call happens on a separate worker
# process, so the user's request never waits on it.
# ---------------------------------------------------------------------------
def send_notification_email(subject, template_message, to_email):
    send_notification_email_task.delay(subject, template_message, to_email)


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
            myuser = User.objects.create_user(
                username=data['username'], email=data['email'], password=data['password'],
                first_name=data['fname'], last_name=data['lname'],
            )
            Workhand.objects.create(
                user=myuser,
                workhand_category=data['category'],
                profile_pic=data.get('propic') or Workhand._meta.get_field('profile_pic').default,
            )

            send_notification_email(
                "Welcome to Sparky Events!",
                welcome_message(myuser.first_name, "You can now start applying for events as a WorkHand."),
                myuser.email,
            )
            messages.success(request, 'Successfully registered. You can now log in!')
            return redirect('workhandlogin')
        else:
            for field_errors in register_form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

    return render(request, 'workdas/workhand_login.html', {'cat': cat, 'register_form': register_form})


def workhand_login(request):
    cat = WorkhandCategory.objects.all()
    login_form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']

            if Workhand.objects.filter(user__username=username).exists():
                myuser = authenticate(request, username=username, password=password)
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

    ap = WorkhandApplications.objects.filter(workhand=wu).select_related('event', 'to_company__user')

    return render(request, 'workdas/workhand_dashboard.html', {'wu': wu, 'eh': eh, 'ap': ap})


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


@login_required
def search_events(request):
    wu = get_object_or_404(Workhand, user=request.user)
    events = Event.objects.select_related('event_category', 'workhand_category', 'company_id__user')
    applied_event_ids = set(
        WorkhandApplications.objects.filter(workhand=wu).values_list('event_id', flat=True)
    )
    return render(request, 'workdas/search_events.html', {
        'events': events, 'wu': wu, 'applied_event_ids': applied_event_ids,
    })


@workhand_required
def apply_for_event(request, id):
    wu = get_object_or_404(Workhand, user=request.user)
    applied_event = get_object_or_404(Event, id=id)

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
    app = WorkhandApplications.objects.filter(workhand=wu).select_related('event', 'to_company__user')
    return render(request, 'workdas/approved_applications.html', {'app': app, 'wu': wu})


@workhand_required
@require_POST
def event_completed(request, id):
    wu = get_object_or_404(Workhand, user=request.user)
    # Ownership check: this application must belong to the logged-in workhand.
    workhand_application = get_object_or_404(WorkhandApplications, id=id, workhand=wu)
    e = get_object_or_404(Event, id=workhand_application.event_id)

    EventHistory.objects.create(
        event_name=e.event_name, description=e.description,
        start_date=e.start_date, end_date=e.end_date,
        event_category=e.event_category, workhand_category=e.workhand_category,
        workhand_needed=e.workhand_needed, payment_range=e.payment_range,
        address=e.address, state=e.state, city=e.city,
        company_id=e.company_id, workhand_id=wu,
    )

    workhand_application.delete()
    WorkhandApplications.objects.filter(event=e).delete()
    e.delete()

    return redirect('approved')


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
            myuser = User.objects.create_user(
                username=data['username'], email=data['email'], password=data['password'],
                first_name=data['cname'],
            )
            Company.objects.create(
                user=myuser, company_name=data['cname'],
                profile_pic=data.get('propic') or Company._meta.get_field('profile_pic').default,
            )
            send_notification_email(
                "Welcome to Sparky Events!",
                welcome_message(myuser.first_name, "Start posting events and get them staffed faster."),
                myuser.email,
            )
            messages.success(request, 'Successfully registered. You can now log in!')
            return redirect('companylogin')
        else:
            for field_errors in register_form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

    return render(request, 'comdas/company_login.html', {'register_form': register_form})


def company_login(request):
    login_form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']

            if Company.objects.filter(user__username=username).exists():
                myuser = authenticate(request, username=username, password=password)
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
    events = Event.objects.filter(company_id=company).select_related('event_category', 'workhand_category')
    eh = EventHistory.objects.filter(company_id=company).select_related('workhand_id__user')[:5]
    return render(request, 'comdas/company_dashboard.html', {'events': events, 'c': company, 'eh': eh})


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
    events = Event.objects.filter(company_id=company).select_related('event_category', 'workhand_category')
    return render(request, 'comdas/manage.html', {'events': events, 'c': company})


@company_required
def approve_applications(request):
    company = get_object_or_404(Company, user=request.user)
    applications = (WorkhandApplications.objects
                     .filter(to_company=company)
                     .select_related('workhand__user', 'event'))
    return render(request, 'comdas/approve_applications.html', {'app': applications, 'c': company})


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
    eh = EventHistory.objects.filter(workhand_id=wu).select_related('company_id__user')
    return render(request, 'workdas/history.html', {'eh': eh, 'wu': wu})


@company_required
def company_event_history(request):
    company = get_object_or_404(Company, user=request.user)
    eh = EventHistory.objects.filter(company_id=company).select_related('workhand_id__user')
    return render(request, 'comdas/event_history.html', {'eh': eh, 'c': company})


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