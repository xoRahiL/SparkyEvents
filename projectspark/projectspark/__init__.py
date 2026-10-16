try:
    # Celery is optional. The web app must boot without a broker or Celery
    # installed; this import remains available when future worker support is
    # enabled again.
    from .celery import app as celery_app
except ImportError:
    celery_app = None

__all__ = ('celery_app',)
