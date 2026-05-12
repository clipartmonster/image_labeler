from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.staticfiles import finders
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Avg, F, Value, CharField
from django.db.models.functions import Concat

from django.conf import settings
from django.http import FileResponse, Http404

import os
import random
import string


import requests
import json
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor


def is_admin(request):
    """Return True if the logged-in user is a superuser (admin)."""
    if not request.user.is_authenticated:
        return False
    return request.user.is_superuser


@login_required
def change_password(request):
    """Force new users to set their own password on first login."""
    if request.method == "POST":
        new_pw = request.POST.get("new_password", "")
        confirm_pw = request.POST.get("confirm_password", "")

        if len(new_pw) < 8:
            return render(request, "change_password.html", {"error": "Password must be at least 8 characters."})
        if new_pw != confirm_pw:
            return render(request, "change_password.html", {"error": "Passwords do not match."})

        request.user.set_password(new_pw)
        request.user.save()

        profile = getattr(request.user, "profile", None)
        if profile:
            profile.must_change_password = False
            profile.save()

        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        return redirect("front_page")

    return render(request, "change_password.html", {})


@login_required
def front_page(request):

    data = {"user_is_admin": is_admin(request)}

    return render(request, "front_page.html", data)


@login_required
def assign_batch(request):
    """Admin-only: assign a sub-batch to a labeler."""
    from .models import BatchAssignment
    from django.contrib.auth.models import User
    from django.utils.dateparse import parse_date
    from django.utils import timezone
    from datetime import datetime

    if request.method != "POST" or not is_admin(request):
        return redirect("setup_session")

    username = request.POST.get("labeler_username")
    task_type = request.POST.get("task_type")
    rule_index = int(request.POST.get("rule_index", 1))
    batch_id = int(request.POST.get("batch_id", 1))
    large_sub_batch = int(request.POST.get("large_sub_batch", 1))
    payment = request.POST.get("payment_amount", settings.LABELER_PAY_PER_BATCH)
    deadline_str = request.POST.get("deadline")

    user = User.objects.get(username=username)
    deadline_date = parse_date(deadline_str)
    deadline_dt = timezone.make_aware(datetime.combine(deadline_date, datetime.max.time().replace(microsecond=0)))

    BatchAssignment.objects.update_or_create(
        user=user,
        task_type=task_type,
        rule_index=rule_index,
        batch_id=batch_id,
        large_sub_batch=large_sub_batch,
        defaults={
            "payment_amount": payment,
            "deadline": deadline_dt,
        },
    )

    return redirect(f"/label_images/setup_session/?task_type={task_type}")


@login_required
def select_line_widths(request):

    labeler_id = request.GET.get("labeler_id", "Steve")
    task_type = request.GET.get("task_type", "asset_type")
    rule_index = request.GET.get("rule_index", 1)
    batch_id = request.GET.get("batch_id", 1)
    large_sub_batch = request.GET.get("large_sub_batch", 1)

    api_url = f"{settings.LABELING_API_BASE_URL}/get_asset_batch/"

    data = {
        "batch_type": "large_sub_batch",
        "large_sub_batch": large_sub_batch,
        "batch_id": batch_id,
        "task_type": "line_width_type",
        "rule_index": rule_index,
    }

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    print("hello")

    assets_to_label = json.loads(response.content)["asset_batch"]

    print(assets_to_label)

    sampling_array = [[1 + col + row * 3 for col in range(3)] for row in range(3)]

    data = {
        "sampling_array": sampling_array,
        "assets_to_label": assets_to_label,
        "labeler_id": labeler_id,
    }

    return render(request, "select_line_widths.html", data)


