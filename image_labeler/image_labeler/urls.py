
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.shortcuts import redirect
from .views import get_config

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("label_images/", include('label_images.urls')),
    path('get_config/', get_config, name='get_config'),
    path("", include('labeling_api.urls')),
    path('', lambda request: redirect('label_images/front_page/', permanent=False)),
]
