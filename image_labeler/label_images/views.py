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
import numpy as np

def front_page(request):

    data = {}

    return render(request, 'front_page.html', data)

def select_line_widths(request):

    labeler_id = request.GET.get('labeler_id','Steve')
    task_type = request.GET.get('task_type','asset_type')
    rule_index = request.GET.get('rule_index',1)
    batch_id = request.GET.get('batch_id',1)
    large_sub_batch = request.GET.get('large_sub_batch',1)

    api_url = 'https://backend-python-nupj.onrender.com/get_asset_batch/'

    data = {'batch_type':'large_sub_batch',
            'large_sub_batch':large_sub_batch,
            'batch_id':batch_id,
            'task_type':'line_width_type',
            'rule_index':rule_index}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }
 
    response = requests.get(api_url, json = data, headers = header)

    print('hello')

    assets_to_label = json.loads(response.content)['asset_batch']

    print(assets_to_label)

    sampling_array = [[1 + col + row * 3 for col in range(3)] for row in range(3)]

    data = {'sampling_array':sampling_array,
            'assets_to_label':assets_to_label,
            'labeler_id':labeler_id}

    return render(request, 'select_line_widths.html', data)


def select_primary_colors(request):

    api_url = 'https://backend-python-nupj.onrender.com/get_asset_batch/'

    data = {'batch_type':'large_sub_batch',
            'large_sub_batch':1,
            'batch_id':2,
            'task_type':'select_primary_colors',
            'rule_index':1}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }
 
    response = requests.get(api_url, json = data, headers = header)

    print('hello')

    assets_to_label = json.loads(response.content)['asset_batch']
    # total_in_full_set_to_label = json.loads(response.content)['total_in_full_set_to_label']
    # total_in_set_to_label = json.loads(response.content)['total_in_set_to_label']

    print(assets_to_label)

    data = {'assets_to_label':assets_to_label}

    return render(request, 'select_primary_colors.html', data)

def show_images(request):

    api_url = 'https://backend-python-nupj.onrender.com/get_color_labels/'

    data = {'source':'initial_training_set',
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
                                                'labeler_id':'Steve'
                                                })



def setup_session(request):
 
    labeler_id = request.GET.get('labeler_id','Steve')
    task_type = request.GET.get('task_type','asset_type')
    rule_index = request.GET.get('rule_index',1)
    batch_id = request.GET.get('batch_id',1)

    api_url = 'https://backend-python-nupj.onrender.com/get_session_options/'

    data = {"task_type":task_type}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    print('--------------')    
    print('sending request')
    response = requests.get(api_url, json = data, headers = header )
    print(response)
    session_options = json.loads(response.content)

    print(session_options)

    selected_options = {'labeler_id':labeler_id,
                        'task_type':task_type,
                        'rule_index':rule_index,
                        'batch_id':batch_id}    
   
    return render(request, 'setup_session.html', {'session_options':session_options,
                                                  'selected_options':selected_options})


def initialize_session(request):
    if request.method == 'POST':

        print(request.POST.get('source'))


        # selected_source = request.POST.get('source')
        # selected_features = request.POST.get('features')
        # labeler_id = request.POST.get('labeler_id')
        # # Save the selected source in the session
        # request.session['selected_source'] = selected_source
        # request.session['features'] = selected_features
        # request.session['labeler_id'] = labeler_id
        return redirect('show_images')
    return redirect('select_source')


def internal(request):

    task_type = request.GET.get('task_type')
    labeler_source = request.GET.get('label_source', None)
    label_type = request.GET.get('label_type')
    labeler_id = request.GET.get('labeler_id')
    samples = request.GET.get('samples',50)
    asset_id = request.GET.get('asset_id',None)
    test_the_labeler = request.GET.get('test_the_labeler', False)
    batch_index  = request.GET.get('batch_index', None)
    rule_indexes  = json.loads(request.GET.get('rule_indexes', None))
    add_lure_questions = request.GET.get('add_lure_questions', None)
    

    api_url = 'https://backend-python-nupj.onrender.com/get_asset_batch/'
    
    data = {'batch_index':batch_index,
            'lure_samples':2}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    assets_to_label = json.loads(response.content)



    

