from django.core.cache import cache
from .models import Workhand, WorkhandApplications


def workhand_notifications(request):
    """
    Adds 'approved_applications_count' to every template's context, without
    needing every view to fetch it manually. Only computes anything for
    logged-in workhand users; everyone else gets an empty dict (no query run).

    The count is cached per-user for 60 seconds to avoid a DB hit on every
    single page load — the value only changes when an application is approved
    or rejected, which happens far less often than page views.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        wu = Workhand.objects.get(user=request.user)
    except Workhand.DoesNotExist:
        return {}

    cache_key = f'approved_count_wh_{wu.pk}'
    count = cache.get(cache_key)
    if count is None:
        count = WorkhandApplications.objects.filter(workhand=wu, status=True).count()
        cache.set(cache_key, count, 60)  # cache for 60 seconds

    return {'approved_applications_count': count}