@login_required
def select_primary_colors(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_asset_batch/"

    data = {
        "batch_type": "large_sub_batch",
        "large_sub_batch": 1,
        "batch_id": 2,
        "task_type": "select_primary_colors",
        "rule_index": 1,
    }

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    print("hello")

    assets_to_label = json.loads(response.content)["asset_batch"]
    # total_in_full_set_to_label = json.loads(response.content)['total_in_full_set_to_label']
    # total_in_set_to_label = json.loads(response.content)['total_in_set_to_label']

    print(assets_to_label)

    data = {"assets_to_label": assets_to_label}

    return render(request, "select_primary_colors.html", data)


@login_required
def show_images(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_color_labels/"

    data = {"source": "initial_training_set", "samples": 50}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    assets_to_label = json.loads(response.content)["assets_to_label"]
    total_in_full_set_to_label = json.loads(response.content)[
        "total_in_full_set_to_label"
    ]
    total_in_set_to_label = json.loads(response.content)["total_in_set_to_label"]

    color_labels = [
        {"label": "red", "hex_code": "#ff0000"},
        {"label": "orange", "hex_code": "#ff7d00"},
        {"label": "yellow", "hex_code": "#FFFF00"},
        {"label": "green", "hex_code": "#00FF00"},
        {"label": "blue", "hex_code": "#0000FF"},
        {"label": "purple", "hex_code": "#7D00FF"},
        {"label": "brown", "hex_code": "#9B4B19"},
        {"label": "tan", "hex_code": "#ffc896"},
        {"label": "pink", "hex_code": "#f5b4c3"},
        {"label": "gray", "hex_code": "#AFAFAF"},
        {"label": "black", "hex_code": "#000000"},
        {"label": "white", "hex_code": "#FFFFFF"},
    ]

    spread_values = ["25%", "50%", "75%", "100%"]

    return render(
        request,
        "show_images.html",
        {
            "assets_to_label": assets_to_label,
            "total_in_set_to_label": total_in_set_to_label,
            "total_in_full_set_to_label": total_in_full_set_to_label,
            "reference_panels": range(9),
            "color_labels": color_labels,
            "spread_values": spread_values,
            "labeler_id": "Steve",
        },
    )


@login_required
def setup_session(request):
    from labeling_api.views import _build_session_options
    from .models import BatchAssignment
    from django.utils import timezone

    labeler_id = request.GET.get("labeler_id", "Steve")
    task_type = request.GET.get("task_type", "asset_type")
    rule_index = request.GET.get("rule_index", 1)
    batch_id = request.GET.get("batch_index", 1)

    user_is_admin = is_admin(request)

    if user_is_admin:
        try:
            session_options = _build_session_options(task_type)
        except Exception as exc:
            return HttpResponse(
                f"Failed to build session options: {exc}",
                status=502,
                content_type="text/plain; charset=utf-8",
            )

        from django.contrib.auth.models import User
        from labeling_api.models import labelling_rules, label_data_selected_assets_new
        labeler_users = User.objects.filter(is_staff=True, is_superuser=False).values_list("username", flat=True)

        all_rules = list(labelling_rules.objects.exclude(task_type="color_type")
                         .values("task_type", "rule_index", "title")
                         .order_by("task_type", "rule_index"))

        all_sub_batches = list(label_data_selected_assets_new.objects
                               .values("task_type", "rule_index", "batch_id", "large_sub_batch")
                               .distinct()
                               .order_by("task_type", "rule_index", "batch_id", "large_sub_batch"))

        selected_options = {
            "labeler_id": labeler_id,
            "task_type": task_type,
            "rule_index": rule_index,
            "batch_id": batch_id,
        }

        return render(
            request,
            "setup_session.html",
            {
                "session_options": session_options,
                "selected_options": selected_options,
                "user_is_admin": True,
                "labeler_users": list(labeler_users),
                "default_pay": settings.LABELER_PAY_PER_BATCH,
                "assign_rules_json": json.dumps(all_rules, default=str),
                "assign_sub_batches_json": json.dumps(all_sub_batches, default=str),
            },
        )
    else:
        now = timezone.now()
        assignments = BatchAssignment.objects.filter(
            user=request.user, completed_at__isnull=True
        ).order_by("deadline")

        assignment_data = []
        for a in assignments:
            from labeling_api.models import label_data_selected_assets_new, prompt_responses
            total = label_data_selected_assets_new.objects.filter(
                task_type=a.task_type,
                rule_index=a.rule_index,
                batch_id=a.batch_id,
                large_sub_batch=a.large_sub_batch,
            ).count()

            completed = prompt_responses.objects.filter(
                task_type=a.task_type,
                rule_index=a.rule_index,
                asset_id__in=label_data_selected_assets_new.objects.filter(
                    task_type=a.task_type,
                    rule_index=a.rule_index,
                    batch_id=a.batch_id,
                    large_sub_batch=a.large_sub_batch,
                ).values_list("asset_id", flat=True),
            ).values("asset_id").annotate(
                cnt=Count("id")
            ).filter(cnt__gte=2).count()

            days_left = (a.deadline - now).days
            if days_left < 0:
                deadline_status = "overdue"
            elif days_left <= 2:
                deadline_status = "urgent"
            else:
                deadline_status = "ok"

            assignment_data.append({
                "id": a.id,
                "task_type": a.task_type,
                "rule_index": a.rule_index,
                "batch_id": a.batch_id,
                "large_sub_batch": a.large_sub_batch,
                "payment_amount": a.payment_amount,
                "deadline": a.deadline,
                "deadline_status": deadline_status,
                "warning_severity": a.deadline_warning_severity,
                "total": total,
                "completed": completed,
                "progress_pct": int((completed / total * 100) if total > 0 else 0),
            })

        return render(
            request,
            "setup_session.html",
            {
                "user_is_admin": False,
                "assignments": assignment_data,
            },
        )


@login_required
def initialize_session(request):
    if request.method == "POST":

        print(request.POST.get("source"))

        # selected_source = request.POST.get('source')
        # selected_features = request.POST.get('features')
        # labeler_id = request.POST.get('labeler_id')
        # # Save the selected source in the session
        # request.session['selected_source'] = selected_source
        # request.session['features'] = selected_features
        # request.session['labeler_id'] = labeler_id
        return redirect("show_images")
    return redirect("select_source")


@login_required
def internal(request):

    task_type = request.GET.get("task_type")
    labeler_source = request.GET.get("label_source", None)
    label_type = request.GET.get("label_type")
    labeler_id = request.GET.get("labeler_id")
    samples = request.GET.get("samples", 50)
    asset_id = request.GET.get("asset_id", None)
    test_the_labeler = request.GET.get("test_the_labeler", False)
    batch_index = request.GET.get("batch_index", None)
    rule_indexes = json.loads(request.GET.get("rule_indexes", None))
    add_lure_questions = request.GET.get("add_lure_questions", None)

    api_url = f"{settings.LABELING_API_BASE_URL}/get_asset_batch/"

    data = {"batch_index": batch_index, "lure_samples": 2}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    assets_to_label = json.loads(response.content)


@login_required
def mturk_redirect(request):

    task_type = request.GET.get("task_type")
    labeler_source = request.GET.get("label_source", None)
    label_type = request.GET.get("label_type")
    labeler_id = request.GET.get("labeler_id")
    samples = request.GET.get("samples", 50)
    asset_id = request.GET.get("asset_id", None)
    sandbox_flag = request.GET.get("sandbox_flag", None)
    test_the_labeler = request.GET.get("test_the_labeler", False)
    batch_id = request.GET.get("batch_id", None)
    large_sub_batch = request.GET.get("large_sub_batch", None)
    mturk_batch_id = request.GET.get("mturk_batch_id", 0)
    rule_indexes = json.loads(request.GET.get("rule_indexes", None))
    add_lure_questions = request.GET.get("add_lure_questions", None)

    rule_index = int(rule_indexes[0])

    assignment_id = request.GET.get("assignmentId", None)
    hit_id = request.GET.get("hitId")
    worker_id = request.GET.get("workerId", "not_assigned")

    # Create an assignment id when not provided one. Important for submission status
    if assignment_id == None:
        assignment_id = "".join(
            random.choices(string.ascii_letters + string.digits, k=20)
        )

    from datetime import datetime
    import pytz

    # Define the Central Time zone
    central_time_zone = pytz.timezone("America/Chicago")

    # Get the current time in Central Time
    central_time = datetime.now(central_time_zone)

    print("----------------------------------------------------")
    # print(central_time.strftime("%Y-%m-%d %I:%M:%S %p"))
    # print('assignment id:' + assignment_id)
    # print('worker id:' + worker_id)
    # print('----------------------------------------------------')

    if labeler_source == "MTurk":
        labeler_id = worker_id

    # print('-----------varaibles-----------')
    # print(batch_id, task_type, rule_index,labeler_id)

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    def fetch_assets():
        api_url = f"{settings.LABELING_API_BASE_URL}/get_asset_batch/"
        data = {
            "batch_type": "large_sub_batch",
            "large_sub_batch": large_sub_batch,
            "batch_id": batch_id,
            "task_type": task_type,
            "rule_index": rule_index,
        }
        response = requests.get(api_url, json=data, headers=header)
        return json.loads(response.content)

    def fetch_rules():
        api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"
        data = {"task_type": task_type, "rule_indexes": rule_indexes}
        response = requests.get(api_url, json=data, headers=header)
        return dict(json.loads(response.content))["labelling_rules"]

    def fetch_test_questions():
        if bool(test_the_labeler) == True:
            # print('preparing test questions')
            api_url = f"{settings.LABELING_API_BASE_URL}/get_test_questions/"
            data = {"samples": 2}
            response = requests.get(api_url, json=data, headers=header)
            return dict(json.loads(response.content))
        return []

    # Execute requests in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_assets = executor.submit(fetch_assets)
        future_rules = executor.submit(fetch_rules)
        future_test = executor.submit(fetch_test_questions)

        assets_content = future_assets.result()
        labelling_rules = future_rules.result()
        test_questions = future_test.result()

    assets_to_label = assets_content["asset_batch"]

    # print('|-------assets to label----------|')
    # print(pd.DataFrame(assets_to_label))

    collection_data = {
        "task_type": task_type,
        "labeler_source": labeler_source,
        "label_type": label_type,
        "labeler_id": labeler_id,
        "assignment_id": assignment_id,
        "hit_id": hit_id,
        "mturk_batch_id": mturk_batch_id,
        "rule_index": rule_indexes[0],
    }

    # Test questions are already fetched in parallel above

    return render(
        request,
        "label_content.html",
        {
            "task_type": task_type,
            "label": label_type,
            "assets_to_label": assets_to_label,
            "labelling_rules": labelling_rules,
            "collection_data": collection_data,
            "labeler_source": labeler_source,
            "assignment_id": assignment_id,
            "hit_id": hit_id,
            "rule_index": rule_index,
            "sandbox_flag": sandbox_flag,
            "test_the_labeler": test_the_labeler,
            "test_questions": test_questions,
        },
    )


@login_required
def view_mturk_responses(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {
        "task_type": "art_type",
        "label_type": "clip_art",
        "rule_indexes": [1, 2, 3, 4, 5],
    }

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    labelling_rules = dict(json.loads(response.content))["labeling_rules"]["clip_art"]

    prompts = {(item["prompt"], item["rule_index"]) for item in labelling_rules}
    prompts = [
        {"prompt": prompt, "rule_index": rule_index} for prompt, rule_index in prompts
    ]

    api_url = f"{settings.LABELING_API_BASE_URL}/get_prompt_responses/"

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, headers=header)
    assets_w_responses = json.loads(response.content)

    # print('----------------------------------')
    # print(assets_w_responses)
    # print(labelling_rules)

    return render(
        request,
        "view_mturk_responses.html",
        {
            "assets_w_responses": assets_w_responses,
            "labelling_rules": labelling_rules,
            "prompts": prompts,
        },
    )


@login_required
def view_asset_labels(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_asset_labels/"

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, headers=header)
    assets_w_labels = json.loads(response.content)

    batch_ids = []

    for label in assets_w_labels.values():
        print(label)
        print("--------------")
        batch_ids.append(int(label["data"]["1"][0]["mturk_batch_id"]))

    batch_ids = list(set(batch_ids))

    data = {"assets_w_labels": assets_w_labels, "batch_ids": batch_ids}

    return render(request, "view_asset_labels.html", data)


@login_required
def reconcile_labels(request):

    assignment_id = "".join(random.choices(string.ascii_letters + string.digits, k=20))
    labeler_source = "reconcile_label"
    batch_type = request.GET.get("batch_type")
    task_type = request.GET.get("task_type")
    labeler_id = request.GET.get("labeler_id")
    batch_index = request.GET.get("batch_index", None)
    rule_indexes = json.loads(request.GET.get("rule_indexes", None))
    rule_index = int(rule_indexes[0])

    api_url = f"{settings.LABELING_API_BASE_URL}/get_disputed_assets/"

    data = {"rule_index": rule_index, "task_type": task_type}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    assets_to_label = json.loads(response.content)

    # print('-----69-69-------')
    # print(assets_to_label)
    # print('size of assets to label')
    # print(len(assets_to_label))

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {"task_type": task_type, "rule_indexes": rule_indexes}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    labelling_rules = dict(json.loads(response.content))["labelling_rules"]

    print("----VvV----")
    print(labelling_rules)

    labelling_rules = sorted(labelling_rules, key=lambda x: x["rule_index"])

    collection_data = {
        "task_type": task_type,
        "labeler_id": labeler_id,
        "assignment_id": assignment_id,
        "labeler_source": labeler_source,
    }

    print(collection_data)
    print(task_type)

    return render(
        request,
        "label_content.html",
        {
            "task_type": task_type,
            "labeler_id": labeler_id,
            "labeler_source": labeler_source,
            "assets_to_label": assets_to_label,
            "assets_to_label_count": len(assets_to_label),
            "labelling_rules": labelling_rules,
            "collection_data": collection_data,
            "assignment_id": assignment_id,
        },
    )


@login_required
def view_batch_labels(request):

    task_type = request.GET.get("task_type", "asset_type")
    rule_index = int(request.GET.get("rule_index", 1))
    batch_index = int(request.GET.get("batch_index", 1))
    label_filter = request.GET.get("label_filter", "only_yes")
    sort_by = request.GET.get("sort_by", "date_desc")

    print(task_type, rule_index, batch_index)

    ###############################
    # get batches assets

    api_url = f"{settings.LABELING_API_BASE_URL}/get_batch_for_viewing/"

    data = {
        "task_type": task_type,
        "rule_index": rule_index,
        "batch_index": batch_index,
    }

    # print(data)

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    batch_of_assets_response = json.loads(response.content)

    # print('-----------batch_of_assets--------------')
    # print(batch_of_assets)

    if (
        "assets_w_labels" in batch_of_assets_response
        and batch_of_assets_response["assets_w_labels"]
    ):
        batch_of_assets = pd.DataFrame(batch_of_assets_response["assets_w_labels"])

        if "label" in batch_of_assets.columns:
            if label_filter == "only_yes":
                batch_of_assets = batch_of_assets.query('label=="yes"')
            elif label_filter == "only_no":
                batch_of_assets = batch_of_assets.query('label=="no"')

        batch_of_assets = batch_of_assets.drop_duplicates(subset="asset_id")

        if "date_labeled" in batch_of_assets.columns:
            ascending = sort_by == "date_asc"
            batch_of_assets = batch_of_assets.sort_values("date_labeled", ascending=ascending)
        else:
            batch_of_assets = pd.DataFrame()
    else:
        batch_of_assets = pd.DataFrame()

    # batch_of_assets = pd.DataFrame(batch_of_assets['assets_w_labels']) \
    # .sample(1000)

    # batch_of_assets = pd.DataFrame(batch_of_assets['assets_w_labels']) \
    # .query('color_type == "multi-color"')

    if not batch_of_assets.empty:
        label_counts = (
            batch_of_assets.groupby("label")
            .agg(count=("asset_id", "count"))
            .reset_index()
            .to_dict(orient="records")
        )
    else:
        label_counts = []

    ###############################
    # get labelling rules
    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    labelling_rules = dict(json.loads(response.content))

    rule_entry = []
    all_rules = []
    if "labelling_rules" in labelling_rules:
        rules_df = pd.DataFrame(labelling_rules["labelling_rules"])
        if (
            not rules_df.empty
            and "task_type" in rules_df.columns
            and "rule_index" in rules_df.columns
        ):
            rule_entry = (
                rules_df.query("task_type == @task_type")
                .query("rule_index == @rule_index")
                .to_dict(orient="records")
            )
            all_rules = rules_df[["task_type", "rule_index", "title"]].to_dict(orient="records")

    print("------------")
    print(rule_entry)

    ##########################

    total_assets = len(batch_of_assets)

    labeler_id_options = ["Steve", "Noah"]
    label_type_filters = ["only_yes", "only_no"]

    if len(rule_entry) > 0:
        rule_entry = rule_entry[0]
    else:
        rule_entry = {
            "title": "No Rule Found",
            "prompt": "",
            "task_type": task_type,
            "rule_index": rule_index,
        }

    data = {
        "rule_entry": rule_entry,
        "all_rules": all_rules,
        "label_counts": label_counts,
        "total_assets": total_assets,
        "labeler_id_options": labeler_id_options,
        "label_type_filters": label_type_filters,
        "label_filter": label_filter,
        "sort_by": sort_by,
        "batch_of_assets": batch_of_assets.to_dict(orient="records"),
    }

    try:
        return render(request, "view_batch_labels.html", data)
    except Exception as e:
        print(f"Error rendering view_batch_labels: {e}")
        import traceback

        traceback.print_exc()
        raise e


@login_required
def view_labels(request):

    task_type = str(request.GET.get("task_type", "asset_type")).strip()

    print("-----task_type-----")
    print(task_type)

    #################################

    api_url = f"{settings.LABELING_API_BASE_URL}/get_dark_ratios/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    dark_ratios = (
        pd.DataFrame(json.loads(response.content))
        .drop(["dark_label"], axis=1)
        .fillna(0)
        .assign(dark_ratio=lambda x: (x.dark_ratio * 100).astype(int))
    )

    dark_ratio_limits = {
        "min": dark_ratios["dark_ratio"].min(),
        "max": dark_ratios["dark_ratio"].max(),
    }

    # print('------Dark Ratios-------')
    # print(dark_ratios)
    # print(dark_ratio_limits)

    #################################

    api_url = f"{settings.LABELING_API_BASE_URL}/get_assets_w_rule_labels/"

    data = {"task_type": task_type}
    # data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    labeled_assets = pd.DataFrame(json.loads(response.content))

    task_types = (
        pd.DataFrame(labeled_assets)["task_type"].drop_duplicates().sort_values()
    )

    rule_options = (
        pd.DataFrame(labeled_assets)
        .filter(["rule_index"])
        .drop_duplicates()
        .sort_values(["rule_index"])
        .reset_index(drop=True)
    )

    asset_links = (
        pd.DataFrame(labeled_assets)
        .filter(["asset_id", "image_link"])
        .drop_duplicates()
    )
    labeled_assets = (
        labeled_assets.filter(["asset_id", "rule_index", "label"])
        .drop_duplicates()
        .assign(label=lambda x: x["label"].astype(int))
        .assign(rule_index=lambda x: "rule_index_" + x["rule_index"].astype(str))
        .pivot(index="asset_id", columns="rule_index", values="label")
        .merge(asset_links, how="left", on="asset_id")
        .dropna()
        .astype("Int8", errors="ignore")
    )

    labeled_assets = (
        labeled_assets.merge(dark_ratios, on="asset_id", how="left")
        .fillna(101)
        .sort_values("dark_ratio", ascending=True)
    )

    # print('------labeled_assets-1------')
    # print(labeled_assets)

    ####################
    # need to create a set of rule_idex, label pairs for building class attributes of each asset (These are used for filtering)
    asset_rule_pairs = (
        pd.DataFrame(labeled_assets)
        .drop("image_link", axis=1)
        .melt(id_vars="asset_id", var_name="rule_index", value_name="label")
        .groupby("asset_id")
        .apply(lambda x: list(zip(x["rule_index"], x["label"])))
        .reset_index(name="rule_pairs")
    )

    labeled_assets = labeled_assets.merge(
        asset_rule_pairs, on="asset_id", how="left"
    ).to_dict(orient="records")

    # print('------labeled_assets-2------')
    # print(labeled_assets)

    #######################
    # get labelling rule title

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    labelling_rules = dict(json.loads(response.content))

    labelling_rules = pd.DataFrame(labelling_rules["labelling_rules"])

    labelling_rules = (
        labelling_rules.filter(["task_type", "rule_index", "title"])
        .query("task_type == @task_type")
        .merge(rule_options.assign(active="yes"), on="rule_index", how="left")
        .dropna()
        .reset_index()
    )

    rule_options = rule_options.merge(
        labelling_rules, on="rule_index", how="left"
    ).to_dict(orient="records")

    data = {
        "rule_options": rule_options,
        "labeled_assets": labeled_assets,
        "dark_ratio_limits": dark_ratio_limits,
        "total_available_images": len(labeled_assets),
    }

    # data = {}

    return render(request, "view_labels.html", data)


@login_required
def manage_rules(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    labelling_rules = dict(json.loads(response.content))

    rule_table = labelling_rules["labelling_rules"]
    task_types = labelling_rules["task_type_set"]

    data = {"task_types": task_types, "rule_table": rule_table}

    return render(request, "manage_rules.html", data)


@login_required
def view_prediction_labels(request):

    task_type = request.GET.get("task_type", "asset_type")
    rule_index = int(request.GET.get("rule_index", 1))
    batch_index = request.GET.get("batch_index", None)
    label_type = request.GET.get("label_type", "mismatch")

    print(task_type, rule_index, batch_index, label_type)

    #################

    if batch_index is not None:
        batch_index = int(batch_index)

    #################

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    task_by_rule_options = pd.DataFrame(
        dict(json.loads(response.content))["labelling_rules"]
    ).filter(["task_type", "rule_index", "title"])

    task_type_options = task_by_rule_options.filter(["task_type"]).drop_duplicates()

    labelling_rules = pd.DataFrame(
        dict(json.loads(response.content))["labelling_rules"]
    )

    labelling_rules = labelling_rules.query("task_type == @task_type").query(
        "rule_index == @rule_index"
    )

    api_url = f"{settings.LABELING_API_BASE_URL}/get_predictions/"

    data = {
        "rule_index": rule_index,
        "task_type": task_type,
        "batch_index": batch_index,
        "label_type": label_type,
    }

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    prediction_data = pd.DataFrame(
        dict(json.loads(response.content))["prediction_data"]
    )
    batch_counts = pd.DataFrame(dict(json.loads(response.content))["batch_counts"])

    if len(prediction_data) > 0:

        # round probability for formatting
        prediction_data = prediction_data.sort_values(
            "probability", ascending=False
        ).assign(probability=lambda x: np.round(x["probability"], 3))

        mismatch_counts = (
            prediction_data.assign(
                status=lambda x: np.where(
                    x["manual_label"] == "yes", "false_negative", "false_positive"
                )
            )
            .groupby("status")
            .agg(count=("asset_id", "count"))
            .to_dict()["count"]
        )

    else:
        prediction_data = pd.DataFrame()
        mismatch_counts = pd.DataFrame()

    if label_type == "only_no":
        prediction_data = prediction_data.iloc[1:3000]

    label_types = ["model", "manual"]
    labeler_id_options = ["Steve", "Noah"]
    label_type_filters = ["only_yes", "only_no", "mismatch"]

    data = {
        "prediction_data": prediction_data.to_dict(orient="records"),
        "batch_counts": batch_counts.to_dict(orient="records"),
        "mismatch_counts": mismatch_counts,
        "labeler_id_options": labeler_id_options,
        "task_type_options": task_type_options.to_dict(orient="records"),
        "task_by_rule_options": task_by_rule_options.to_dict(orient="records"),
        "task_type": task_type,
        "rule_index": rule_index,
        "label_types": label_types,
        "label_title": labelling_rules["title"].values[0],
        "label_type_filters": label_type_filters,
    }

    return render(request, "view_prediction_labels.html", data)


@login_required
def view_asset(request):

    asset_id = request.GET.get("asset_id", 158370)

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    labelling_rules = dict(json.loads(response.content))["labelling_rules"]

    # print('-------------')
    # print(labelling_rules)

    task_types = (
        pd.DataFrame(labelling_rules)
        .query('task_type != "select_primary_colors"')
        .filter(["task_type"])
        .drop_duplicates()
        .squeeze()
        .tolist()
    )

    api_url = f"{settings.LABELING_API_BASE_URL}/get_asset_labels/"

    data = {"asset_id": asset_id}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    print("--------statust code---------")
    print(response.status_code)

    if response.status_code != 500:
        asset_labels = json.loads(response.content)

        asset_metadata = asset_labels["asset_metadata"][0]
        asset = asset_labels["asset_data"][0]
        prompt_response = asset_labels["prompt_responses"]
        labels = asset_labels["rule_labels"]

    else:
        asset_labels = []
        asset_metadata = []
        asset = []
        prompt_response = []
        labels = []

    data = {
        "task_types": task_types,
        "labelling_rules": labelling_rules,
        "asset_metadata": asset_labels,
        "asset": asset,
        "prompt_responses": prompt_response,
        "labels": labels,
    }

    return render(request, "view_asset.html", data)


@login_required
def view_label_issues(request):

    task_type = request.GET.get("task_type", "color_fill_type")
    rule_index = int(request.GET.get("rule_index", 1))

    print("------------------")
    print(task_type)
    print(rule_index)

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    task_by_rule_options = pd.DataFrame(
        dict(json.loads(response.content))["labelling_rules"]
    ).filter(["task_type", "rule_index", "title"])

    task_type_options = task_by_rule_options.filter(["task_type"]).drop_duplicates()

    labelling_rules = pd.DataFrame(
        dict(json.loads(response.content))["labelling_rules"]
    )

    labelling_rules = labelling_rules.query("task_type == @task_type").query(
        "rule_index == @rule_index"
    )

    api_url = f"{settings.LABELING_API_BASE_URL}/get_assets_w_label_issues/"

    data = {"task_type": task_type, "rule_index": rule_index}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    assets_w_label_issues = json.loads(response.content)

    assets_w_label_issues = pd.DataFrame(assets_w_label_issues)

    print("--------assets_w_label_issues---------")
    print(assets_w_label_issues)

    label_types = ["model", "manual"]
    labeler_id_options = ["Steve", "Noah"]

    # data = {'assets':assets_w_label_issues}

    data = {
        "assets": assets_w_label_issues,
        "labeler_id_options": labeler_id_options,
        "task_type_options": task_type_options.to_dict(orient="records"),
        "task_by_rule_options": task_by_rule_options.to_dict(orient="records"),
        "task_type": task_type,
        "rule_index": rule_index,
        "label_types": label_types,
        "label_title": labelling_rules["title"].values[0],
    }

    return render(request, "view_label_issues.html", data)


@login_required
def label_testing(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_label_testing_options/"

    data = {"session_id": 2}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    session_data = json.loads(response.content)

    experiments = session_data["data"]

    data = {"experiments": experiments}

    print(data)

    return render(request, "label_testing.html", data)


@login_required
def view_model_results(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json={}, headers=header)
    label_rules = json.loads(response.content)

    label_rules = label_rules["labelling_rules"]

    label_rules = [
        {
            "rule_index": entry["rule_index"],
            "task_type": entry["task_type"],
            "title": entry["title"],
        }
        for entry in label_rules
    ]
    label_rules = pd.DataFrame(label_rules)

    # print('------label_rules-------')
    # print(label_rules)

    api_url = f"{settings.LABELING_API_BASE_URL}/get_model_results/"

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json={}, headers=header)
    model_results = json.loads(response.content)

    model_results = pd.DataFrame(model_results["model_results"]).merge(
        label_rules, on=["rule_index", "task_type"], how="left"
    )

    # print('------model_results------')
    # print(model_results)

    model_results["label"] = model_results["task_type"].str[
        0:2
    ].str.upper() + model_results["rule_index"].astype(str)

    model_results = model_results.sort_values(
        by=["label", "status"], ascending=[True, False]
    )

    model_result = model_results["date"] = pd.to_datetime(
        model_results["created_at"]
    ).dt.date

    best_models = (
        model_results.assign(
            performant=lambda x: np.where(
                (x.val_recall > 0.88) & (x.val_precision > 0.88), "close", "no"
            )
        )
        .assign(
            performant=lambda x: np.where(
                (x.val_recall > 0.9) & (x.val_precision > 0.9), "yes", x.performant
            )
        )
        .sort_values(["task_type", "rule_index", "score"], ascending=False)
        .groupby(["task_type", "rule_index"])
        .head(1)
        .reset_index()
        .filter(
            [
                "task_type",
                "label",
                "val_recall",
                "val_precision",
                "performant",
                "val_mae",
            ]
        )
    )

    # print('-----best_models------')
    # print(best_models)
    # print(best_models.columns)

    model_results = (
        model_results.groupby(["task_type", "rule_index"])
        .head(20)
        .sort_values(
            by=["task_type", "rule_index", "score"], ascending=[True, True, False]
        )
        .assign(
            index_column=lambda x: x.groupby(["task_type", "rule_index"]).cumcount() + 1
        )
        .reset_index(drop=True)
    )

    model_type_options = model_results["model_type"].unique()
    task_type_options = model_results["task_type"].unique()
    rule_index_options = model_results["title"].unique()
    model_labels = model_results["label"].unique()

    # print(model_results)

    model_labels = (
        model_results.filter(["title", "label", "task_type"])
        .drop_duplicates()
        .merge(best_models, on=["label", "task_type"], how="left")
    )

    # print('-----model_labels------')
    # print(model_labels)

    data = {
        "model_results": model_results.to_dict(orient="records"),
        "model_labels": model_labels.to_dict(orient="records"),
        "model_type_options": model_type_options,
        "task_type_options": task_type_options,
        "rule_index_options": rule_index_options,
    }

    return render(request, "view_model_results.html", data)


@login_required
def view_primary_colors(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_primary_colors/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    primary_colors = json.loads(response.content)

    # print(primary_colors)

    asset_primary_colors = pd.DataFrame(primary_colors)

    # data = {}
    data = {"asset_primary_colors": asset_primary_colors.to_dict(orient="records")}

    return render(request, "view_primary_colors.html", data)


@login_required
def correct_mismatch_labels(request):

    task_type = request.GET.get("task_type", "color_fill_type")
    rule_index = int(request.GET.get("rule_index", 2))
    labeler_id = request.GET.get("labeler_id", "Steve")

    # print(task_type)
    # print(rule_index)

    ##############################

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    ##############################

    api_url = f"{settings.LABELING_API_BASE_URL}/get_labelling_rules/"

    data = {"task_type": task_type, "rule_indexes": [rule_index]}

    response = requests.get(api_url, json=data, headers=header)
    # print(response)
    label_rules = json.loads(response.content)["labelling_rules"]

    prompt = label_rules[0]["prompt"]

    # print('-----label_rules-------')
    # print(label_rules)

    ##############################

    api_url = f"{settings.LABELING_API_BASE_URL}/get_mismatched_labels/"

    data = {"task_type": task_type, "rule_index": rule_index}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)
    mismatched_labels = json.loads(response.content)["mistmatched_labels"]

    mismatched_labels = pd.DataFrame(mismatched_labels).query('status == "active"')

    # print('-----mismatched_labels-------')
    # print(mismatched_labels)

    collection_data = {
        "task_type": task_type,
        "labeler_source": "mismatch",
        "labeler_id": labeler_id,
    }

    data = {
        "mismatched_labels": mismatched_labels.to_dict(orient="records"),
        "collection_data": collection_data,
        "label_rules": label_rules,
        "prompt": prompt,
    }

    return render(request, "correct_mismatch_labels.html", data)


@login_required
def view_rough_fill(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_rough_fill_scores/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    rough_fill_scores = pd.DataFrame(json.loads(response.content)["rough_fill_scores"])

    rough_fill_scores = rough_fill_scores.sample(2000)

    # print('-------rough_fill_scores------')
    # print(rough_fill_scores)
    # print(rough_fill_scores.columns)

    rough_options = [
        {
            "metric_name": "roughness",
            "min": round(float(np.min(rough_fill_scores["roughness"])), 2),
            "max": round(float(np.max(rough_fill_scores["roughness"])), 2),
            "step": "0.01",
        },
        {
            "metric_name": "identical_count",
            "min": float(np.min(rough_fill_scores["identical_count"])),
            "max": float(np.max(rough_fill_scores["identical_count"])),
            "step": ".25",
        },
        {
            "metric_name": "estimated_peak_count",
            "min": float(np.min(rough_fill_scores["estimated_peak_count"])),
            "max": float(np.max(rough_fill_scores["estimated_peak_count"])),
            "step": "1",
        },
        {
            "metric_name": "score",
            "min": float(np.min(rough_fill_scores["score"])),
            "max": float(np.max(rough_fill_scores["score"])),
            "step": "0.01",
        },
        {
            "metric_name": "percent_rough",
            "min": float(np.min(rough_fill_scores["percent_rough"])),
            "max": float(np.max(rough_fill_scores["percent_rough"])),
            "step": "0.01",
        },
        {
            "metric_name": "histogram_group",
            "min": float(np.min(rough_fill_scores["histogram_group"])),
            "max": float(np.max(rough_fill_scores["histogram_group"])),
            "step": "1",
        },
    ]

    # print('------rough_metrics-------')
    # print(rough_options)

    data = {
        "rough_options": rough_options,
        "rough_fill_scores": rough_fill_scores.to_dict(orient="records"),
    }

    return render(request, "view_rough_fill.html", data)


@login_required
def view_line_widths(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_line_widths/"

    data = {}

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    response = requests.get(api_url, json=data, headers=header)

    # print(response.content)
    line_widths = pd.DataFrame(json.loads(response.content))

    line_widths = line_widths.assign(
        line_width_bin=lambda x: pd.cut(
            x["line_width"].clip(lower=2),
            bins=np.arange(-2, 22, 2).tolist() + [np.inf],
            include_lowest=True,
            labels=False,
        )
    ).assign(prominence=lambda x: np.round(x["prominence"] * 100, 0))

    # print('-------rough_fill_scores------')
    # print(line_widths)
    # print(line_widths.columns)
    # print(np.min(line_widths['line_width_bin']))
    # print(np.max(line_widths['line_width_bin']))

    line_width_options = [
        {
            "metric_name": "line_width",
            "min": np.min(line_widths["line_width_bin"]),
            "max": np.max(line_widths["line_width_bin"]),
            "step": "1",
        },
        {
            "metric_name": "prominence",
            "min": np.min(line_widths["prominence"]),
            "max": np.max(line_widths["prominence"]),
            "step": ".05",
        },
    ]

    line_widths = line_widths.query("prominence > 85")

    # print('------rough_metrics-------')
    # print(line_width_options)

    data = {
        "line_width_options": line_width_options,
        "line_widths": line_widths.to_dict(orient="records"),
    }

    return render(request, "view_line_widths.html", data)


@login_required
def label_search_results(request):

    api_url = f"{settings.LABELING_API_BASE_URL}/get_search_results/"

    # Get parameters from request, with defaults
    search_string = request.GET.get("search_string", "hawk")
    selected_result_index = request.GET.get("selected_result_index", "5")

    # Convert selected_result_index to int if it's a string
    try:
        selected_result_index = int(selected_result_index)
    except (ValueError, TypeError):
        selected_result_index = 5

    data = {
        "search_string": search_string,
        "selected_result_index": selected_result_index,
    }

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    print(f"=== DEBUG: Calling get_search_results API ===")
    print(f"Search string being sent: '{search_string}'")
    print(f"Selected result index: {selected_result_index}")

    response = requests.get(api_url, json=data, headers=header)

    # Initialize default values
    selected_image = None
    search_results = []

    # Check if response is successful
    if response.status_code != 200:
        print(f"Error: API returned status code {response.status_code}")
        print(f"Response content: {response.content}")
        print(f"Response text: {response.text}")
    else:
        # Check if response has content
        if not response.text or not response.text.strip():
            print(f"Error: API returned empty response")
            print(f"Response status code: {response.status_code}")
        else:
            # Try to parse JSON response
            try:
                # Handle potential NaN values in JSON by replacing them with null
                response_text = response.text.strip()
                cleaned_text = response_text.replace(": NaN", ": null").replace(
                    ":NaN", ":null"
                )
                response_json = json.loads(cleaned_text)

                # Extract selected_image and search_results from the response
                selected_image = response_json.get("selected_image")
                # If selected_image is a list, get the first item
                if isinstance(selected_image, list) and len(selected_image) > 0:
                    selected_image = selected_image[0]
                search_results = response_json.get("search_results", [])

                # Debug: Check if selected_image matches the search
                if selected_image:
                    print(f"=== DEBUG: API Response ===")
                    print(f"Selected image asset_id: {selected_image.get('asset_id')}")
                    print(f"Number of search results: {len(search_results)}")
                    if search_results and len(search_results) > 0:
                        print(
                            f"First search result asset_id: {search_results[0].get('asset_id')}"
                        )
                        print(
                            f"First few search result asset_ids: {[r.get('asset_id') for r in search_results[:5]]}"
                        )

                # Remove the first listing if it matches the selected_image asset_id
                if selected_image and selected_image.get("asset_id") and search_results:
                    selected_asset_id = selected_image.get("asset_id")
                    # Check if first result matches selected image
                    if search_results[0].get("asset_id") == selected_asset_id:
                        search_results = search_results[1:]  # Remove first item

                # If search results are empty, get a new search term
                if not search_results or len(search_results) == 0:
                    print(
                        "=== Search results are empty. Fetching new search term... ==="
                    )
                    from django.urls import reverse

                    # Call get_search_term API to get a new search term
                    get_search_term_url = (
                        f"{settings.LABELING_API_BASE_URL}/get_search_term/"
                    )

                    # Get batch_id and labeler_id from request if available
                    batch_id = request.GET.get("batch_id") or request.POST.get(
                        "batch_id"
                    )
                    labeler_id = request.GET.get("labeler_id") or request.POST.get(
                        "labeler_id", "Steve"
                    )

                    # Prepare POST data
                    get_search_term_data = {}
                    if batch_id:
                        try:
                            get_search_term_data["batch_id"] = int(batch_id)
                        except (ValueError, TypeError):
                            print(
                                f"Warning: Invalid batch_id '{batch_id}', skipping get_search_term call"
                            )
                            batch_id = None
                    if labeler_id:
                        get_search_term_data["labeler_id"] = labeler_id

                    # Only call get_search_term if we have batch_id
                    if batch_id:
                        print(
                            f"Calling get_search_term with data: {get_search_term_data}"
                        )
                        get_search_term_response = requests.post(
                            get_search_term_url,
                            json=get_search_term_data,
                            headers=header,
                        )

                        print(
                            f"get_search_term response status: {get_search_term_response.status_code}"
                        )

                        if get_search_term_response.status_code == 200:
                            try:
                                get_search_term_text = (
                                    get_search_term_response.text.strip()
                                )
                                cleaned_text = get_search_term_text.replace(
                                    ": NaN", ": null"
                                ).replace(":NaN", ":null")
                                get_search_term_response_data = json.loads(cleaned_text)

                                print(
                                    f"get_search_term response data: {get_search_term_response_data}"
                                )

                                if (
                                    get_search_term_response_data
                                    and not get_search_term_response_data.get("error")
                                ):
                                    search_topic = get_search_term_response_data.get(
                                        "search_topic", ""
                                    )
                                    asset_type = get_search_term_response_data.get(
                                        "asset_type", ""
                                    )
                                    selected_index = get_search_term_response_data.get(
                                        "selected_index", 0
                                    )

                                    if search_topic and asset_type:
                                        # Redirect to the same page with new search parameters
                                        combined_string = f"{search_topic} {asset_type}"
                                        redirect_url = reverse("label_search_results")
                                        redirect_params = f"search_string={combined_string}&selected_result_index={selected_index}"
                                        if batch_id:
                                            redirect_params += f"&batch_id={batch_id}"
                                        if labeler_id:
                                            redirect_params += (
                                                f"&labeler_id={labeler_id}"
                                            )
                                        return redirect(
                                            f"{redirect_url}?{redirect_params}"
                                        )
                            except json.JSONDecodeError as e:
                                print(f"Error parsing get_search_term response: {e}")
                        else:
                            print(
                                f"get_search_term returned error status: {get_search_term_response.status_code}"
                            )
                            print(
                                f"Response content: {get_search_term_response.text[:500]}"
                            )
                    else:
                        print(
                            "No batch_id available in request, skipping get_search_term call. Frontend will handle this."
                        )
                    # If we can't get a new search term, continue with empty results
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Response status code: {response.status_code}")
                print(f"Response content: {response.content}")
                print(f"Response text: {response.text}")

    print(selected_image)

    # Convert search_results to DataFrame for processing
    search_results_df = pd.DataFrame(search_results)

    # Only filter by platform_name if DataFrame is not empty and has the column
    if not search_results_df.empty and "platform_name" in search_results_df.columns:
        invalid_platforms = [
            "clipart library",
            "vectorstock",
            "pngegg",
            "pixabay",
            "clipart.com",
            "freepik",
        ]
        invalid_platforms = []

        search_results_df = search_results_df.query(
            "platform_name not in @invalid_platforms"
        )

    # Get all results for replacement pool (before limiting)
    all_results = search_results_df.to_dict(orient="records")

    # Limit to first 20 for display (we already removed the first one if it matched selected_image)
    # So we'll show 20 unique listings (not including the reference image)
    search_results_df = search_results_df.head(20)

    data = {
        "selected_image": selected_image,
        "search_results": search_results_df.to_dict(orient="records"),
        "all_search_results": all_results,
        "search_string": search_string,
        "selected_result_index": selected_result_index,
    }

    # print(data)

    return render(request, "label_search_results.html", data)


# ===========================================================================
# Workforce management views
# ===========================================================================

from .decorators import admin_required, labeler_required, admin_required_ajax
from .models import (
    BatchAssignment, LabelingSession, GoldStandardLabel,
    AdjudicationDecision, UserProfile,
)


# ---------------------------------------------------------------------------
# Labeler: earnings view
# ---------------------------------------------------------------------------

@labeler_required
def labeler_earnings(request):
    assignments = BatchAssignment.objects.filter(user=request.user).order_by("-deadline")
    completed = [a for a in assignments if a.completed_at]
    pending = [a for a in assignments if not a.completed_at]

    completed_total = sum(a.payment_amount for a in completed)
    pending_total = sum(a.payment_amount for a in pending)

    return render(request, "labeler_earnings.html", {
        "completed_assignments": completed,
        "pending_assignments": pending,
        "completed_total": completed_total,
        "pending_total": pending_total,
    })


# ---------------------------------------------------------------------------
# Admin: labeler list with search/filter
# ---------------------------------------------------------------------------

@admin_required
def admin_labeler_list(request):
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "real")
    show_test = request.GET.get("show_test", "0") == "1"

    qs = User.objects.filter(is_superuser=False)

    if search:
        qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search)
                       | Q(first_name__icontains=search) | Q(last_name__icontains=search))

    cutoff = timezone.now() - timedelta(days=getattr(settings, "LABELER_INACTIVE_DAYS", 30))

    if status_filter == "real":
        qs = qs.filter(Q(is_staff=True) | Q(is_superuser=True))
    elif status_filter == "test":
        qs = qs.filter(is_staff=False, is_superuser=False)
    elif status_filter == "active":
        qs = qs.filter(labeling_sessions__ended_at__gte=cutoff).distinct()
        if not show_test:
            qs = qs.filter(Q(is_staff=True) | Q(is_superuser=True))
    elif status_filter == "inactive":
        qs = qs.exclude(labeling_sessions__ended_at__gte=cutoff)
        if not show_test:
            qs = qs.filter(Q(is_staff=True) | Q(is_superuser=True))
    else:
        if not show_test:
            qs = qs.filter(Q(is_staff=True) | Q(is_superuser=True))

    labelers = []
    for u in qs.order_by("username"):
        total_assignments = u.batch_assignments.count()
        completed_assignments = u.batch_assignments.filter(completed_at__isnull=False).count()
        labelers.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.get_full_name(),
            "is_staff": u.is_staff,
            "is_active": u.is_active,
            "total_assignments": total_assignments,
            "completed_assignments": completed_assignments,
        })

    return render(request, "admin_labeler_list.html", {
        "labelers": labelers,
        "search": search,
        "status_filter": status_filter,
        "show_test": show_test,
    })


