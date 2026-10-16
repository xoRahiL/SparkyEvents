import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projectspark.settings')

app = Celery('projectspark')
# Reads all CELERY_* settings from settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')
# Auto-discovers tasks.py inside each installed app (appspark/tasks.py)
app.autodiscover_tasks()