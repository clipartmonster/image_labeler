from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.staticfiles import finders
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from .models import listings_to_be_labeled, UserProfile

from django.conf import settings
from django.http import FileResponse, Http404

import os
import random
import string

import logging
import requests
import json
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from .decorators import labeler_required, admin_required

logger = logging.getLogger(__name__)

API_BASE = 'https://backend-python-nupj.onrender.com'
API_TIMEOUT = 15


def api_get(path, data=None, timeout=API_TIMEOUT):
    """GET from the backend API with standard headers, timeout, and error handling.
    Returns parsed JSON dict, or raises on non-2xx / network failure."""
    url = f"{API_BASE}/{path.lstrip('/')}".rstrip('/') + '/'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': settings.API_ACCESS_KEY,
    }
    resp = requests.get(url, json=data or {}, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('front_page')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            next_url = request.GET.get('next', '')
            if not next_url or not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                next_url = 'front_page'
            return redirect(next_url)
        return render(request, 'auth/login.html', {'error': 'Invalid username or password.'})
    return render(request, 'auth/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('front_page')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        errors = []
        if not username:
            errors.append('Username is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != password2:
            errors.append('Passwords do not match.')
        if User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        if errors:
            return render(request, 'auth/register.html', {'errors': errors, 'username': username})
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user, role='labeler')
        return redirect('login')
    return render(request, 'auth/register.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')

@labeler_required
def front_page(request):
    from django.db import connection

    rules_map = {}
    try:
        rules_list = api_get('get_labelling_rules').get('labelling_rules', [])
        for r in rules_list:
            key = (r.get('task_type'), r.get('rule_index'))
            rules_map[key] = r.get('title', '')
    except Exception:
        rules_list = []

    best_models = {}
    try:
        mr = pd.DataFrame(api_get('get_model_results').get('model_results', []))
        if not mr.empty:
            mr['score'] = mr.get('score', 0)
            best = (
                mr.sort_values('score', ascending=False)
                .groupby(['task_type', 'rule_index'])
                .head(1)
            )
            for _, row in best.iterrows():
                key = (row['task_type'], int(row['rule_index']))
                best_models[key] = {
                    'val_precision': round(row.get('val_precision', 0), 3),
                    'val_recall': round(row.get('val_recall', 0), 3),
                    'score': round(row.get('score', 0), 3),
                }
    except Exception:
        pass

    # --- Asset and label counts from Postgres ---
    feature_status = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    sa.task_type,
                    sa.rule_index,
                    COUNT(DISTINCT sa.asset_id) AS total_selected,
                    COUNT(DISTINCT pr.asset_id) AS with_any_label
                FROM "label_data.selected_assets" sa
                LEFT JOIN (
                    SELECT DISTINCT asset_id, task_type, rule_index
                    FROM "label_data.prompt_responses"
                ) pr
                    ON sa.asset_id = pr.asset_id
                    AND sa.task_type = pr.task_type
                    AND CAST(sa.rule_index AS text) = CAST(pr.rule_index AS text)
                WHERE sa.task_type IS NOT NULL
                GROUP BY sa.task_type, sa.rule_index
                ORDER BY sa.task_type, sa.rule_index
            """)
            selected_rows = cursor.fetchall()

            # Reconciliation readiness: assets with 2+ responses, non-tied,
            # not yet in the labels table
            cursor.execute("""
                SELECT
                    pr.task_type,
                    pr.rule_index,
                    COUNT(*) AS reconcilable
                FROM (
                    SELECT
                        asset_id, task_type, rule_index,
                        SUM(CASE WHEN prompt_response = 'yes' THEN 1 ELSE 0 END) AS yes_ct,
                        COUNT(*) AS sample_ct
                    FROM "label_data.prompt_responses"
                    GROUP BY asset_id, task_type, rule_index
                    HAVING COUNT(*) > 1
                ) pr
                LEFT JOIN "label_data.asset_type.rule.labels" rl
                    ON pr.asset_id = rl.asset_id
                    AND CAST(pr.task_type AS text) = CAST(rl.task_type AS text)
                    AND CAST(pr.rule_index AS text) = CAST(rl.rule_index AS text)
                WHERE rl.asset_id IS NULL
                  AND (CAST(pr.yes_ct AS float) / pr.sample_ct) != 0.5
                GROUP BY pr.task_type, pr.rule_index
            """)
            reconcile_rows = {
                (row[0], row[1]): row[2] for row in cursor.fetchall()
            }

        for row in selected_rows:
            tt, ri = row[0], row[1]
            ri_int = int(ri) if ri is not None else 0
            key = (tt, ri_int)
            total = row[2]
            labeled = row[3]
            feature_status.append({
                'task_type': tt,
                'rule_index': ri_int,
                'title': rules_map.get(key, ''),
                'total_selected': total,
                'unlabeled': total - labeled,
                'labeled': labeled,
                'reconcilable': reconcile_rows.get((tt, ri), reconcile_rows.get((tt, str(ri_int)), 0)),
                'best_model': best_models.get(key, None),
            })
    except Exception:
        pass

    is_admin = getattr(getattr(request.user, 'profile', None), 'role', '') == 'admin'

    data = {
        'feature_status': feature_status,
        'is_admin': is_admin,
    }

    return render(request, 'front_page.html', data)

@labeler_required
def select_line_widths(request):

    labeler_id = request.GET.get('labeler_id', request.user.username)
    task_type = request.GET.get('task_type','asset_type')
    rule_index = request.GET.get('rule_index',1)
    batch_id = request.GET.get('batch_id',1)
    large_sub_batch = request.GET.get('large_sub_batch',1)

    resp = api_get('get_asset_batch', {
        'batch_type': 'large_sub_batch',
        'large_sub_batch': large_sub_batch,
        'batch_id': batch_id,
        'task_type': 'line_width_type',
        'rule_index': rule_index,
    })
    assets_to_label = resp['asset_batch']

    sampling_array = [[1 + col + row * 3 for col in range(3)] for row in range(3)]

    data = {'sampling_array':sampling_array,
            'assets_to_label':assets_to_label,
            'labeler_id':labeler_id}

    return render(request, 'select_line_widths.html', data)


@labeler_required
def select_primary_colors(request):

    resp = api_get('get_asset_batch', {
        'batch_type': 'large_sub_batch',
        'large_sub_batch': 1,
        'batch_id': 2,
        'task_type': 'select_primary_colors',
        'rule_index': 1,
    })
    assets_to_label = resp['asset_batch']

    data = {'assets_to_label':assets_to_label}

    return render(request, 'select_primary_colors.html', data)

@labeler_required
def show_images(request):

    resp = api_get('get_color_labels', {
        'source': 'initial_training_set',
        'samples': 50,
    })
    assets_to_label = resp['assets_to_label']
    total_in_full_set_to_label = resp['total_in_full_set_to_label']
    total_in_set_to_label = resp['total_in_set_to_label']



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
                                                'labeler_id': request.user.username
                                                })



@labeler_required
def setup_session(request):
 
    labeler_id = request.GET.get('labeler_id', request.user.username)
    task_type = request.GET.get('task_type','asset_type')
    rule_index = request.GET.get('rule_index',1)
    batch_id = request.GET.get('batch_id',1)

    session_options = api_get('get_session_options', {"task_type": task_type})

    # print(session_options)

    selected_options = {'labeler_id':labeler_id,
                        'task_type':task_type,
                        'rule_index':rule_index,
                        'batch_id':batch_id}    
   
    return render(request, 'setup_session.html', {'session_options':session_options,
                                                  'selected_options':selected_options})


@labeler_required
def initialize_session(request):
    if request.method == 'POST':
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
    return HttpResponse("Not implemented", status=501)



@labeler_required
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

    if labeler_source == 'MTurk':
        labeler_id = worker_id 


    # print('-----------varaibles-----------')
    # print(batch_id, task_type, rule_index,labeler_id)

    
    def fetch_assets():
        return api_get('get_asset_batch', {
            'batch_type': 'large_sub_batch',
            'large_sub_batch': large_sub_batch,
            'batch_id': batch_id,
            'task_type': task_type,
            'rule_index': rule_index,
        })

    def fetch_rules():
        return api_get('get_labelling_rules', {
            'task_type': task_type,
            'rule_indexes': rule_indexes,
        })['labelling_rules']

    def fetch_test_questions():
        if bool(test_the_labeler):
            return api_get('get_test_questions', {'samples': 2})
        return []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_assets = executor.submit(fetch_assets)
        future_rules = executor.submit(fetch_rules)
        future_test = executor.submit(fetch_test_questions)

        assets_content = future_assets.result()
        labelling_rules = future_rules.result()
        test_questions = future_test.result()

    assets_to_label = assets_content['asset_batch']

    # print('|-------assets to label----------|')
    # print(pd.DataFrame(assets_to_label))

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

    # Test questions are already fetched in parallel above
    
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


@labeler_required
def view_mturk_responses(request):

    resp = api_get('get_labelling_rules', {
        'task_type': 'art_type',
        'label_type': 'clip_art',
        'rule_indexes': [1, 2, 3, 4, 5],
    })
    labelling_rules = resp['labeling_rules']['clip_art']

    prompts = {(item['prompt'], item['rule_index']) for item in labelling_rules}
    prompts = [{'prompt': prompt, 'rule_index': rule_index} for prompt, rule_index in prompts]    

    assets_w_responses = api_get('get_prompt_responses')
   
    # print('----------------------------------')
    # print(assets_w_responses)
    # print(labelling_rules)

    return render(request, 'view_mturk_responses.html', {'assets_w_responses':assets_w_responses,
                                                         'labelling_rules':labelling_rules,
                                                         'prompts':prompts})



@labeler_required
def view_asset_labels(request):

    assets_w_labels = api_get('get_asset_labels')

    batch_ids = []

    for label in assets_w_labels.values():
        batch_ids.append(int(label['data']['1'][0]['mturk_batch_id']))

    batch_ids = list(set(batch_ids))

    data = {'assets_w_labels':assets_w_labels,
            'batch_ids':batch_ids}

    return render(request, 'view_asset_labels.html', data)


@labeler_required
def reconcile_labels(request):

    assignment_id = ''.join(random.choices( string.ascii_letters + string.digits, k =20))
    labeler_source = 'reconcile_label'
    batch_type = request.GET.get('batch_type')
    task_type = request.GET.get('task_type')
    labeler_id = request.GET.get('labeler_id')
    batch_index  = request.GET.get('batch_index', None)
    rule_indexes  = json.loads(request.GET.get('rule_indexes', None))
    rule_index = int(rule_indexes[0])

    assets_to_label = api_get('get_disputed_assets', {
        'rule_index': rule_index,
        'task_type': task_type,
    })

    labelling_rules = api_get('get_labelling_rules', {
        'task_type': task_type,
        'rule_indexes': rule_indexes,
    })['labelling_rules']

    labelling_rules = sorted(labelling_rules, key=lambda x: x['rule_index'])

    collection_data = {
        "task_type":task_type,
        "labeler_id":labeler_id,  
        "assignment_id":assignment_id,
        "labeler_source":labeler_source,
    }

    return render(request, 'label_content.html', {'task_type':task_type,
                                                  'labeler_id':labeler_id,
                                                  'labeler_source':labeler_source,
                                                  'assets_to_label':assets_to_label,
                                                  'assets_to_label_count':len(assets_to_label),
                                                  'labelling_rules':labelling_rules,
                                                  'collection_data':collection_data,
                                                  'assignment_id':assignment_id                                                 
                                                  })

@labeler_required
def view_batch_labels(request):

    task_type = request.GET.get('task_type', 'asset_type')
    rule_index = int(request.GET.get('rule_index', 1))
    batch_index = int(request.GET.get('batch_index', 1))
    label_filter = request.GET.get('label_filter', 'only_yes')

    batch_of_assets_response = api_get('get_batch_for_viewing', {
        "task_type": task_type,
        "rule_index": rule_index,
        "batch_index": batch_index,
    })

    # print('-----------batch_of_assets--------------')
    # print(batch_of_assets)

    if 'assets_w_labels' in batch_of_assets_response and batch_of_assets_response['assets_w_labels']:
        batch_of_assets = pd.DataFrame(batch_of_assets_response['assets_w_labels'])
        
        if 'label' in batch_of_assets.columns:
            if label_filter == 'only_yes':
                batch_of_assets = batch_of_assets.query('label=="yes"')
            elif label_filter == 'only_no':
                batch_of_assets = batch_of_assets.query('label=="no"')
        else:
            batch_of_assets = pd.DataFrame()
    else:
        batch_of_assets = pd.DataFrame()

    # batch_of_assets = pd.DataFrame(batch_of_assets['assets_w_labels']) \
    # .sample(1000)



    # batch_of_assets = pd.DataFrame(batch_of_assets['assets_w_labels']) \
    # .query('color_type == "multi-color"')


    if not batch_of_assets.empty:
        label_counts = batch_of_assets \
        .groupby('label') \
        .agg(count = ('asset_id','count')) \
        .reset_index() \
        .to_dict(orient = 'records')
    else:
        label_counts = []

    labelling_rules = api_get('get_labelling_rules')

    rule_entry = []
    if 'labelling_rules' in labelling_rules:
        rules_df = pd.DataFrame(labelling_rules['labelling_rules'])
        if not rules_df.empty and 'task_type' in rules_df.columns and 'rule_index' in rules_df.columns:
            rule_entry = rules_df \
            .query("task_type == @task_type") \
            .query("rule_index == @rule_index") \
            .to_dict(orient = 'records')

    ##########################

    total_assets = len(batch_of_assets)

    labeler_id_options = list(User.objects.values_list('username', flat=True))
    label_type_filters = ['only_yes', 'only_no']

    if len(rule_entry) > 0:
        rule_entry = rule_entry[0]
    else:
        rule_entry = {'title':'No Rule Found', 'prompt':'', 'task_type':task_type, 'rule_index':rule_index}

    data = {"rule_entry":rule_entry,
            "label_counts":label_counts,
            "total_assets": total_assets,
            "labeler_id_options":labeler_id_options,
            "label_type_filters":label_type_filters,
            "label_filter":label_filter,
            "batch_of_assets":batch_of_assets.to_dict(orient = 'records')}

    try:
        return render(request, 'view_batch_labels.html', data)
    except Exception as e:
        print(f"Error rendering view_batch_labels: {e}")
        import traceback
        traceback.print_exc()
        raise e



@labeler_required
def view_labels(request):

    task_type = str(request.GET.get('task_type', 'asset_type')).strip()

    dark_ratios = pd.DataFrame(api_get('get_dark_ratios')) \
    .drop(['dark_label'],axis = 1) \
    .fillna(0) \
    .assign(dark_ratio = lambda x: (x.dark_ratio * 100).astype(int))
    
    dark_ratio_limits = {'min':dark_ratios['dark_ratio'].min(),
                         'max':dark_ratios['dark_ratio'].max()}
    
    # print('------Dark Ratios-------')
    # print(dark_ratios)
    # print(dark_ratio_limits)

    labeled_assets = pd.DataFrame(api_get('get_assets_w_rule_labels', {"task_type": task_type}))

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

    # print('------labeled_assets-1------')
    # print(labeled_assets)

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

    # print('------labeled_assets-2------')
    # print(labeled_assets)

    labelling_rules = pd.DataFrame(api_get('get_labelling_rules')['labelling_rules']) 

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


@admin_required
def manage_rules(request):
    
    labelling_rules = api_get('get_labelling_rules')
    
    rule_table = labelling_rules['labelling_rules']
    task_types = labelling_rules['task_type_set']

    data = {"task_types":task_types,
            "rule_table":rule_table}
    
    return render(request, 'manage_rules.html', data)





@admin_required
def view_prediction_labels(request):

    task_type = request.GET.get('task_type', 'asset_type')
    rule_index = int(request.GET.get('rule_index', 1))
    batch_index = request.GET.get('batch_index',None)
    label_type = request.GET.get("label_type",'mismatch')

    #################

    if batch_index is not None:
        batch_index = int(batch_index)

    #################


    rules_resp = api_get('get_labelling_rules')

    task_by_rule_options = pd.DataFrame(rules_resp['labelling_rules']) \
    .filter(['task_type', 'rule_index','title'])

    task_type_options = task_by_rule_options \
    .filter(['task_type']) \
    .drop_duplicates() 

    labelling_rules = pd.DataFrame(rules_resp['labelling_rules'])

    labelling_rules = labelling_rules \
    .query('task_type == @task_type') \
    .query('rule_index == @rule_index') 

    predictions_resp = api_get('get_predictions', {
        "rule_index": rule_index,
        "task_type": task_type,
        "batch_index": batch_index,
        "label_type": label_type,
    })

    prediction_data = pd.DataFrame(predictions_resp['prediction_data'])
    batch_counts = pd.DataFrame(predictions_resp['batch_counts'])

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
    labeler_id_options = list(User.objects.values_list('username', flat=True))
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



@labeler_required
def view_asset(request):

    asset_id = request.GET.get('asset_id', 158370)

    
    labelling_rules = api_get('get_labelling_rules')['labelling_rules']

    task_types = pd.DataFrame(labelling_rules) \
    .query('task_type != "select_primary_colors"') \
    .filter(['task_type']) \
    .drop_duplicates() \
    .squeeze() \
    .tolist()

    try:
        asset_labels = api_get('get_asset_labels', {"asset_id": asset_id})
        asset_metadata = asset_labels['asset_metadata'][0]
        asset = asset_labels['asset_data'][0]
        prompt_response = asset_labels['prompt_responses']
        labels = asset_labels['rule_labels']
    except Exception:
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



@admin_required
def view_label_issues(request):
    
    task_type = request.GET.get('task_type', 'color_fill_type')
    rule_index = int(request.GET.get('rule_index', 1))

    rules_resp = api_get('get_labelling_rules')

    task_by_rule_options = pd.DataFrame(rules_resp['labelling_rules']) \
    .filter(['task_type', 'rule_index','title'])

    task_type_options = task_by_rule_options \
    .filter(['task_type']) \
    .drop_duplicates() 

    labelling_rules = pd.DataFrame(rules_resp['labelling_rules'])

    labelling_rules = labelling_rules \
    .query('task_type == @task_type') \
    .query('rule_index == @rule_index') 

    assets_w_label_issues = api_get('get_assets_w_label_issues', {
        'task_type': task_type,
        'rule_index': rule_index,
    })

    assets_w_label_issues = pd.DataFrame(assets_w_label_issues) 
        
    label_types = ['model','manual']
    labeler_id_options = list(User.objects.values_list('username', flat=True))

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


@admin_required
def label_testing(request):

    session_data = api_get('get_label_testing_options', {"session_id": 2})

    experiments = session_data['data']

    data = {"experiments":experiments}

    return render(request, 'label_testing.html', data)


@admin_required
def view_model_results(request):

    rules_resp = api_get('get_labelling_rules')
    label_rules = [{'rule_index': e['rule_index'], 'task_type': e['task_type'], 'title': e['title']}
                   for e in rules_resp['labelling_rules']]
    label_rules = pd.DataFrame(label_rules)

    model_results = pd.DataFrame(api_get('get_model_results')['model_results']) \
    .merge(label_rules, on = ['rule_index','task_type'], how = 'left')

    # print('------model_results------')
    # print(model_results)

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
    .filter(['task_type','label', 'val_recall', 'val_precision','performant','val_mae'])


    # print('-----best_models------')
    # print(best_models)
    # print(best_models.columns)

    model_results = model_results \
    .groupby(['task_type', 'rule_index']) \
    .head(20) \
    .sort_values(by=['task_type', 'rule_index', 'score'], ascending=[True, True, False]) \
    .assign(index_column=lambda x: x.groupby(['task_type', 'rule_index']).cumcount() + 1) \
    .reset_index(drop=True)


    model_type_options = model_results['model_type'].unique()
    task_type_options = model_results['task_type'].unique()
    rule_index_options = model_results['title'].unique()
    model_labels = model_results['label'].unique()

    # print(model_results)

    model_labels = model_results \
    .filter(['title','label','task_type']) \
    .drop_duplicates() \
    .merge(best_models, on = ['label','task_type'], how = 'left')

    # print('-----model_labels------')
    # print(model_labels)


    data = {'model_results':model_results.to_dict(orient = 'records'),
            'model_labels':model_labels.to_dict(orient = 'records'),
            'model_type_options':model_type_options,
            'task_type_options':task_type_options,
            'rule_index_options':rule_index_options,
            }

    return render(request, 'view_model_results.html', data)



@labeler_required
def view_primary_colors(request):
    
    asset_primary_colors = pd.DataFrame(api_get('get_primary_colors'))

    # data = {}
    data = {'asset_primary_colors':asset_primary_colors.to_dict(orient = 'records')}

    return render(request, 'view_primary_colors.html', data)


@admin_required
def correct_mismatch_labels(request):

    task_type = request.GET.get('task_type', 'color_fill_type')
    rule_index = int(request.GET.get('rule_index', 2))
    labeler_id = request.GET.get('labeler_id', request.user.username)

    label_rules = api_get('get_labelling_rules', {
        'task_type': task_type,
        'rule_indexes': [rule_index],
    })['labelling_rules']

    prompt = label_rules[0]['prompt']

    mismatched_labels = api_get('get_mismatched_labels', {
        'task_type': task_type,
        'rule_index': rule_index,
    })['mistmatched_labels']

    mismatched_labels = pd.DataFrame(mismatched_labels) \
    .query('status == "active"')

    # print('-----mismatched_labels-------')
    # print(mismatched_labels)

    collection_data = {'task_type':task_type,
                       'labeler_source':'mismatch',
                       'labeler_id':labeler_id}

    data = {'mismatched_labels':mismatched_labels.to_dict(orient = 'records'),
            'collection_data':collection_data,
            'label_rules':label_rules,
            'prompt':prompt}

    return render(request, 'correct_mismatch_labels.html', data)




@labeler_required
def view_rough_fill(request):
    
    rough_fill_scores = pd.DataFrame(api_get('get_rough_fill_scores')['rough_fill_scores'])

    rough_fill_scores = rough_fill_scores \
    .sample(2000)

    # print('-------rough_fill_scores------')
    # print(rough_fill_scores)
    # print(rough_fill_scores.columns)

    rough_options = [ 
        {
        'metric_name':'roughness',
        'min': round(float(np.min(rough_fill_scores['roughness'])), 2),
        'max': round(float(np.max(rough_fill_scores['roughness'])), 2),
        'step':'0.01'
        },
    
        {
        'metric_name':'identical_count',
        'min': float(np.min(rough_fill_scores['identical_count'])),
        'max': float(np.max(rough_fill_scores['identical_count'])),
        'step':'.25'
        },

        {
        'metric_name':'estimated_peak_count',
        'min': float(np.min(rough_fill_scores['estimated_peak_count'])),
        'max': float(np.max(rough_fill_scores['estimated_peak_count'])),
        'step':'1'
        },

        {
        'metric_name':'score',
        'min': float(np.min(rough_fill_scores['score'])),
        'max': float(np.max(rough_fill_scores['score'])),
        'step':'0.01'
        },

        {
        'metric_name':'percent_rough',
        'min': float(np.min(rough_fill_scores['percent_rough'])),
        'max': float(np.max(rough_fill_scores['percent_rough'])),
        'step':'0.01'
        },

        {
        'metric_name':'histogram_group',
        'min': float(np.min(rough_fill_scores['histogram_group'])),
        'max': float(np.max(rough_fill_scores['histogram_group'])),
        'step':'1'
        }

    ]

    # print('------rough_metrics-------')
    # print(rough_options)



    data = {'rough_options':rough_options, 
            'rough_fill_scores':rough_fill_scores.to_dict(orient = 'records')}

    return render(request, 'view_rough_fill.html', data)




@labeler_required
def view_line_widths(request):
    
    line_widths = pd.DataFrame(api_get('get_line_widths'))

    line_widths = line_widths \
    .assign(line_width_bin=lambda x: pd.cut(  x['line_width'].clip(lower=2),
                                            bins=np.arange(-2, 22, 2).tolist() + [np.inf], 
                                            include_lowest=True,
                                            labels = False)) \
    .assign(prominence = lambda x: np.round(x['prominence']*100,0))





    # print('-------rough_fill_scores------')
    # print(line_widths)
    # print(line_widths.columns)
    # print(np.min(line_widths['line_width_bin']))
    # print(np.max(line_widths['line_width_bin']))

    line_width_options = [ 

        {
        'metric_name':'line_width',
        'min': np.min(line_widths['line_width_bin']),
        'max': np.max(line_widths['line_width_bin']),
        'step':'1'
        },
   
        {
        'metric_name':'prominence',
        'min': np.min(line_widths['prominence']),
        'max': np.max(line_widths['prominence']),
        'step':'.05'
        },

    ]

    line_widths = line_widths \
    .query('prominence > 85')

    # print('------rough_metrics-------')
    # print(line_width_options)



    data = {'line_width_options':line_width_options, 
            'line_widths':line_widths.to_dict(orient = 'records')}

    return render(request, 'view_line_widths.html', data)