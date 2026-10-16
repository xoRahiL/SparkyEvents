from .models import Workhand, WorkhandApplications


def workhand_notifications(request):
    """
    Adds 'approved_applications_count' to every template's context, without
    needing every view to fetch it manually. Only computes anything for
    logged-in workhand users; everyone else gets an empty dict (no query run).
    """
    if request.user.is_authenticated:
        try:
            wu = Workhand.objects.get(user=request.user)
        except Workhand.DoesNotExist:
            return {}
        count = WorkhandApplications.objects.filter(workhand=wu, status=True).count()
        return {'approved_applications_count': count}
    return {}