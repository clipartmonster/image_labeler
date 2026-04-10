from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from .views import get_config


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('front_page')
    return redirect('login')


urlpatterns = [
    path("admin/", admin.site.urls),
    path("label_images/", include('label_images.urls')),
    path('get_config/', get_config, name='get_config'),
    path('', root_redirect),
]
