from django.urls import path
from . import views

urlpatterns = [
    path('front_page/', views.front_page, name = 'front_page'),
    path('show_images/', views.show_images, name = 'show_images'),
    path('setup_session/', views.setup_session, name = 'setup_session'),
    path('initialize_session/', views.initialize_session, name = 'initialize_session'),

    path('mturk_redirect/', views.mturk_redirect, name= 'mturk_redirect'),
    path('view_mturk_responses/', views.view_mturk_responses, name = 'view_mturk_responses'),

    path('view_asset_labels/', views.view_asset_labels, name = 'view_asset_labels'),
    path('reconcile_labels/', views.reconcile_labels, name = 'reconcile_labels'),
    path('view_labels/', views.view_labels, name = 'view_labels'),
    path('view_batch_labels/', views.view_batch_labels, name = 'view_batch_labels'),
    path('view_prediction_labels/', views.view_prediction_labels, name = 'view_prediction_labels'),
    path('view_asset/', views.view_asset, name = 'view_asset'),
    path('view_label_issues/', views.view_label_issues, name = 'view_label_issues'),
    path('view_model_results/', views.view_model_results, name = 'view_model_results'),
    path('view_primary_colors/', views.view_primary_colors, name = 'view_primary_colors'),
    path('label_testing/', views.label_testing, name = 'label_testing'),
    path('select_primary_colors/', views.select_primary_colors, name = 'select_primary_colors'),
    path('select_line_widths/', views.select_line_widths, name = 'select_line_widths'),

    path('manage_rules/', views.manage_rules, name = 'manage_rules'),


]

