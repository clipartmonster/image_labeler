from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def api_authorization(view_func):
    """Require Authorization header to match settings.API_ACCESS_KEY (if configured)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        expected = getattr(settings, "API_ACCESS_KEY", None)
        if expected:
            got = request.headers.get("Authorization") or request.META.get(
                "HTTP_AUTHORIZATION", ""
            )
            if (got or "").strip() != (expected or "").strip():
                return JsonResponse({"error": "unauthorized"}, status=401)
        return view_func(request, *args, **kwargs)

    return _wrapped