def mturk_redirect(request):

    task_type = request.GET.get('task_type')
    labeler_source = request.GET.get('label_source', None)
    label_type = request.GET.get('label_type')
    labeler_id = request.GET.get('labeler_id')
    samples = request.GET.get('samples',50)
    asset_id = request.GET.get('asset_id',None)
    sandbox_flag = request.GET.get('sandbox_flag', None)
    test_the_labeler = request.GET.get('test_the_labeler', False)
    batch_id  = request.GET.get('batch_id', None)
    large_sub_batch = request.GET.get('large_sub_batch', None)
    mturk_batch_id = request.GET.get('mturk_batch_id',0)
    rule_indexes  = json.loads(request.GET.get('rule_indexes', None))
    add_lure_questions = request.GET.get('add_lure_questions', None)

    rule_index = int(rule_indexes[0])

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


    print('-----------varaibles-----------')
    print(batch_id, task_type, rule_index,labeler_id)

 

    api_url = 'https://backend-python-nupj.onrender.com/get_asset_batch/'
    
    data = {'batch_type':'large_sub_batch',
            'large_sub_batch':large_sub_batch,
            'batch_id':batch_id,
            'task_type':task_type,
            'rule_index':rule_index}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    print('|-------response.content----------|')
    print(json.loads(response.content))
    assets_to_label = json.loads(response.content)['asset_batch']

    print('|-------assets to label----------|')
    print(pd.DataFrame(assets_to_label))


    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {'task_type':task_type,
            'rule_indexes':rule_indexes
            }

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))['labelling_rules']

    collection_data = {
        "task_type":task_type,
        "labeler_source":labeler_source,
        "label_type":label_type,
        "labeler_id":labeler_id,  
        "assignment_id":assignment_id,
        "hit_id":hit_id,      
        "mturk_batch_id":mturk_batch_id,    
        "rule_index":rule_indexes[0]
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



    return render(request, 'label_content.html', {'task_type':task_type,
                                                  'label':label_type,                                                  
                                                  'assets_to_label':assets_to_label,
                                                  'labelling_rules':labelling_rules,
                                                  'collection_data':collection_data,
                                                  'labeler_source':labeler_source, 
                                                  'assignment_id':assignment_id,
                                                  'hit_id':hit_id,
                                                  'rule_index':rule_index,
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

    batch_ids = []

    for label in assets_w_labels.values():
        print(label)
        print('--------------')
        batch_ids.append(int(label['data']['1'][0]['mturk_batch_id']))

    batch_ids = list(set(batch_ids))

    data = {'assets_w_labels':assets_w_labels,
            'batch_ids':batch_ids}

    return render(request, 'view_asset_labels.html', data)


def reconcile_labels(request):

    assignment_id = ''.join(random.choices( string.ascii_letters + string.digits, k =20))
    labeler_source = 'reconcile_label'
    batch_type = request.GET.get('batch_type')
    task_type = request.GET.get('task_type')
    labeler_id = request.GET.get('labeler_id')
    batch_index  = request.GET.get('batch_index', None)
    rule_indexes  = json.loads(request.GET.get('rule_indexes', None))
    rule_index = int(rule_indexes[0])

    api_url = 'https://backend-python-nupj.onrender.com/get_disputed_assets/'
    
    data = {'rule_index':rule_index,
            'task_type':task_type}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    assets_to_label = json.loads(response.content)
  
    print('-----69-69-------')
    print(assets_to_label)
    print('size of assets to label')
    print(len(assets_to_label))


    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {'task_type':task_type,
            'rule_indexes':rule_indexes
            }

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))['labelling_rules']

    print('----VvV----')
    print(labelling_rules)

    labelling_rules = sorted(labelling_rules, key=lambda x: x['rule_index'])



    collection_data = {
        "task_type":task_type,
        "labeler_id":labeler_id,  
        "assignment_id":assignment_id,
        "labeler_source":labeler_source,
    }

    print(collection_data)
    print(task_type)

    return render(request, 'label_content.html', {'task_type':task_type,
                                                  'labeler_id':labeler_id,
                                                  'labeler_source':labeler_source,
                                                  'assets_to_label':assets_to_label,
                                                  'assets_to_label_count':len(assets_to_label),
                                                  'labelling_rules':labelling_rules,
                                                  'collection_data':collection_data,
                                                  'assignment_id':assignment_id                                                 
                                                  })

def view_batch_labels(request):

    task_type = request.GET.get('task_type', 'asset_type')
    rule_index = int(request.GET.get('rule_index', 1))
    batch_index = int(request.GET.get('batch_index', 1))

    print(task_type,rule_index,batch_index)

    ###############################
    #get batches assets

    api_url = 'https://backend-python-nupj.onrender.com/get_batch_for_viewing/'

    data = {"task_type":task_type,
            "rule_index":rule_index,
            "batch_index":batch_index}

    print(data)

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = data, headers = header)
    batch_of_assets = json.loads(response.content)

    batch_of_assets = pd.DataFrame(batch_of_assets['assets_w_labels']) \
    .query('label=="yes"')

    # batch_of_assets = pd.DataFrame(batch_of_assets['assets_w_labels']) \
    # .sample(1000)

    print(batch_of_assets)

    # batch_of_assets = pd.DataFrame(batch_of_assets['assets_w_labels']) \
    # .query('color_type == "multi-color"')


    label_counts = batch_of_assets \
    .groupby('label') \
    .agg(count = ('asset_id','count')) \
    .reset_index() \
    .to_dict(orient = 'records')

    ###############################
    #get labelling rules
    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))

    rule_entry = pd.DataFrame(labelling_rules['labelling_rules']) \
    .query("task_type == @task_type") \
    .query("rule_index == @rule_index") \
    .to_dict(orient = 'records')

    print('------------')
    print(rule_entry)

    ##########################

    total_assets = len(batch_of_assets)

    data = {"rule_entry":rule_entry[0],
            "label_counts":label_counts,
            "total_assets": total_assets,
            "batch_of_assets":batch_of_assets.to_dict(orient = 'records')}

    return render(request, 'view_batch_labels.html', data)



