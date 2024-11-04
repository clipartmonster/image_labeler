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
    labeler_source = request.GET.get('label_source')
    assignment_id = request.GET.get('assignmentId')
    label_type = request.GET.get('label_type')
    hit_id = request.GET.get('hitId')
    samples = request.GET.get('samples',50)
    asset_id = request.GET.get('asset_id',None)

    api_url = 'https://backend-python-nupj.onrender.com/get_assets_to_label/'

    if asset_id is None: 
        data = {'samples':samples,
                'labeler_id':1,
                'task_type':'art_type'}

    else:
        data = {'asset_id':asset_id}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    assets_to_label = json.loads(response.content)['assets_to_label']

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {'task_type':task_type}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))['labeling_rules']

    labelling_rules = labelling_rules[label_type]
    labelling_rules = sorted(labelling_rules, key=lambda x: x['rule_index'])

    collection_data = {
        "task_type":task_type,
        "labeler_source":labeler_source,
        "labeler_id":assignment_id,
        "label_type":label_type,        
        "hit_id": hit_id        
    }
    

    return render(request, 'label_content.html', {'task_type':task_type,
                                                  'label':label_type,                                                  
                                                  'assets_to_label':assets_to_label,
                                                  'labelling_rules':labelling_rules,
                                                  'collection_data':collection_data,
                                                  'labeler_source':labeler_source, 
                                                  'assignment_id':assignment_id,
                                                  'hit_id':hit_id
                                                  })
