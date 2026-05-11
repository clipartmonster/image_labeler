from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse


def _get_role(user):
    profile = getattr(user, "profile", None)
    if profile is None:
        return "admin" if user.is_superuser else None
    return profile.role


def admin_required(view_func):
    """Allow only authenticated users with the *admin* role (or superuser)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        role = _get_role(request.user)
        if role == "admin" or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Admin access required.")

    return _wrapped


def labeler_required(view_func):
    """Allow only authenticated users with the *labeler* role."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        role = _get_role(request.user)
        if role == "labeler":
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Labeler access required.")

    return _wrapped


def admin_required_ajax(view_func):
    """Like admin_required but returns 403 JSON for XHR endpoints."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        role = _get_role(request.user)
        if role == "admin" or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return JsonResponse({"error": "admin access required"}, status=403)

    return _wrapped
