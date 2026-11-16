"""
Seed demo data for SparkyEvents.

Usage (from the repo root):
    python projectspark/manage.py seed_demo
    python projectspark/manage.py seed_demo --password "MyDemoPass1"

Safe to re-run: accounts, events and applications are updated in place and
never duplicated. Event dates are re-based on today, so re-running also keeps
the demo events in the future.

Demo password priority: --password option > DEMO_PASSWORD env var > default.
"""
import os
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from appspark.models import (
    Company,
    Event,
    EventHistory,
    EventsCategory,
    Feedback,
    Workhand,
    WorkhandApplications,
    WorkhandCategory,
)

DEFAULT_PASSWORD = "Demo@12345"

COMPANY = {
    "username": "democompany",
    "email": "demo.company@example.com",
    "first_name": "Spark",
    "last_name": "Celebrations",
    "company_name": "Spark Celebrations",
    "contact": "9000000001",
    "address": "12 Event Plaza, Demo Street",
    "state": "Maharashtra",
    "city": "Mumbai",
}

WORKHANDS = [
    {
        "username": "demoworkhand",
        "email": "demo.workhand@example.com",
        "first_name": "Demo",
        "last_name": "Workhand",
        "contact": "9000000011",
        "address": "5 Demo Nagar",
        "state": "Maharashtra",
        "city": "Mumbai",
        "category": "Photography",
    },
    {
        "username": "demoworkhand2",
        "email": "demo.workhand2@example.com",
        "first_name": "Asha",
        "last_name": "Patel",
        "contact": "9000000012",
        "address": "21 Sample Colony",
        "state": "Gujarat",
        "city": "Ahmedabad",
        "category": "Catering",
    },
    {
        "username": "demoworkhand3",
        "email": "demo.workhand3@example.com",
        "first_name": "Ravi",
        "last_name": "Kumar",
        "contact": "9000000013",
        "address": "8 Test Layout",
        "state": "Karnataka",
        "city": "Bengaluru",
        "category": "Decoration",
    },
]

# start_in / length are in days from today.
EVENTS = [
    {
        "name": "Sharma Wedding Reception",
        "event_category": "Wedding",
        "workhand_category": "Photography",
        "needed": 3,
        "pay": 4500.0,
        "start_in": 14,
        "length": 1,
        "city": "Mumbai",
        "state": "Maharashtra",
        "address": "Grand Hall, Marine Drive",
        "description": "Evening reception for ~300 guests. Candid and stage photography needed.",
    },
    {
        "name": "TechNova Annual Conference",
        "event_category": "Conference",
        "workhand_category": "Catering",
        "needed": 10,
        "pay": 2200.0,
        "start_in": 21,
        "length": 2,
        "city": "Mumbai",
        "state": "Maharashtra",
        "address": "Convention Centre, BKC",
        "description": "Two-day corporate conference. Tea/coffee service and lunch counters.",
    },
    {
        "name": "Rooftop Birthday Bash",
        "event_category": "Birthday Party",
        "workhand_category": "Decoration",
        "needed": 4,
        "pay": 1800.0,
        "start_in": 30,
        "length": 1,
        "city": "Mumbai",
        "state": "Maharashtra",
        "address": "Sky Lounge, Andheri West",
        "description": "Balloon, lighting and backdrop setup for a 100-guest birthday party.",
    },
    {
        "name": "Winter Music Fest",
        "event_category": "Concert",
        "workhand_category": "Security",
        "needed": 20,
        "pay": 2600.0,
        "start_in": 45,
        "length": 3,
        "city": "Mumbai",
        "state": "Maharashtra",
        "address": "Open Grounds, Mahalaxmi",
        "description": "Crowd management and gate security for a three-day music festival.",
    },
]

# (workhand username, event name, approved?)
APPLICATIONS = [
    ("demoworkhand", "Sharma Wedding Reception", True),
    ("demoworkhand", "Rooftop Birthday Bash", False),
    ("demoworkhand2", "TechNova Annual Conference", False),
    ("demoworkhand2", "Sharma Wedding Reception", False),
    ("demoworkhand3", "Rooftop Birthday Bash", False),
]


