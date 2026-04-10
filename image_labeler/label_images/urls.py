from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('front_page/', views.front_page, name='front_page'),

    # Labeling
    path('show_images/', views.show_images, name='show_images'),
    path('setup_session/', views.setup_session, name='setup_session'),
    path('initialize_session/', views.initialize_session, name='initialize_session'),
    path('mturk_redirect/', views.mturk_redirect, name='mturk_redirect'),
    path('select_primary_colors/', views.select_primary_colors, name='select_primary_colors'),
    path('select_line_widths/', views.select_line_widths, name='select_line_widths'),
    path('reconcile_labels/', views.reconcile_labels, name='reconcile_labels'),

    # Review
    path('view_mturk_responses/', views.view_mturk_responses, name='view_mturk_responses'),
    path('view_asset_labels/', views.view_asset_labels, name='view_asset_labels'),
    path('view_labels/', views.view_labels, name='view_labels'),
    path('view_batch_labels/', views.view_batch_labels, name='view_batch_labels'),
    path('view_prediction_labels/', views.view_prediction_labels, name='view_prediction_labels'),
    path('view_asset/', views.view_asset, name='view_asset'),
    path('view_label_issues/', views.view_label_issues, name='view_label_issues'),
    path('correct_mismatch_labels/', views.correct_mismatch_labels, name='correct_mismatch_labels'),

    # Admin
    path('view_model_results/', views.view_model_results, name='view_model_results'),
    path('manage_rules/', views.manage_rules, name='manage_rules'),
    path('label_testing/', views.label_testing, name='label_testing'),

    # Analytics
    path('view_primary_colors/', views.view_primary_colors, name='view_primary_colors'),
    path('view_rough_fill/', views.view_rough_fill, name='view_rough_fill'),
    path('view_line_widths/', views.view_line_widths, name='view_line_widths'),
]

