from django.conf import settings


def labeling_api_base(request):
    return {
        "LABELING_API_BASE_URL": getattr(settings, "LABELING_API_BASE_URL", "").rstrip(
            "/"
        ),
    }