def get_category(model, name):
    """Reuse the category if it exists (migration 0002 seeds most of them)."""
    obj = model.objects.filter(category=name).first()
    return obj or model.objects.create(category=name)


def upsert_user(data, password):
    user, _ = User.objects.update_or_create(
        username=data["username"],
        defaults={
            "email": data["email"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "is_active": True,
        },
    )
    user.set_password(password)
    user.save()
    return user


class Command(BaseCommand):
    help = "Create (or refresh) demo accounts, events, applications and history."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help="Password for all demo accounts (default: DEMO_PASSWORD env var, "
                 "else a built-in demo password).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"] or os.environ.get("DEMO_PASSWORD") or DEFAULT_PASSWORD
        today = date.today()

        # --- Company -------------------------------------------------------
        company_user = upsert_user(COMPANY, password)
        company, _ = Company.objects.update_or_create(
            user=company_user,
            defaults={
                "company_name": COMPANY["company_name"],
                "contact": COMPANY["contact"],
                "address": COMPANY["address"],
                "state": COMPANY["state"],
                "city": COMPANY["city"],
            },
        )

        # --- Workhands -----------------------------------------------------
        workhands = {}
        for w in WORKHANDS:
            user = upsert_user(w, password)
            workhands[w["username"]], _ = Workhand.objects.update_or_create(
                user=user,
                defaults={
                    "contact": w["contact"],
                    "address": w["address"],
                    "state": w["state"],
                    "city": w["city"],
                    "workhand_category": get_category(WorkhandCategory, w["category"]),
                },
            )

        # --- Upcoming events (dates re-based on today) ---------------------
        events = {}
        for e in EVENTS:
            start = today + timedelta(days=e["start_in"])
            events[e["name"]], _ = Event.objects.update_or_create(
                company_id=company,
                event_name=e["name"],
                defaults={
                    "event_category": get_category(EventsCategory, e["event_category"]),
                    "description": e["description"],
                    "start_date": start,
                    "end_date": start + timedelta(days=e["length"] - 1),
                    "workhand_category": get_category(WorkhandCategory, e["workhand_category"]),
                    "workhand_needed": e["needed"],
                    "payment_range": e["pay"],
                    "address": e["address"],
                    "state": e["state"],
                    "city": e["city"],
                },
            )

        # --- Applications --------------------------------------------------
        for username, event_name, approved in APPLICATIONS:
            WorkhandApplications.objects.update_or_create(
                workhand=workhands[username],
                event=events[event_name],
                defaults={"to_company": company, "status": approved},
            )

        # --- One completed event + feedback for the main demo workhand -----
        main = workhands["demoworkhand"]
        past_start = today - timedelta(days=40)
        history, _ = EventHistory.objects.update_or_create(
            company_id=company,
            workhand_id=main,
            event_name="Verma Engagement Ceremony",
            defaults={
                "event_category": get_category(EventsCategory, "Anniversary"),
                "description": "Engagement ceremony photography for ~150 guests.",
                "start_date": past_start,
                "end_date": past_start,
                "workhand_category": get_category(WorkhandCategory, "Photography"),
                "workhand_needed": 2,
                "payment_range": 4000.0,
                "address": "Lotus Banquet, Powai",
                "state": "Maharashtra",
                "city": "Mumbai",
            },
        )
        Feedback.objects.update_or_create(
            event_id=history,
            workhand_id=main,
            company_id=company,
            defaults={
                "feedback_title": "Great work on the day",
                "feedback": "Punctual, professional and delivered the photos ahead of schedule.",
                "date": past_start + timedelta(days=1),
            },
        )

        # --- Summary -------------------------------------------------------
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"  Company login:   {COMPANY['username']}")
        for w in WORKHANDS:
            self.stdout.write(f"  Workhand login:  {w['username']}")
        shown = "(from --password / DEMO_PASSWORD)" if (options["password"] or os.environ.get("DEMO_PASSWORD")) \
            else f"{DEFAULT_PASSWORD} (built-in default)"
        self.stdout.write(f"  Password:        {shown}")
        self.stdout.write(
            f"  {Event.objects.filter(company_id=company).count()} events, "
            f"{WorkhandApplications.objects.filter(to_company=company).count()} applications."
        )
