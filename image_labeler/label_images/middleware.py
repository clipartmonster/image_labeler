from django.shortcuts import redirect


class ForcePasswordChangeMiddleware:
    """Redirect users with must_change_password=True to the password change page."""

    EXEMPT_URLS = [
        "/label_images/change_password/",
        "/accounts/logout/",
        "/accounts/login/",
        "/admin/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            profile = getattr(request.user, "profile", None)
            if profile and profile.must_change_password:
                if not any(request.path.startswith(url) for url in self.EXEMPT_URLS):
                    return redirect("change_password")

        return self.get_response(request)