@admin_required_ajax
def admin_toggle_staff(request):
    """AJAX: toggle User.is_staff for a labeler."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.contrib.auth.models import User

    data = json.loads(request.body)
    user_id = data.get("user_id")
    try:
        user = User.objects.get(pk=user_id, is_superuser=False)
    except User.DoesNotExist:
        return JsonResponse({"error": "labeler not found"}, status=404)

    user.is_staff = not user.is_staff
    user.save(update_fields=["is_staff"])
    return JsonResponse({"user_id": user.id, "is_staff": user.is_staff})


# ---------------------------------------------------------------------------
# Admin: bulk batch assignment
# ---------------------------------------------------------------------------

@admin_required
def admin_bulk_assign(request):
    from django.contrib.auth.models import User
    from labeling_api.models import label_data_selected_assets_new, labelling_rules

    labeler_users = list(
        User.objects.filter(is_staff=True, is_superuser=False)
        .order_by("username")
        .values("id", "username")
    )

    all_sub_batches = list(
        label_data_selected_assets_new.objects
        .values("task_type", "rule_index", "batch_id", "large_sub_batch")
        .distinct()
        .order_by("task_type", "rule_index", "batch_id", "large_sub_batch")
    )

    all_rules = list(
        labelling_rules.objects.exclude(task_type="color_type")
        .values("task_type", "rule_index", "title")
        .order_by("task_type", "rule_index")
    )

    existing = list(
        BatchAssignment.objects
        .values("user_id", "task_type", "rule_index", "batch_id", "large_sub_batch")
    )

    return render(request, "admin_bulk_assign.html", {
        "labeler_users_json": json.dumps(labeler_users, default=str),
        "sub_batches_json": json.dumps(all_sub_batches, default=str),
        "rules_json": json.dumps(all_rules, default=str),
        "existing_json": json.dumps(existing, default=str),
        "default_pay": settings.LABELER_PAY_PER_BATCH,
        "default_num_labelers": getattr(settings, "LABELER_DEFAULT_NUM_LABELERS", 2),
    })


@admin_required_ajax
def admin_bulk_assign_save(request):
    """AJAX: create BatchAssignments for each (sub-batch, labeler) pair."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from django.contrib.auth.models import User
    from django.utils.dateparse import parse_date
    from django.utils import timezone
    from datetime import datetime

    data = json.loads(request.body)
    sub_batches = data.get("sub_batches", [])
    labeler_ids = data.get("labeler_ids", [])
    payment = data.get("payment_amount", settings.LABELER_PAY_PER_BATCH)
    deadline_str = data.get("deadline")
    num_labelers = data.get("num_labelers_target", getattr(settings, "LABELER_DEFAULT_NUM_LABELERS", 2))
    severity = data.get("deadline_warning_severity", getattr(settings, "LABELER_DEFAULT_DEADLINE_WARNING", "medium"))

    if not sub_batches or not labeler_ids or not deadline_str:
        return JsonResponse({"error": "sub_batches, labeler_ids, and deadline are required"}, status=400)

    deadline_date = parse_date(deadline_str)
    if not deadline_date:
        return JsonResponse({"error": "invalid deadline"}, status=400)
    deadline_dt = timezone.make_aware(datetime.combine(deadline_date, datetime.max.time().replace(microsecond=0)))

    users = {u.id: u for u in User.objects.filter(pk__in=labeler_ids)}
    created = 0
    skipped = 0

    for sb in sub_batches:
        for uid in labeler_ids:
            user = users.get(uid)
            if not user:
                skipped += 1
                continue
            _, was_created = BatchAssignment.objects.update_or_create(
                user=user,
                task_type=sb["task_type"],
                rule_index=sb["rule_index"],
                batch_id=sb["batch_id"],
                large_sub_batch=sb["large_sub_batch"],
                defaults={
                    "payment_amount": payment,
                    "deadline": deadline_dt,
                    "num_labelers_target": num_labelers,
                    "deadline_warning_severity": severity,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

    return JsonResponse({"created": created, "skipped": skipped})


# ---------------------------------------------------------------------------
# Admin: performance dashboard
# ---------------------------------------------------------------------------

@admin_required
def admin_performance(request):
    from django.contrib.auth.models import User

    labelers = list(
        User.objects.filter(is_staff=True, is_superuser=False)
        .order_by("username")
        .values("id", "username")
    )
    return render(request, "admin_performance.html", {
        "labelers_json": json.dumps(labelers, default=str),
    })


@admin_required_ajax
def admin_performance_data(request):
    """AJAX: return throughput, accuracy, on-time stats for a labeler."""
    from django.contrib.auth.models import User
    from labeling_api.models import prompt_responses

    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id required"}, status=400)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "user not found"}, status=404)

    # --- Throughput ---
    sessions = LabelingSession.objects.filter(user=user, ended_at__isnull=False)
    total_labels = sum(s.labels_completed for s in sessions)
    total_hours = sum((s.duration_hours or 0) for s in sessions)
    throughput = round(total_labels / total_hours, 1) if total_hours > 0 else None

    # --- Accuracy vs gold ---
    labeler_id_str = user.username
    gold_labels = {
        (g.asset_id, g.task_type, g.rule_index): g.correct_response
        for g in GoldStandardLabel.objects.all()
    }
    gold_total = 0
    gold_correct = 0
    if gold_labels:
        responses = prompt_responses.objects.filter(labeler_id=labeler_id_str)
        for r in responses:
            key = (r.asset_id, r.task_type, r.rule_index)
            if key in gold_labels:
                gold_total += 1
                if r.prompt_response == gold_labels[key]:
                    gold_correct += 1
    accuracy = round(gold_correct / gold_total * 100, 1) if gold_total > 0 else None

    # --- On-time completion ---
    assignments = BatchAssignment.objects.filter(user=user)
    completed = assignments.filter(completed_at__isnull=False)
    total_completed = completed.count()
    on_time = completed.filter(completed_at__lte=F("deadline")).count()
    on_time_rate = round(on_time / total_completed * 100, 1) if total_completed > 0 else None

    return JsonResponse({
        "username": user.username,
        "throughput_labels_per_hour": throughput,
        "total_labels": total_labels,
        "total_hours": round(total_hours, 1),
        "accuracy_pct": accuracy,
        "gold_total": gold_total,
        "gold_correct": gold_correct,
        "on_time_pct": on_time_rate,
        "total_completed": total_completed,
        "on_time_count": on_time,
        "total_assignments": assignments.count(),
    })


# ---------------------------------------------------------------------------
# Admin: adjudication queue
# ---------------------------------------------------------------------------

@admin_required
def admin_adjudication(request):
    return render(request, "admin_adjudication.html", {
        "threshold": getattr(settings, "LABELER_DISAGREEMENT_THRESHOLD", 1.0),
    })


@admin_required_ajax
def admin_adjudication_list(request):
    """AJAX: return assets with labeler disagreements that haven't been adjudicated."""
    from labeling_api.models import prompt_responses, label_data_selected_assets_new

    task_type = request.GET.get("task_type", "")
    rule_index = request.GET.get("rule_index", "")
    page = int(request.GET.get("page", 1))
    page_size = 50

    threshold = getattr(settings, "LABELER_DISAGREEMENT_THRESHOLD", 1.0)

    qs = prompt_responses.objects.all()
    if task_type:
        qs = qs.filter(task_type=task_type)
    if rule_index:
        qs = qs.filter(rule_index=int(rule_index))

    # Group by (asset_id, task_type, rule_index), find disagreements
    grouped = (
        qs.values("asset_id", "task_type", "rule_index")
        .annotate(
            total=Count("id"),
            yes_count=Count("id", filter=Q(prompt_response="yes")),
        )
        .filter(total__gte=2)
    )

    already_adjudicated = set(
        AdjudicationDecision.objects.values_list("asset_id", "task_type", "rule_index")
    )

    disagreements = []
    for row in grouped:
        key = (row["asset_id"], row["task_type"], row["rule_index"])
        if key in already_adjudicated:
            continue
        total = row["total"]
        yes = row["yes_count"]
        no = total - yes
        majority = max(yes, no)
        agreement = majority / total
        if agreement < threshold:
            # Fetch image_link for display
            asset = label_data_selected_assets_new.objects.filter(
                asset_id=row["asset_id"]
            ).values("image_link").first()

            responses = list(
                prompt_responses.objects.filter(
                    asset_id=row["asset_id"],
                    task_type=row["task_type"],
                    rule_index=row["rule_index"],
                ).values("labeler_id", "prompt_response", "datetime_created")
            )

            disagreements.append({
                "asset_id": row["asset_id"],
                "task_type": row["task_type"],
                "rule_index": row["rule_index"],
                "total_responses": total,
                "yes_count": yes,
                "no_count": no,
                "agreement_pct": round(agreement * 100, 1),
                "image_link": (asset or {}).get("image_link", ""),
                "responses": [
                    {"labeler_id": r["labeler_id"], "response": r["prompt_response"],
                     "datetime": str(r["datetime_created"])}
                    for r in responses
                ],
            })

    disagreements.sort(key=lambda x: x["agreement_pct"])
    total_count = len(disagreements)
    start = (page - 1) * page_size
    end = start + page_size

    return JsonResponse({
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "items": disagreements[start:end],
    })


@admin_required_ajax
def admin_adjudicate_save(request):
    """AJAX: save an adjudication decision."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = json.loads(request.body)
    asset_id = data.get("asset_id")
    task_type = data.get("task_type")
    rule_index = data.get("rule_index")
    decision = data.get("decision")
    notes = data.get("notes", "")

    if not all([asset_id, task_type, rule_index is not None, decision]):
        return JsonResponse({"error": "asset_id, task_type, rule_index, decision required"}, status=400)

    obj, created = AdjudicationDecision.objects.update_or_create(
        asset_id=asset_id,
        task_type=task_type,
        rule_index=rule_index,
        defaults={
            "decided_by": request.user,
            "decision": decision,
            "notes": notes,
        },
    )

    return JsonResponse({"status": "saved", "created": created, "id": obj.id})


# ---------------------------------------------------------------------------
# Admin: gold-standard import from reconciled labels
# ---------------------------------------------------------------------------

@admin_required_ajax
def admin_import_gold(request):
    """AJAX: import reconciled labels from assets_w_rule_labels as gold standards."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from labeling_api.models import assets_w_rule_labels

    data = json.loads(request.body)
    task_type = data.get("task_type", "")
    rule_index = data.get("rule_index")
    min_agreement = float(data.get("min_agreement", 0.9))

    qs = assets_w_rule_labels.objects.filter(percent_agree__gte=min_agreement)
    if task_type:
        qs = qs.filter(task_type=task_type)
    if rule_index is not None:
        qs = qs.filter(rule_index=int(rule_index))

    created = 0
    for row in qs:
        correct = "yes" if row.label == 1 else "no"
        _, was_created = GoldStandardLabel.objects.update_or_create(
            asset_id=row.asset_id,
            task_type=row.task_type,
            rule_index=row.rule_index,
            defaults={"correct_response": correct},
        )
        if was_created:
            created += 1

    return JsonResponse({"imported": created, "total_candidates": qs.count()})


# ---------------------------------------------------------------------------
# Admin: sub-batch completion stats (AJAX, scoped by task_type for speed)
# ---------------------------------------------------------------------------

@admin_required_ajax
def admin_subbatch_completion(request):
    """Return completion stats for sub-batches filtered by task_type."""
    from labeling_api.models import label_data_selected_assets_new, prompt_responses
    from collections import defaultdict

    task_type = request.GET.get("task_type", "")
    if not task_type:
        return JsonResponse({"error": "task_type required"}, status=400)

    # Assets with 2+ responses for this task_type
    done_ids = set(
        prompt_responses.objects
        .filter(task_type=task_type)
        .values("asset_id", "rule_index")
        .annotate(cnt=Count("id"))
        .filter(cnt__gte=2)
        .values_list("asset_id", flat=True)
    )

    # Tally per sub-batch
    stats = defaultdict(lambda: [0, 0])  # [total, done]
    for row in (
        label_data_selected_assets_new.objects
        .filter(task_type=task_type)
        .values_list("asset_id", "rule_index", "batch_id", "large_sub_batch")
    ):
        key = f"{task_type}|{row[1]}|{row[2]}|{row[3]}"
        stats[key][0] += 1
        if row[0] in done_ids:
            stats[key][1] += 1

    result = {}
    for key, (total, done) in stats.items():
        result[key] = {"total": total, "done": done, "complete": done >= total and total > 0}

    return JsonResponse(result)