def view_labels(request):

    task_type = str(request.GET.get('task_type', 'asset_type')).strip()

    print('-----task_type-----')
    print(task_type)

    #################################

    api_url = 'https://backend-python-nupj.onrender.com/get_dark_ratios/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)

    dark_ratios = pd.DataFrame(json.loads(response.content)) \
    .drop(['dark_label'],axis = 1) \
    .fillna(0) \
    .assign(dark_ratio = lambda x: (x.dark_ratio * 100).astype(int))
    
    dark_ratio_limits = {'min':dark_ratios['dark_ratio'].min(),
                         'max':dark_ratios['dark_ratio'].max()}
    
    print('------Dark Ratios-------')
    print(dark_ratios)
    print(dark_ratio_limits)

    #################################

    api_url = 'https://backend-python-nupj.onrender.com/get_assets_w_rule_labels/'

    data = {"task_type":task_type}
    # data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)

    labeled_assets = pd.DataFrame(json.loads(response.content))

    task_types = pd.DataFrame(labeled_assets) \
    ['task_type'] \
    .drop_duplicates() \
    .sort_values()

    rule_options = pd.DataFrame(labeled_assets) \
    .filter(['rule_index']) \
    .drop_duplicates() \
    .sort_values(['rule_index']) \
    .reset_index(drop = True)

    asset_links = pd.DataFrame(labeled_assets) \
    .filter(['asset_id', 'image_link']) \
    .drop_duplicates() \

    labeled_assets = labeled_assets \
    .filter(['asset_id','rule_index','label']) \
    .drop_duplicates() \
    .assign(label = lambda x: x['label'].astype(int)) \
    .assign(rule_index = lambda x: 'rule_index_' + x['rule_index'].astype(str)) \
    .pivot(index = 'asset_id', columns = 'rule_index', values = 'label') \
    .merge(asset_links, how = 'left', on = 'asset_id') \
    .dropna() \
    .astype('Int8', errors = 'ignore') 

    labeled_assets = labeled_assets \
    .merge(dark_ratios, on = 'asset_id', how = 'left')\
    .fillna(101) \
    .sort_values('dark_ratio', ascending=True)

    print('------labeled_assets-1------')
    print(labeled_assets)

    ####################
    #need to create a set of rule_idex, label pairs for building class attributes of each asset (These are used for filtering)
    asset_rule_pairs = pd.DataFrame(labeled_assets) \
    .drop('image_link', axis = 1) \
    .melt(id_vars = 'asset_id', var_name = 'rule_index', value_name = 'label' ) \
    .groupby('asset_id') \
    .apply(lambda x: list(zip(x['rule_index'],x['label']))) \
    .reset_index(name = 'rule_pairs') 

    labeled_assets = labeled_assets \
    .merge(asset_rule_pairs, on = 'asset_id', how = 'left') \
    .to_dict(orient = 'records')

    print('------labeled_assets-2------')
    print(labeled_assets)

    #######################
    #get labelling rule title

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))

    labelling_rules = pd.DataFrame(labelling_rules['labelling_rules']) 

    labelling_rules = labelling_rules \
    .filter(['task_type','rule_index','title']) \
    .query('task_type == @task_type')  \
    .merge(rule_options.assign(active = 'yes'), on = 'rule_index', how = 'left') \
    .dropna() \
    .reset_index()

    rule_options = rule_options \
    .merge(labelling_rules, on = 'rule_index', how = 'left') \
    .to_dict(orient = 'records')

    data = {"rule_options":rule_options,
            "labeled_assets":labeled_assets,
            "dark_ratio_limits":dark_ratio_limits,
            "total_available_images":len(labeled_assets)}

    # data = {}

    return render(request, 'view_labels.html', data)


