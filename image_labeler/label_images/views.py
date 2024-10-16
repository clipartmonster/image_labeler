from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from .models import listings_to_be_labeled



from django.conf import settings
from django.http import FileResponse, Http404
import os

import requests
import json
import pandas as pd

def show_images(request):

    print('----------------')
    print(request.session['selected_source'])
    print(request.session['features'])
    print(request.session['labeler_id'])

    api_url = 'https://backend-python-nupj.onrender.com/get_color_labels/'

    data = {'source':request.session['selected_source'],
            'samples':50}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }
    
    response = requests.get(api_url, json = data, headers = header)

    assets_to_label = json.loads(response.content)['assets_to_label']
    total_in_full_set_to_label = json.loads(response.content)['total_in_full_set_to_label']
    total_in_set_to_label = json.loads(response.content)['total_in_set_to_label']



    color_labels = [{'label':'red','hex_code':'#ff0000'},
                    {'label':'orange','hex_code':'#ff7d00'},
                    {'label':'yellow','hex_code':'#FFFF00'},
                    {'label':'green','hex_code':'#00FF00'},
                    {'label':'blue','hex_code':'#0000FF'},
                    {'label':'purple','hex_code':'#7D00FF'},
                    {'label':'brown', 'hex_code':'#9B4B19'},
                    {'label':'tan', 'hex_code':'#ffc896'},
                    {'label':'pink', 'hex_code':'#f5b4c3'},
                    {'label':'gray', 'hex_code':'#AFAFAF'},
                    {'label':'black','hex_code':'#000000'},
                    {'label':'white','hex_code':'#FFFFFF'},
                    ]

    spread_values = ['25%', '50%', '75%', '100%']

    return render(request, 'show_images.html', {'assets_to_label' : assets_to_label,
                                                'total_in_set_to_label':total_in_set_to_label,
                                                'total_in_full_set_to_label':total_in_full_set_to_label,
                                                'reference_panels':range(9),
                                                'color_labels':color_labels,
                                                'spread_values':spread_values,
                                                'labeler_id':request.session['labeler_id']
                                                })



def setup_session(request):

    features = ['title', 'main_element', 'description', 'art_type', 
                'clip_art_type', 'count', 'primary_colors', 'line_width', 'color_depth']

   
    return render(request, 'setup_session.html', {'features':features})



def initialize_session(request):
    if request.method == 'POST':
        selected_source = request.POST.get('source')
        selected_features = request.POST.get('features')
        labeler_id = request.POST.get('labeler_id')
        # Save the selected source in the session
        request.session['selected_source'] = selected_source
        request.session['features'] = selected_features
        request.session['labeler_id'] = labeler_id
        return redirect('show_images')
    return redirect('select_source')


def mturk_redirect(request):

    task_type = request.GET.get('task_type')
    assignment_id = request.GET.get('assignmentId')
    hit_id = request.GET.get('hitId')

    print(assignment_id)
    print(hit_id)


    api_url = 'https://backend-python-nupj.onrender.com/get_assets_to_label/'

    data = {'samples':2,
            'labeler_id':1,
            'task_type':'art_type'}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)

    assets_to_label = json.loads(response.content)['assets_to_label']

    labels = ['invalid','pattern','clipart']


    return render(request, 'label_content.html', {'task_type':task_type,
                                                  'assignment_id':assignment_id,
                                                  'assets_to_label':assets_to_label,
                                                  'example_count':range(1,5),
                                                  'labels':labels})
