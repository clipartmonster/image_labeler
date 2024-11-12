from django.urls import path
from . import views

urlpatterns = [
    path('show_images/', views.show_images, name = 'show_images'),
    path('setup_session/', views.setup_session, name = 'setup_session'),
    path('initialize_session/', views.initialize_session, name = 'initialize_session'),

    path('mturk_redirect/', views.mturk_redirect, name= 'mturk_redirect'),
    path('view_mturk_responses/', views.view_mturk_responses, name = 'view_mturk_responses')

]
