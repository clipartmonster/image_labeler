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

def front_page(request):

    data = {}

    return render(request, 'front_page.html', data)

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
 
    labeler_id = request.GET.get('labeler_id','Steve')
    task_type = request.GET.get('task_type','asset_type')
    rule_index = request.GET.get('rule_index',1)
    batch_id = request.GET.get('batch_id',1)

    api_url = 'https://backend-python-nupj.onrender.com/get_session_options/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    print('--------------')    
    print('sending request')
    response = requests.get(api_url, json = data, headers = header )
    print(response)
    session_options = json.loads(response.content)

    print(session_options['rule_index_stats'])

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

    batch_of_assets = pd.DataFrame(batch_of_assets['assets_w_labels']) 

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

    api_url = 'https://backend-python-nupj.onrender.com/get_assets_w_rule_labels/'

    data = {"samples":35000,
            "task_type":'clip_art_type'}
    # data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)

    # print(response)
    labeled_assets = pd.DataFrame(json.loads(response.content))

    # print('------labeled_assets------')
    # print(labeled_assets)

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
    .filter(['asset_id', 'asset_link']) \
    .drop_duplicates() \

    labeled_assets = pd.DataFrame(labeled_assets) \
    .assign(label = lambda x: x['label'].astype(int)) \
    .assign(rule_index = lambda x: 'rule_' + x['rule_index'].astype(str)) \
    .filter(['asset_id', 'rule_index', 'label']) \
    .pivot(index = 'asset_id', columns = 'rule_index', values = 'label') \
    .merge(asset_links, how = 'left', on = 'asset_id') \
    .dropna() \
    .astype('Int8', errors = 'ignore') \
    .to_dict(orient = 'records')

    # print('------labeled_assets------')
    # print(labeled_assets)

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

    # print('----task type-------')
    # print(task_type)

    # print('----labelling rules-------')
    # print(labelling_rules)

    labelling_rules = pd.DataFrame(labelling_rules['labelling_rules']) 
    labelling_rules['task_type'] = labelling_rules['task_type'].astype(str)
    labelling_rules = labelling_rules.loc[labelling_rules['task_type'] == 'clip_art_type']


    # .filter(['task_type','rule_index','title']) \
    # .query('task_type == @task_type') 
   
    print('----labelling rules-------')
    print(labelling_rules)

    rule_options = rule_options \
    .merge(labelling_rules, on = 'rule_index', how = 'left') \
    .to_dict(orient = 'records')

    # print(rule_options)

    data = {"rule_options":rule_options,
            "labeled_assets":labeled_assets,
            "total_available_images":len(labeled_assets)}

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

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    data = {}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)

    labelling_rules = pd.DataFrame(dict(json.loads(response.content))['labelling_rules'])
    labelling_rules = labelling_rules \
    .query('task_type == @task_type') \
    .query('rule_index == @rule_index') 

    api_url = 'https://backend-python-nupj.onrender.com/get_predictions/'

    data = {"rule_index":rule_index,
            "task_type":task_type}

    header = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY
        }

    response = requests.get(api_url, json = data, headers = header)
    prediction_data = pd.DataFrame(dict(json.loads(response.content))['prediction_data'])

    prediction_data = prediction_data \
    .query('predicted_label == "no"') \
    .sort_values('probability', ascending=False)

    data = {'prediction_data':prediction_data.to_dict(orient = 'records'),
            'task_type':task_type,
            'rule_index':rule_index,
            'label_title':labelling_rules['title'].values[0]}
    
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


    task_types = pd.DataFrame(labelling_rules) \
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
    asset_labels = json.loads(response.content)

    print(asset_labels)
    # print(asset_labels['asset_data'])

    print('-----------------s--------------------')
    print(asset_labels['rule_labels'])


    data = {"task_types":task_types,
            "labelling_rules":labelling_rules,
            "asset_metadata":asset_labels['asset_metadata'][0],
            "asset":asset_labels['asset_data'][0],
            "prompt_responses":asset_labels['prompt_responses'],
            "labels":asset_labels['rule_labels']}

    return render(request, 'view_asset.html', data)



def view_label_issues(request):

    
    api_url = 'https://backend-python-nupj.onrender.com/get_assets_w_label_issues/'

    data = {}

    header = {
    'Content-Type': 'application/json',
    'Authorization': settings.API_ACCESS_KEY
    }

    response = requests.get(api_url, json = data, headers = header)
    assets_w_label_issues = json.loads(response.content)['issue_table']

    print(assets_w_label_issues)

    data = {'assets':assets_w_label_issues}

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
        model_results['task_type'].str[0].str.upper() + model_results['rule_index'].astype(str)

    model_results = \
        model_results.sort_values(by=['label', 'status'], ascending=[True, False])

    print('---Model Results---')
    print(model_results)

    model_type_options = model_results['model_type'].unique()
    task_type_options = model_results['task_type'].unique()
    rule_index_options = model_results['title'].unique()
    model_labels = model_results['label'].unique()

    model_labels = model_results \
    .filter(['title','label','task_type']) \
    .drop_duplicates()

    print(model_type_options)
    print(model_labels)

    data = {'model_results':model_results.to_dict(orient = 'records'),
            'model_labels':model_labels.to_dict(orient = 'records'),
            'model_type_options':model_type_options,
            'task_type_options':task_type_options,
            'rule_index_options':rule_index_options,
            }

    return render(request, 'view_model_results.html', data)