def manage_rules(request):
    
    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))
    
    rule_table = labelling_rules['labelling_rules']
    task_types = labelling_rules['task_type_set']

    data = {"task_types":task_types,
            "rule_table":rule_table}
    
    return render(request, 'manage_rules.html', data)





def view_prediction_labels(request):

    task_type = request.GET.get('task_type', 'asset_type')
    rule_index = int(request.GET.get('rule_index', 1))
    batch_index = request.GET.get('batch_index',None)
    label_type = request.GET.get("label_type",'mismatch')

    #################

    if batch_index is not None:
        batch_index = int(batch_index)

    #################


    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)

    task_by_rule_options = pd.DataFrame(dict(json.loads(response.content))['labelling_rules']) \
    .filter(['task_type', 'rule_index','title'])

    task_type_options = task_by_rule_options \
    .filter(['task_type']) \
    .drop_duplicates() 

    labelling_rules = pd.DataFrame(dict(json.loads(response.content))['labelling_rules'])

    labelling_rules = labelling_rules \
    .query('task_type == @task_type') \
    .query('rule_index == @rule_index') 

    api_url = 'https://backend-python-nupj.onrender.com/get_predictions/'

    data = {"rule_index":rule_index,
            "task_type":task_type,
            "batch_index":batch_index,
            "label_type":label_type}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    print('----response-----')
    print(response.content)

    prediction_data = pd.DataFrame(dict(json.loads(response.content))['prediction_data'])
    batch_counts = pd.DataFrame(dict(json.loads(response.content))['batch_counts'])

    if len(prediction_data) > 0:

        #round probability for formatting
        prediction_data = prediction_data \
        .sort_values('probability', ascending=False) \
        .assign(probability = lambda x: np.round(x['probability'],3))

        mismatch_counts = prediction_data \
            .assign(status = lambda x: np.where(x['manual_label'] == 'yes', 'false_negative','false_positive')) \
            .groupby('status') \
            .agg(count = ('asset_id','count')) \
            .to_dict()['count']
        
    else:
        prediction_data = pd.DataFrame()
        mismatch_counts = pd.DataFrame()

    if label_type == 'only_no':
        prediction_data = prediction_data.iloc[1:3000]

    label_types = ['model','manual']
    labeler_id_options = ['Steve','Noah']
    label_type_filters = ['only_yes','only_no','mismatch']

    data = {'prediction_data':prediction_data.to_dict(orient = 'records'),
            'batch_counts':batch_counts.to_dict(orient = 'records'),
            'mismatch_counts':mismatch_counts,
            'labeler_id_options':labeler_id_options,
            'task_type_options':task_type_options.to_dict(orient = 'records'),
            'task_by_rule_options':task_by_rule_options.to_dict(orient = 'records'),
            'task_type':task_type,
            'rule_index':rule_index,
            'label_types':label_types,
            'label_title':labelling_rules['title'].values[0],
            'label_type_filters':label_type_filters}
    
    return render(request, 'view_prediction_labels.html', data)



