from django.db import migrations


WORKHAND_CATEGORIES = [
    "Catering", "Photography", "Videography", "Decoration", "Sound & DJ",
    "Security", "Event Coordination", "Housekeeping", "Waitstaff",
    "Anchor / Host", "Makeup Artist", "Florist", "Lighting", "Transportation",
]

EVENT_CATEGORIES = [
    "Wedding", "Birthday Party", "Corporate Event", "Concert", "Conference",
    "Exhibition", "Product Launch", "Anniversary", "Baby Shower",
    "Graduation Party", "Religious Ceremony", "Sports Event", "Festival",
]


def seed_categories(apps, schema_editor):
    WorkhandCategory = apps.get_model('appspark', 'WorkhandCategory')
    EventsCategory = apps.get_model('appspark', 'EventsCategory')

    for name in WORKHAND_CATEGORIES:
        WorkhandCategory.objects.get_or_create(category=name)

    for name in EVENT_CATEGORIES:
        EventsCategory.objects.get_or_create(category=name)


def remove_categories(apps, schema_editor):
    # Reverse migration: only removes the exact seeded names, leaves any
    # custom categories you added yourself untouched.
    WorkhandCategory = apps.get_model('appspark', 'WorkhandCategory')
    EventsCategory = apps.get_model('appspark', 'EventsCategory')

    WorkhandCategory.objects.filter(category__in=WORKHAND_CATEGORIES).delete()
    EventsCategory.objects.filter(category__in=EVENT_CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('appspark', '0026_workhandapplications_unique_application_per_event'),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_categories),
    ]