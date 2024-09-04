
from django.contrib import admin
from django.urls import path, include
from .views import get_config

urlpatterns = [
    path("admin/", admin.site.urls),
    path("label_images/", include('label_images.urls')),
    path('get_config/', get_config, name = 'get_config')
]
