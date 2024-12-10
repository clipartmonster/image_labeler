from django.urls import path
from . import views

urlpatterns = [
    path('show_images/', views.show_images, name = 'show_images'),
    path('setup_session/', views.setup_session, name = 'setup_session'),
    path('initialize_session/', views.initialize_session, name = 'initialize_session'),

    path('mturk_redirect/', views.mturk_redirect, name= 'mturk_redirect'),
    path('view_mturk_responses/', views.view_mturk_responses, name = 'view_mturk_responses'),

    path('view_asset_labels/', views.view_asset_labels, name = 'view_asset_labels'),
    path('reconcile_labels/', views.reconcile_labels, name = 'reconcile_labels'),
    path('view_labels/', views.view_labels, name = 'view_labels'),


]