def view_asset(request):

    asset_id = request.GET.get('asset_id', 158370)

    
    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    labelling_rules = dict(json.loads(response.content))['labelling_rules']

    print('-------------')
    print(labelling_rules)

    task_types = pd.DataFrame(labelling_rules) \
    .query('task_type != "select_primary_colors"') \
    .filter(['task_type']) \
    .drop_duplicates() \
    .squeeze() \
    .tolist()

    api_url = 'https://backend-python-nupj.onrender.com/get_asset_labels/'

    data = {"asset_id":asset_id}

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = data, headers = header)

    print("--------statust code---------")
    print(response.status_code)

    if response.status_code != 500: 
        asset_labels = json.loads(response.content)

        asset_metadata = asset_labels['asset_metadata'][0]
        asset = asset_labels['asset_data'][0]
        prompt_response = asset_labels['prompt_responses']
        labels = asset_labels['rule_labels']

    else:
        asset_labels = []
        asset_metadata = []
        asset = []
        prompt_response = []
        labels = []

    data = {"task_types":task_types,
            "labelling_rules":labelling_rules,
            "asset_metadata":asset_labels,
            "asset":asset,
            "prompt_responses":prompt_response,
            "labels":labels}

    return render(request, 'view_asset.html', data)



def view_label_issues(request):
    
    task_type = request.GET.get('task_type', 'color_fill_type')
    rule_index = int(request.GET.get('rule_index', 1))

    print('------------------')
    print(task_type)
    print(rule_index)

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)

    task_by_rule_options = pd.DataFrame(dict(json.loads(response.content))['labelling_rules']) \
    .filter(['task_type', 'rule_index','title'])

    task_type_options = task_by_rule_options \
    .filter(['task_type']) \
    .drop_duplicates() 

    labelling_rules = pd.DataFrame(dict(json.loads(response.content))['labelling_rules'])

    labelling_rules = labelling_rules \
    .query('task_type == @task_type') \
    .query('rule_index == @rule_index') 


    api_url = 'https://backend-python-nupj.onrender.com/get_assets_w_label_issues/'

    data = {'task_type':task_type,
            'rule_index':rule_index}

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = data, headers = header)
    assets_w_label_issues = json.loads(response.content)

    assets_w_label_issues = pd.DataFrame(assets_w_label_issues) 
        
    print('--------assets_w_label_issues---------')
    print(assets_w_label_issues)

    label_types = ['model','manual']
    labeler_id_options = ['Steve','Noah']

    # data = {'assets':assets_w_label_issues}

    data = {'assets':assets_w_label_issues,
            'labeler_id_options':labeler_id_options,
            'task_type_options':task_type_options.to_dict(orient = 'records'),
            'task_by_rule_options':task_by_rule_options.to_dict(orient = 'records'),
            'task_type':task_type,
            'rule_index':rule_index,
            'label_types':label_types,
            'label_title':labelling_rules['title'].values[0]}

    return render(request, 'view_label_issues.html', data)


def label_testing(request):

    api_url = 'https://backend-python-nupj.onrender.com/get_label_testing_options/'

    data = {"session_id":2}

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = data, headers = header)
    session_data = json.loads(response.content)

    experiments = session_data['data']

    data = {"experiments":experiments}

    print(data)

    return render(request, 'label_testing.html', data)


