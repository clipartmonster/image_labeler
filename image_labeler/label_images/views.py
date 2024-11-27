from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from .models import listings_to_be_labeled



from django.conf import settings
from django.http import FileResponse, Http404

import os
import random
import string


import requests
import json
import pandas as pd

def show_images(request):

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
    labeler_source = request.GET.get('label_source', None)
    label_type = request.GET.get('label_type')
    labeler_id = request.GET.get('labeler_id')
    samples = request.GET.get('samples',50)
    asset_id = request.GET.get('asset_id',None)
    sandbox_flag = request.GET.get('sandbox_flag', None)
    test_the_labeler = request.GET.get('test_the_labeler', False)
    batch_index  = request.GET.get('batch_index', None)
    mturk_batch_id = request.GET.get('mturk_batch_id',None)
    rule_indexes  = json.loads(request.GET.get('rule_indexes', None))
    add_lure_questions = request.GET.get('add_lure_questions', None)
    
    print(mturk_batch_id)
    print(bool(test_the_labeler))

    assignment_id = request.GET.get('assignmentId',None)
    hit_id = request.GET.get('hitId')
    worker_id = request.GET.get('workerId', 'not_assigned')

    #Create an assignment id when not provided one. Important for submission status
    if assignment_id == None:
        assignment_id = ''.join(random.choices( string.ascii_letters + string.digits, k =20))


    from datetime import datetime
    import pytz

    # Define the Central Time zone
    central_time_zone = pytz.timezone('America/Chicago')

    # Get the current time in Central Time
    central_time = datetime.now(central_time_zone)

    print('----------------------------------------------------')
    print(central_time.strftime("%Y-%m-%d %I:%M:%S %p"))
    print('assignment id:' + assignment_id)
    print('worker id:' + worker_id)
    print('----------------------------------------------------')


    if labeler_source == 'MTurk':
        labeler_id = worker_id 


    # api_url = 'https://backend-python-nupj.onrender.com/get_assets_to_label/'
   
    # if asset_id is None: 
    #     data = {'samples':int(samples),
    #             'labeler_id':1,
    #             'task_type':'art_type'}

    # else:
    #     data = {'asset_id':asset_id}

    api_url = 'https://backend-python-nupj.onrender.com/get_asset_batch/'
    
    data = {'batch_index':batch_index,
            'lure_samples':2}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    # assets_to_label = json.loads(response.content)['assets_to_label']
    assets_to_label = json.loads(response.content)

  

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {'task_type':task_type,
            'label_type':'clip_art',
            'rule_indexes':rule_indexes
            }

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))['labeling_rules']

    labelling_rules = labelling_rules[label_type]
    labelling_rules = sorted(labelling_rules, key=lambda x: x['rule_index'])

    print(labelling_rules)

    collection_data = {
        "task_type":task_type,
        "labeler_source":labeler_source,
        "label_type":label_type,
        "labeler_id":labeler_id,  
        "assignment_id":assignment_id,
        "hit_id":hit_id,      
        'mturk_batch_id':mturk_batch_id       
    }

    #Get test examples 

    if bool(test_the_labeler) == True:
        print('preparing test questions')
        api_url = 'https://backend-python-nupj.onrender.com/get_test_questions/'

        data = {'samples':2}

        header = {
            'Content-Type': 'application/json',
            'Authorization': settings.API_ACCESS_KEY
            }

        response = requests.get(api_url, json = data, headers = header)
        test_questions = dict(json.loads(response.content))
        
    else:
        test_questions = []    


    print(assets_to_label)

    return render(request, 'label_content.html', {'task_type':task_type,
                                                  'label':label_type,                                                  
                                                  'assets_to_label':assets_to_label,
                                                  'labelling_rules':labelling_rules,
                                                  'collection_data':collection_data,
                                                  'labeler_source':labeler_source, 
                                                  'assignment_id':assignment_id,
                                                  'hit_id':hit_id,
                                                  'sandbox_flag':sandbox_flag,
                                                  'test_the_labeler':test_the_labeler,
                                                  'test_questions':test_questions
                                                  })


def view_mturk_responses(request):

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {'task_type':'art_type',
            'label_type':'clip_art',
             'rule_indexes':[1,2,3,4,5]}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))['labeling_rules']['clip_art']

    prompts = {(item['prompt'], item['rule_index']) for item in labelling_rules}
    prompts = [{'prompt': prompt, 'rule_index': rule_index} for prompt, rule_index in prompts]    


    api_url = 'https://backend-python-nupj.onrender.com/get_prompt_responses/'

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }
    
    response = requests.get(api_url, headers = header)
    assets_w_responses = json.loads(response.content)
   
    print('----------------------------------')
    print(assets_w_responses)
    # print(labelling_rules)

    return render(request, 'view_mturk_responses.html', {'assets_w_responses':assets_w_responses,
                                                         'labelling_rules':labelling_rules,
                                                         'prompts':prompts})



def view_asset_labels(request):

    api_url = 'https://backend-python-nupj.onrender.com/get_asset_labels/'

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }
    
    response = requests.get(api_url, headers = header)
    assets_w_labels = json.loads(response.content)
   
    print('----------------------------------')
    print(assets_w_labels.values())
   
    batch_ids = []

    for label in assets_w_labels.values():
        batch_ids.append(int(label['data']['1'][0]['mturk_batch_id']))

    batch_ids = list(set(batch_ids))

    data = {'assets_w_labels':assets_w_labels,
            'batch_ids':batch_ids}

    return render(request, 'view_asset_labels.html', data)
