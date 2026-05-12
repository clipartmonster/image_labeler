from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse


def admin_required(view_func):
    """Allow only authenticated superusers (admins)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Admin access required.")

    return _wrapped


def labeler_required(view_func):
    """Allow only authenticated staff users who are not superusers (labelers)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.is_staff and not request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Labeler access required.")

    return _wrapped


def admin_required_ajax(view_func):
    """Like admin_required but returns 403 JSON for XHR endpoints."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return JsonResponse({"error": "admin access required"}, status=403)

    return _wrapped