def view_model_results(request):

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = {}, headers = header)
    label_rules = json.loads(response.content)

    label_rules = label_rules['labelling_rules']

    label_rules = [{'rule_index': entry['rule_index'], 'task_type': entry['task_type'], 'title': entry['title']} for entry in label_rules]
    label_rules = pd.DataFrame(label_rules)
    
    

    api_url = 'https://backend-python-nupj.onrender.com/get_model_results/'

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = {}, headers = header)
    model_results = json.loads(response.content)

    model_results = pd.DataFrame(model_results['model_results']) \
    .merge(label_rules, on = ['rule_index','task_type'], how = 'left')

    model_results['label'] = \
        model_results['task_type'].str[0:2].str.upper() + model_results['rule_index'].astype(str)

    model_results = \
        model_results.sort_values(by=['label', 'status'], ascending=[True, False])

    model_result = \
        model_results['date'] = pd.to_datetime(model_results['created_at']).dt.date

    best_models = model_results \
    .assign( performant=lambda x: np.where((x.val_recall > 0.88) & (x.val_precision > 0.88), 'close', 'no')) \
    .assign( performant=lambda x: np.where((x.val_recall > 0.9) & (x.val_precision > 0.9), 'yes', x.performant)) \
    .sort_values(['task_type','rule_index', 'score'], ascending = False) \
    .groupby(['task_type','rule_index']) \
    .head(1) \
    .reset_index() \
    .filter(['task_type','label', 'val_recall', 'val_precision','performant'])


    print('-----best_models------')
    print(best_models)
    print(best_models.columns)

    model_results = model_results \
    .assign( sample_size = lambda x:np.where(x.total_samples < 7000, 0,1)) \
    .dropna( subset = ['total_samples']) \
    .query('total_samples > 1000') \
    .groupby(['task_type', 'rule_index','sample_size']) \
    .head(20) \
    .sort_values(by=['task_type', 'rule_index', 'sample_size', 'score'], ascending=[True, True, False, False]) \
    .assign(index_column=lambda x: x.groupby(['task_type', 'rule_index']).cumcount() + 1) \
    .reset_index(drop=True)
  

    model_type_options = model_results['model_type'].unique()
    task_type_options = model_results['task_type'].unique()
    rule_index_options = model_results['title'].unique()
    model_labels = model_results['label'].unique()

    model_labels = model_results \
    .filter(['title','label','task_type']) \
    .drop_duplicates() \
    .merge(best_models, on = ['label','task_type'], how = 'left')

    print('-----model_labels------')
    print(model_labels)


    data = {'model_results':model_results.to_dict(orient = 'records'),
            'model_labels':model_labels.to_dict(orient = 'records'),
            'model_type_options':model_type_options,
            'task_type_options':task_type_options,
            'rule_index_options':rule_index_options,
            }

    return render(request, 'view_model_results.html', data)



def view_primary_colors(request):
    
    api_url = 'https://backend-python-nupj.onrender.com/get_primary_colors/'

    data = {}

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = data, headers = header)
    primary_colors = json.loads(response.content)

    print(primary_colors)

    asset_primary_colors = pd.DataFrame(primary_colors)

    # data = {}
    data = {'asset_primary_colors':asset_primary_colors.to_dict(orient = 'records')}

    return render(request, 'view_primary_colors.html', data)


def correct_mismatch_labels(request):

    task_type = request.GET.get('task_type', 'color_fill_type')
    rule_index = int(request.GET.get('rule_index', 2))
    labeler_id = request.GET.get('labeler_id', 'Steve')

    print(task_type)
    print(rule_index)

    ##############################

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    ##############################

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {'task_type':task_type,
            'rule_indexes':[rule_index]
            }

    response = requests.get(api_url, json = data, headers = header)
    print(response)
    label_rules = json.loads(response.content)['labelling_rules']

    prompt = label_rules[0]['prompt']

    print('-----label_rules-------')
    print(label_rules)

    ##############################

    api_url = 'https://backend-python-nupj.onrender.com/get_mismatched_labels/'

    data = {'task_type':task_type,
            'rule_index':rule_index}

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = data, headers = header)
    mismatched_labels = json.loads(response.content)['mistmatched_labels']

    mismatched_labels = pd.DataFrame(mismatched_labels) \
    .query('status == "active"')

    print('-----mismatched_labels-------')
    print(mismatched_labels)

    collection_data = {'task_type':task_type,
                       'labeler_source':'mismatch',
                       'labeler_id':labeler_id}

    data = {'mismatched_labels':mismatched_labels.to_dict(orient = 'records'),
            'collection_data':collection_data,
            'label_rules':label_rules,
            'prompt':prompt}

    return render(request, 'correct_mismatch_labels.html', data)