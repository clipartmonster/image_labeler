import os
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


@login_required
def get_config(request):
    config = {
        'API_ACCESS_KEY': os.getenv('API_ACCESS_KEY'),
        'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
        'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
    }
    return JsonResponse(config)