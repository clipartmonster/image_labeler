from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def labeler_required(view_func):
    """Requires login. All authenticated users (admin or labeler) can access."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Requires login + admin role."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if profile is None or profile.role != 'admin':
            return HttpResponseForbidden("Admin access required.")
        return view_func(request, *args, **kwargs)
    return wrapper
