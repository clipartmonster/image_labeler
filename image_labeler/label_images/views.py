from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.staticfiles import finders
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
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
    bonus = request.POST.get("bonus_amount", "0")
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
            "bonus_amount": bonus,
            "deadline": deadline_dt,
        },
    )

    return redirect(f"/label_images/setup_session/?task_type={task_type}")


@login_required
def select_line_widths(request):

    labeler_id = request.GET.get("labeler_id", request.user.username)
    batch_id = request.GET.get("batch_id", 1)
    large_sub_batch = request.GET.get("large_sub_batch", 1)

    rule_indexes_raw = request.GET.get("rule_indexes", "[]")
    try:
        rule_indexes = json.loads(rule_indexes_raw)
    except (json.JSONDecodeError, TypeError):
        rule_indexes = rule_indexes_raw
    if not isinstance(rule_indexes, list):
        rule_indexes = [rule_indexes]
    rule_index = int(rule_indexes[0]) if rule_indexes else int(request.GET.get("rule_index", 2))

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
    assets_to_label = json.loads(response.content)["asset_batch"]

    # Exclude assets that this labeler has already sampled
    from labeling_api.models import line_width_sample_table
    already_sampled = set(
        line_width_sample_table.objects
        .filter(labeler_id=labeler_id)
        .values_list("asset_id", flat=True)
    )
    assets_to_label = [a for a in assets_to_label if a["asset_id"] not in already_sampled]

    sampling_array = [[1 + col + row * 3 for col in range(3)] for row in range(3)]

    data = {
        "sampling_array": sampling_array,
        "assets_to_label": assets_to_label,
        "labeler_id": labeler_id,
        "rule_index": rule_index,
    }

    return render(request, "select_line_widths.html", data)


@login_required
def measure_line_widths(request):
    """Measurement-tool based line-width labeling (replaces the 9-section circle approach)."""

    labeler_id = request.GET.get("labeler_id", request.user.username)
    batch_id = request.GET.get("batch_id", 1)
    large_sub_batch = request.GET.get("large_sub_batch", 1)

    rule_indexes_raw = request.GET.get("rule_indexes", "[]")
    try:
        rule_indexes = json.loads(rule_indexes_raw)
    except (json.JSONDecodeError, TypeError):
        rule_indexes = rule_indexes_raw
    if not isinstance(rule_indexes, list):
        rule_indexes = [rule_indexes]
    rule_index = int(rule_indexes[0]) if rule_indexes else int(request.GET.get("rule_index", 2))

    header = {
        "Content-Type": "application/json",
        "Authorization": settings.API_ACCESS_KEY,
    }

    api_url = f"{settings.LABELING_API_BASE_URL}/get_asset_batch/"
    data = {
        "batch_type": "large_sub_batch",
        "large_sub_batch": large_sub_batch,
        "batch_id": batch_id,
        "task_type": "line_width_type",
        "rule_index": rule_index,
        "labeler_id": labeler_id,
    }
    response = requests.get(api_url, json=data, headers=header)
    assets_to_label = json.loads(response.content)["asset_batch"]

    return render(request, "measure_line_widths.html", {
        "assets_to_label": assets_to_label,
        "labeler_id": labeler_id,
        "rule_index": rule_index,
        "batch_id": batch_id,
        "large_sub_batch": large_sub_batch,
        "total_count": len(assets_to_label),
    })


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
            "labeler_id": request.user.username,
        },
    )


@login_required
def setup_session(request):
    from labeling_api.views import _build_session_options
    from .models import BatchAssignment
    from django.utils import timezone

    labeler_id = request.GET.get("labeler_id", request.user.username)
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
        from labeling_api.models import label_data_selected_assets_new, prompt_responses, labelling_rules as LR
        from .models import TrainingBatchAsset

        rule_titles = {}
        for r in LR.objects.exclude(task_type="color_type").values("task_type", "rule_index", "title"):
            rule_titles[(r["task_type"], r["rule_index"])] = r["title"]

        # Always show training batches (even completed); only show incomplete work batches
        training_qs = BatchAssignment.objects.filter(
            user=request.user, is_training=True,
        ).order_by("completed_at", "deadline")
        work_qs = BatchAssignment.objects.filter(
            user=request.user, is_training=False, completed_at__isnull=True,
        ).order_by("deadline")

        # Build set of features with completed training
        completed_training_features = set(
            training_qs.filter(completed_at__isnull=False)
            .values_list("task_type", "rule_index")
        )

        training_assignments = []
        for a in training_qs:
            total = TrainingBatchAsset.objects.filter(assignment=a).count()
            is_done = a.completed_at is not None
            training_assignments.append({
                "id": a.id,
                "task_type": a.task_type,
                "rule_index": a.rule_index,
                "feature_name": rule_titles.get((a.task_type, a.rule_index), ""),
                "batch_id": a.batch_id,
                "large_sub_batch": a.large_sub_batch,
                "payment_amount": a.payment_amount,
                "total": total,
                "completed": total if is_done else 0,
                "progress_pct": 100 if is_done else 0,
                "is_training": True,
                "training_done": is_done,
            })

        from labeling_api.models import label_issues_table, line_width_sample_table

        work_assignments = []
        for a in work_qs:
            batch_asset_ids = set(
                label_data_selected_assets_new.objects.filter(
                    task_type=a.task_type,
                    rule_index=a.rule_index,
                    batch_id=a.batch_id,
                    large_sub_batch=a.large_sub_batch,
                ).values_list("asset_id", flat=True)
            )
            total = len(batch_asset_ids)

            if a.task_type == "line_width_type":
                labeled_ids = set(
                    line_width_sample_table.objects.filter(
                        asset_id__in=batch_asset_ids,
                        labeler_id=request.user.username,
                    ).values_list("asset_id", flat=True).distinct()
                )
            else:
                labeled_ids = set(
                    prompt_responses.objects.filter(
                        task_type=a.task_type,
                        rule_index=a.rule_index,
                        labeler_id=request.user.username,
                        asset_id__in=batch_asset_ids,
                    ).values_list("asset_id", flat=True).distinct()
                )
            # Count flagged assets as completed too
            flagged_ids = set(
                label_issues_table.objects.filter(
                    asset_id__in=batch_asset_ids,
                ).values_list("asset_id", flat=True)
            )
            completed = len(labeled_ids | flagged_ids)

            # Backfill: mark assignment complete if all assets are covered
            if total > 0 and completed >= total:
                from django.utils import timezone as tz
                a.completed_at = tz.now()
                a.save(update_fields=["completed_at"])
                continue

            days_left = (a.deadline - now).days
            if days_left < 0:
                deadline_status = "overdue"
            elif days_left <= 2:
                deadline_status = "urgent"
            else:
                deadline_status = "ok"

            training_required = (
                (a.task_type, a.rule_index) not in completed_training_features
                and not (a.task_type == "line_width_type" and a.rule_index == 2)
            )
            work_assignments.append({
                "id": a.id,
                "task_type": a.task_type,
                "rule_index": a.rule_index,
                "feature_name": rule_titles.get((a.task_type, a.rule_index), ""),
                "batch_id": a.batch_id,
                "large_sub_batch": a.large_sub_batch,
                "payment_amount": a.payment_amount,
                "bonus_amount": getattr(a, "bonus_amount", 0) or 0,
                "deadline": a.deadline,
                "deadline_status": deadline_status,
                "total": total,
                "completed": completed,
                "progress_pct": int((completed / total * 100) if total > 0 else 0),
                "is_training": False,
                "training_required": training_required,
            })

        from collections import OrderedDict
        def _group_by_task(items):
            groups = OrderedDict()
            for a in items:
                groups.setdefault(a["task_type"], []).append(a)
            return list(groups.items())

        return render(
            request,
            "setup_session.html",
            {
                "user_is_admin": False,
                "assignments": training_assignments + work_assignments,
                "training_groups": _group_by_task(training_assignments),
                "work_groups": _group_by_task(work_assignments),
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
    labeler_id = request.GET.get("labeler_id", request.user.username)
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
    labeler_id = request.GET.get("labeler_id", request.user.username)
    samples = request.GET.get("samples", 50)
    asset_id = request.GET.get("asset_id", None)
    sandbox_flag = request.GET.get("sandbox_flag", None)
    test_the_labeler = request.GET.get("test_the_labeler", False)
    batch_id = request.GET.get("batch_id", None)
    large_sub_batch = request.GET.get("large_sub_batch", None)
    mturk_batch_id = request.GET.get("mturk_batch_id", 0)
    rule_indexes_raw = request.GET.get("rule_indexes", "[]")
    try:
        rule_indexes = json.loads(rule_indexes_raw)
    except (json.JSONDecodeError, TypeError):
        rule_indexes = rule_indexes_raw
    if not isinstance(rule_indexes, list):
        rule_indexes = [rule_indexes]
    add_lure_questions = request.GET.get("add_lure_questions", None)
    is_training = request.GET.get("is_training", "0") == "1"

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
            "labeler_id": labeler_id,
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

    training_answers = {}
    if is_training:
        from .models import TrainingBatchAsset

        ta_list = list(
            TrainingBatchAsset.objects.filter(
                assignment__user=request.user,
                assignment__task_type=task_type,
                assignment__rule_index=rule_index,
                assignment__is_training=True,
            ).values("asset_id", "image_link", "correct_label")
        )

        assets_to_label = [{"asset_id": t["asset_id"], "image_link": t["image_link"]} for t in ta_list]
        for t in ta_list:
            training_answers[str(t["asset_id"])] = t["correct_label"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_rules = executor.submit(fetch_rules)
            future_test = executor.submit(fetch_test_questions)
            labelling_rules = future_rules.result()
            test_questions = future_test.result()
    else:
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_assets = executor.submit(fetch_assets)
            future_rules = executor.submit(fetch_rules)
            future_test = executor.submit(fetch_test_questions)

            assets_content = future_assets.result()
            labelling_rules = future_rules.result()
            test_questions = future_test.result()

        assets_to_label = assets_content["asset_batch"]

    if not is_training and not assets_to_label and not request.user.is_superuser:
        from django.contrib import messages
        messages.info(request, "This batch is already complete — all assets have been labeled or flagged.")
        return redirect("setup_session")

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

    from .models import RuleGuide
    rule_guides = list(
        RuleGuide.objects.filter(task_type=task_type, rule_index=rule_index)
        .prefetch_related("directives", "reference_images")
    )

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
            "is_training": is_training,
            "training_answers_json": json.dumps(training_answers),
            "rule_guides": rule_guides,
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
    labeler_id = request.GET.get("labeler_id", request.user.username)
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

    from .models import RuleGuide
    rule_guides = list(
        RuleGuide.objects.filter(task_type=task_type, rule_index=rule_index)
        .prefetch_related("directives", "reference_images")
    )

    return render(
        request,
        "label_content.html",
        {
            "task_type": task_type,
            "rule_index": rule_index,
            "labeler_id": labeler_id,
            "labeler_source": labeler_source,
            "assets_to_label": assets_to_label,
            "assets_to_label_count": len(assets_to_label),
            "labelling_rules": labelling_rules,
            "collection_data": collection_data,
            "assignment_id": assignment_id,
            "rule_guides": rule_guides,
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

    from django.contrib.auth.models import User
    labeler_id_options = list(User.objects.filter(is_staff=True).values_list("username", flat=True))
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
    from django.contrib.auth.models import User
    labeler_id_options = list(User.objects.filter(is_staff=True).values_list("username", flat=True))
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
    from django.contrib.auth.models import User
    labeler_id_options = list(User.objects.filter(is_staff=True).values_list("username", flat=True))

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
    from labeling_api.models import (
        model_results_table, production_models_table,
        rule_index_thresholds_table, labelling_rules as LR,
    )

    _db = "prod" if "prod" in settings.DATABASES else "default"

    rule_titles = {}
    for r in LR.objects.exclude(task_type="color_type").values("task_type", "rule_index", "title"):
        rule_titles[(r["task_type"], r["rule_index"])] = r["title"]

    # model_results_prod is SSOT for what's in production.
    prod_rows = list(
        production_models_table.objects.using(_db)
        .filter(active=True)
        .values("version_id", "dev_id")
    )

    # Threshold data keyed by model_version
    thresh_version_map = {}
    for t in rule_index_thresholds_table.objects.using(_db).values():
        thresh_version_map[t["model_version"]] = {
            "task_type": t["task_type"],
            "rule_index": t["rule_index"],
            "thresh_precision": round(t["precision"], 3) if t["precision"] else None,
            "thresh_recall": round(t["recall"], 3) if t["recall"] else None,
            "percent_kept": round(t["percent_kept"] * 100, 1) if t["percent_kept"] else None,
            "min_threshold": round(t["min_threshold"], 3) if t["min_threshold"] is not None else None,
            "max_threshold": round(t["max_threshold"], 3) if t["max_threshold"] is not None else None,
        }

    # Parse version_id to (task_type, rule_index) as fallback when no threshold data
    import re
    _VID_PREFIX = {
        "A": "asset_type", "CF": "color_fill_type", "CL": "clip_art_type",
        "MU": "multi_color_type", "MO": "mono_color_type", "LW": "line_width_type",
        "DR": "dark_ratio_score", "RO": "roughness_score", "PC": "select_primary_colors",
    }
    def _parse_version_id(vid):
        m = re.match(r"^([A-Z]+)(\d+)_", vid)
        if not m:
            return None
        prefix, ri = m.group(1), int(m.group(2))
        tt = _VID_PREFIX.get(prefix)
        return (tt, ri) if tt else None

    # Build prod info per feature
    prod_by_feature = {}
    prod_dev_ids_valid = set()
    for pr in prod_rows:
        vid = pr["version_id"]
        thresh = thresh_version_map.get(vid)
        if thresh:
            feat_key = (thresh["task_type"], thresh["rule_index"])
        else:
            feat_key = _parse_version_id(vid)
        if not feat_key:
            continue
        prod_by_feature[feat_key] = {
            "version_id": vid, "dev_id": pr["dev_id"],
            "threshold": thresh, "feat_key": feat_key,
        }
        if pr["dev_id"] is not None:
            prod_dev_ids_valid.add((pr["dev_id"], feat_key))

    all_results = list(
        model_results_table.objects.using(_db)
        .order_by("-created_at")
        .values()
    )

    def _float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    for row in all_results:
        for f in ("val_recall", "val_precision", "val_auc", "val_loss", "val_mae", "learning_rate"):
            row[f] = round(_float(row.get(f)), 3)
        row["is_regressor"] = row.get("outcome_type") == "regressor"
        row["title"] = rule_titles.get((row["task_type"], row["rule_index"]), "")
        if row["is_regressor"]:
            row["score"] = round(-row["val_mae"], 3) if row["val_mae"] else 0
        else:
            row["score"] = round((row["val_precision"] + row["val_recall"]) - abs(row["val_precision"] - row["val_recall"]), 3)
        row["total_samples"] = (row.get("train_samples") or 0) + (row.get("val_samples") or 0)
        row["date"] = row["created_at"].strftime("%b %d, %Y") if row["created_at"] else ""
        feat_key = (row["task_type"], row["rule_index"])
        # Only mark as prod if dev_id matches AND the feature matches
        row["is_prod"] = (row["id"], feat_key) in prod_dev_ids_valid
        row["threshold"] = prod_by_feature[feat_key]["threshold"] if row["is_prod"] and feat_key in prod_by_feature else None

    features = {}
    for row in all_results:
        key = (row["task_type"], row["rule_index"])
        if key not in features:
            features[key] = {
                "task_type": row["task_type"],
                "rule_index": row["rule_index"],
                "title": row["title"],
                "prod_model": None,
                "models": [],
            }
        if row["is_prod"]:
            features[key]["prod_model"] = row
        features[key]["models"].append(row)

    for feat in features.values():
        feat["models"].sort(key=lambda m: m["score"], reverse=True)
        feat["models"] = feat["models"][:20]
        for i, m in enumerate(feat["models"]):
            m["rank"] = i + 1
        fkey = (feat["task_type"], feat["rule_index"])
        prod_info = prod_by_feature.get(fkey)
        if prod_info:
            feat["has_prod"] = True
            feat["prod_version"] = prod_info["version_id"]
            feat["prod_threshold"] = prod_info.get("threshold")
            # Sidebar dot uses pre-thresholding numbers from the actual model_results row
            p = feat["prod_model"]
            if p:
                is_reg = p.get("is_regressor")
                if is_reg:
                    feat["perf"] = "yes" if p["val_mae"] <= 0.1 else ("close" if p["val_mae"] <= 0.2 else "no")
                else:
                    feat["perf"] = "yes" if p["val_recall"] > 0.9 and p["val_precision"] > 0.9 else (
                        "close" if p["val_recall"] > 0.88 and p["val_precision"] > 0.88 else "no"
                    )
            else:
                feat["perf"] = "yes"
        else:
            feat["perf"] = "none"
            feat["has_prod"] = False

    task_types = sorted(set(k[0] for k in features))
    grouped = []
    for tt in task_types:
        items = sorted(
            [f for f in features.values() if f["task_type"] == tt],
            key=lambda f: f["rule_index"],
        )
        grouped.append({"task_type": tt, "features": items})

    features_json = {}
    for f in features.values():
        key = f"{f['task_type']}_{f['rule_index']}"
        is_reg = any(m.get("is_regressor") for m in f["models"])
        features_json[key] = {
            "models": f["models"],
            "has_prod": f.get("has_prod", False),
            "prod_version": f.get("prod_version", ""),
            "prod_threshold": f.get("prod_threshold"),
            "is_regressor": is_reg,
        }

    data = {
        "grouped_features": grouped,
        "features_json": json.dumps(features_json, default=str),
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
    labeler_id = request.GET.get("labeler_id", request.user.username)

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
        "task_type": task_type,
        "rule_index": rule_index,
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
                        "labeler_id", request.user.username
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
    UserProfile,
)


# ---------------------------------------------------------------------------
# Labeler: earnings view
# ---------------------------------------------------------------------------

@labeler_required
def labeler_earnings(request):
    from labeling_api.models import labelling_rules as LR

    assignments = BatchAssignment.objects.filter(user=request.user).order_by("-deadline")

    rule_titles = {}
    for r in LR.objects.exclude(task_type="color_type").values("task_type", "rule_index", "title"):
        rule_titles[(r["task_type"], r["rule_index"])] = r["title"]

    def annotate(a):
        a.feature_name = rule_titles.get((a.task_type, a.rule_index), "")
        return a

    completed = [annotate(a) for a in assignments if a.completed_at]
    pending = [annotate(a) for a in assignments if not a.completed_at]

    completed_total = sum(a.payment_amount for a in completed)
    pending_total = sum(a.payment_amount for a in pending)

    return render(request, "labeler_earnings.html", {
        "completed_assignments": completed,
        "pending_assignments": pending,
        "completed_total": completed_total,
        "pending_total": pending_total,
    })


# ---------------------------------------------------------------------------
# Labeler: view my corrections / errors
# ---------------------------------------------------------------------------

@login_required
def labeler_errors(request):
    from labeling_api.models import (
        labelling_rules as LR, label_data_selected_assets_new,
        modified_prompt_table, prompt_responses,
    )

    username = request.user.username

    # Get this labeler's original prompt_responses
    orig_responses = list(prompt_responses.objects.filter(
        labeler_id=username,
    ).values("asset_id", "task_type", "rule_index", "prompt_response"))

    if not orig_responses:
        return render(request, "labeler_errors.html", {"items": [], "total": 0})

    # Build lookup of asset keys this labeler touched
    asset_ids = list(set(r["asset_id"] for r in orig_responses))

    # Get all modified_prompt_responses for those assets (one per asset)
    mod_map = {}
    for m in modified_prompt_table.objects.filter(
        asset_id__in=asset_ids,
    ).values("asset_id", "task_type", "rule_index",
             "modified_prompt_response", "date_time_created"):
        key = (m["asset_id"], m["task_type"], m["rule_index"])
        mod_map[key] = {
            "correct": "yes" if m["modified_prompt_response"] == "1" else "no",
            "date": m["date_time_created"],
        }

    if not mod_map:
        return render(request, "labeler_errors.html", {"items": [], "total": 0})

    rule_titles = {}
    for r in LR.objects.exclude(task_type="color_type").values("task_type", "rule_index", "title"):
        rule_titles[(r["task_type"], r["rule_index"])] = r["title"]

    image_map = {}
    for row in label_data_selected_assets_new.objects.filter(
        asset_id__in=asset_ids
    ).values("asset_id", "image_link").distinct():
        if row["asset_id"] not in image_map:
            image_map[row["asset_id"]] = row["image_link"]

    items = []
    for r in orig_responses:
        key = (r["asset_id"], r["task_type"], r["rule_index"])
        mod = mod_map.get(key)
        if not mod:
            continue
        if r["prompt_response"] != mod["correct"]:
            items.append({
                "asset_id": r["asset_id"],
                "feature": rule_titles.get((r["task_type"], r["rule_index"]),
                                           f"{r['task_type']} / {r['rule_index']}"),
                "original": r["prompt_response"],
                "correct": mod["correct"],
                "image_link": image_map.get(r["asset_id"], ""),
                "date": mod["date"],
            })

    items.sort(key=lambda x: x["date"], reverse=True)

    return render(request, "labeler_errors.html", {
        "items": items,
        "total": len(items),
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


@admin_required_ajax
def admin_create_labeler(request):
    """AJAX: create a new labeler User account."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.contrib.auth.models import User

    data = json.loads(request.body)
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return JsonResponse({"error": "Username and password are required."}, status=400)
    if len(password) < 8:
        return JsonResponse({"error": "Password must be at least 8 characters."}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": f"Username '{username}' already exists."}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    return JsonResponse({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
    })


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
        .select_related("user")
        .values("id", "user_id", "user__username", "task_type", "rule_index",
                "batch_id", "large_sub_batch", "payment_amount", "deadline",
                "completed_at", "is_training")
    )

    return render(request, "admin_bulk_assign.html", {
        "labeler_users_json": json.dumps(labeler_users, default=str),
        "sub_batches_json": json.dumps(all_sub_batches, default=str),
        "rules_json": json.dumps(all_rules, default=str),
        "existing_json": json.dumps(existing, default=str),
        "default_pay": settings.LABELER_PAY_PER_BATCH,
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
    bonus = data.get("bonus_amount", "0")
    deadline_str = data.get("deadline")

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
                    "bonus_amount": bonus,
                    "deadline": deadline_dt,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

    return JsonResponse({"created": created, "skipped": skipped})


@admin_required_ajax
def admin_remove_assignments(request):
    """AJAX: delete BatchAssignment rows by ID."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    data = json.loads(request.body)
    ids = data.get("ids", [])
    if not ids:
        return JsonResponse({"error": "No assignment IDs provided"}, status=400)
    deleted, _ = BatchAssignment.objects.filter(id__in=ids).delete()
    return JsonResponse({"deleted": deleted})


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
    """AJAX: return summary, training results, and work batch stats for a labeler."""
    from django.contrib.auth.models import User
    from labeling_api.models import prompt_responses, labelling_rules as LR
    from .models import TrainingResult

    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id required"}, status=400)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "user not found"}, status=404)

    rule_titles = {}
    for r in LR.objects.exclude(task_type="color_type").values("task_type", "rule_index", "title"):
        rule_titles[(r["task_type"], r["rule_index"])] = r["title"]

    # --- Training results ---
    training_assignments = {
        (a.task_type, a.rule_index): a.id
        for a in BatchAssignment.objects.filter(user=user, is_training=True)
    }
    training_rows = []
    for tr in TrainingResult.objects.filter(user=user).order_by("-completed_at"):
        mins = round(tr.time_seconds / 60, 1)
        assignment_id = training_assignments.get((tr.task_type, tr.rule_index))
        has_detail = tr.label_responses.exists() if assignment_id else False
        training_rows.append({
            "task_type": tr.task_type,
            "rule_index": tr.rule_index,
            "feature": rule_titles.get((tr.task_type, tr.rule_index), ""),
            "correct": tr.correct,
            "total": tr.total,
            "accuracy_pct": round(tr.correct / tr.total * 100, 1) if tr.total > 0 else 0,
            "time_min": mins,
            "per_image_sec": round(tr.time_seconds / tr.total, 1) if tr.total > 0 else 0,
            "date": tr.completed_at.strftime("%b %d, %Y %I:%M %p") if tr.completed_at else "",
            "assignment_id": assignment_id,
            "training_result_id": tr.id,
            "has_detail": has_detail,
        })

    # Training summary
    tr_qs = TrainingResult.objects.filter(user=user)
    tr_total_imgs = sum(t.total for t in tr_qs)
    tr_total_correct = sum(t.correct for t in tr_qs)
    tr_total_secs = sum(t.time_seconds for t in tr_qs)
    tr_avg_accuracy = round(tr_total_correct / tr_total_imgs * 100, 1) if tr_total_imgs > 0 else None
    tr_count = tr_qs.count()

    # --- Work batch stats ---
    from labeling_api.models import label_data_selected_assets_new, label_issues_table
    work_assignments = BatchAssignment.objects.filter(user=user, is_training=False)
    work_rows = []
    total_work_labels = 0
    for a in work_assignments.order_by("-assigned_at"):
        # Backfill: if completed_at is not set, check actual progress
        if a.completed_at is None:
            batch_asset_ids = set(
                label_data_selected_assets_new.objects.filter(
                    task_type=a.task_type, rule_index=a.rule_index,
                    batch_id=a.batch_id, large_sub_batch=a.large_sub_batch,
                ).values_list("asset_id", flat=True)
            )
            if batch_asset_ids:
                labeled_ids = set(
                    prompt_responses.objects.filter(
                        task_type=a.task_type, rule_index=a.rule_index,
                        labeler_id=user.username, asset_id__in=batch_asset_ids,
                    ).values_list("asset_id", flat=True).distinct()
                )
                flagged_ids = set(
                    label_issues_table.objects.filter(
                        asset_id__in=batch_asset_ids,
                    ).values_list("asset_id", flat=True)
                )
                if batch_asset_ids.issubset(labeled_ids | flagged_ids):
                    from django.utils import timezone as tz
                    a.completed_at = tz.now()
                    a.save(update_fields=["completed_at"])

        sessions = LabelingSession.objects.filter(batch_assignment=a, ended_at__isnull=False)
        labels = sum(s.labels_completed for s in sessions)
        hours = sum((s.duration_hours or 0) for s in sessions)
        total_work_labels += labels
        work_rows.append({
            "task_type": a.task_type,
            "rule_index": a.rule_index,
            "feature": rule_titles.get((a.task_type, a.rule_index), ""),
            "batch_id": a.batch_id,
            "sub_batch": a.large_sub_batch,
            "labels": labels,
            "hours": round(hours, 2),
            "throughput": round(labels / hours, 1) if hours > 0 else None,
            "deadline": a.deadline.strftime("%b %d") if a.deadline else "",
            "deadline_iso": a.deadline.strftime("%Y-%m-%d") if a.deadline else "",
            "assignment_id": a.id,
            "completed": a.completed_at is not None,
            "on_time": a.completed_at <= a.deadline if a.completed_at and a.deadline else None,
        })

    # Work summary
    all_sessions = LabelingSession.objects.filter(user=user, ended_at__isnull=False,
                                                   batch_assignment__is_training=False)
    w_total_labels = sum(s.labels_completed for s in all_sessions)
    w_total_hours = sum((s.duration_hours or 0) for s in all_sessions)
    w_throughput = round(w_total_labels / w_total_hours, 1) if w_total_hours > 0 else None
    w_completed = work_assignments.filter(completed_at__isnull=False)
    w_completed_count = w_completed.count()
    w_on_time = w_completed.filter(completed_at__lte=F("deadline")).count()
    w_on_time_pct = round(w_on_time / w_completed_count * 100, 1) if w_completed_count > 0 else None

    return JsonResponse({
        "username": user.username,
        "summary": {
            "training_accuracy": tr_avg_accuracy,
            "training_sessions": tr_count,
            "training_total_imgs": tr_total_imgs,
            "work_labels": w_total_labels,
            "work_hours": round(w_total_hours, 1),
            "work_throughput": w_throughput,
            "work_on_time_pct": w_on_time_pct,
            "work_completed": w_completed_count,
            "work_assignments": work_assignments.count(),
        },
        "training": training_rows,
        "work": work_rows,
    })


# ---------------------------------------------------------------------------
# Admin: labeler label review
# ---------------------------------------------------------------------------

@admin_required_ajax
def admin_labeler_labels(request):
    """Page: pick a labeler, browse their assignments, see every label they chose."""
    from django.contrib.auth.models import User
    labelers = list(
        User.objects.filter(is_staff=True, is_superuser=False)
        .order_by("username")
        .values("id", "username")
    )
    return render(request, "admin_labeler_labels.html", {
        "labelers_json": json.dumps(labelers, default=str),
    })


@admin_required_ajax
def admin_labeler_labels_assignments(request):
    """AJAX: return all assignments for a user."""
    from django.contrib.auth.models import User
    from labeling_api.models import labelling_rules as LR

    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id required"}, status=400)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    rule_titles = {
        (r["task_type"], r["rule_index"]): r["title"]
        for r in LR.objects.values("task_type", "rule_index", "title")
    }

    rows = []
    for a in BatchAssignment.objects.filter(user=user).order_by("-assigned_at"):
        # For training, completed_at is set by complete_training view.
        # For work batches, completed_at may never be auto-set — use LabelingSession.
        if a.is_training:
            completed = a.completed_at is not None
        else:
            has_session = LabelingSession.objects.filter(
                batch_assignment=a, ended_at__isnull=False
            ).exists()
            completed = a.completed_at is not None or has_session

        rows.append({
            "id": a.id,
            "task_type": a.task_type,
            "rule_index": a.rule_index,
            "feature": rule_titles.get((a.task_type, a.rule_index), ""),
            "batch_id": a.batch_id,
            "sub_batch": a.large_sub_batch,
            "is_training": a.is_training,
            "completed": completed,
            "assigned_at": a.assigned_at.strftime("%b %d, %Y") if a.assigned_at else "",
        })
    return JsonResponse({"username": user.username, "assignments": rows})


@admin_required_ajax
def admin_labeler_labels_detail(request):
    """AJAX: return every label the labeler chose for one assignment."""
    from labeling_api.models import prompt_responses, label_data_selected_assets_new
    from .models import TrainingBatchAsset, TrainingLabelResponse, TrainingResult

    assignment_id = request.GET.get("assignment_id")
    training_result_id = request.GET.get("training_result_id")
    if not assignment_id:
        return JsonResponse({"error": "assignment_id required"}, status=400)
    try:
        a = BatchAssignment.objects.select_related("user").get(pk=assignment_id)
    except BatchAssignment.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    labeler_id = a.user.username
    legacy_score = None

    if a.is_training:
        assets = {
            ta.asset_id: {"image_link": ta.image_link, "correct_label": ta.correct_label}
            for ta in TrainingBatchAsset.objects.filter(assignment=a)
        }
        responses = {}
        if training_result_id:
            for r in TrainingLabelResponse.objects.filter(
                assignment=a, training_result_id=training_result_id,
            ):
                responses[r.asset_id] = r.user_answer
            if not responses:
                tr = TrainingResult.objects.filter(pk=training_result_id).first()
                if tr:
                    legacy_score = {"correct": tr.correct, "total": tr.total}
        else:
            for r in TrainingLabelResponse.objects.filter(assignment=a).order_by(
                "-training_result__completed_at", "asset_id",
            ):
                if r.asset_id not in responses:
                    responses[r.asset_id] = r.user_answer
    else:
        assets_qs = label_data_selected_assets_new.objects.filter(
            batch_id=a.batch_id,
            large_sub_batch=a.large_sub_batch,
            task_type=a.task_type,
            rule_index=a.rule_index,
        ).values("asset_id", "image_link")
        if not assets_qs.exists():
            assets_qs = label_data_selected_assets_new.objects.filter(
                batch_id=a.batch_id,
                large_sub_batch=a.large_sub_batch,
            ).values("asset_id", "image_link")
        assets = {row["asset_id"]: {"image_link": row["image_link"]} for row in assets_qs}

        responses = {}
        if assets:
            for pr in prompt_responses.objects.filter(
                asset_id__in=list(assets.keys()),
                task_type=a.task_type,
            ).order_by("asset_id", "datetime_created"):
                if pr.labeler_id.strip().lower() == labeler_id.strip().lower():
                    if str(pr.rule_index) == str(a.rule_index):
                        responses[pr.asset_id] = pr.prompt_response

    rows = []
    for asset_id, info in assets.items():
        answer = responses.get(asset_id)
        if answer == "none":
            answer = None
        row = {
            "asset_id": asset_id,
            "image_link": info["image_link"],
            "answer": answer,
        }
        if a.is_training:
            correct_label = info["correct_label"]
            correct_str = "yes" if correct_label == 1 else "no"
            row["correct"] = correct_str
            row["right"] = (answer == correct_str) if answer else None
        rows.append(row)

    return JsonResponse({
        "assignment_id": a.id,
        "is_training": a.is_training,
        "task_type": a.task_type,
        "rule_index": a.rule_index,
        "labels": rows,
        "legacy_score": legacy_score,
    })


# ---------------------------------------------------------------------------
# Admin: override a labeler's answer for a single asset
# ---------------------------------------------------------------------------

@admin_required_ajax
def admin_override_label(request):
    """AJAX: set or clear a labeler's prompt_response for a single asset."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    import json as _json
    from labeling_api.models import prompt_responses

    body = _json.loads(request.body)
    assignment_id = body.get("assignment_id")
    asset_id = body.get("asset_id")
    new_answer = body.get("answer")  # "yes", "no", or None/empty to clear

    if not assignment_id or not asset_id:
        return JsonResponse({"error": "assignment_id and asset_id required"}, status=400)

    try:
        a = BatchAssignment.objects.select_related("user").get(pk=assignment_id)
    except BatchAssignment.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    labeler_id = a.user.username

    if new_answer:
        # Update existing row if present, else insert
        qs = prompt_responses.objects.filter(
            asset_id=asset_id,
            task_type=a.task_type,
            rule_index=a.rule_index,
            labeler_id=labeler_id,
        )
        if qs.exists():
            qs.update(prompt_response=new_answer)
        else:
            from django.utils import timezone as tz
            prompt_responses(
                datetime_created=tz.now(),
                asset_id=asset_id,
                labeler_source="admin_override",
                labeler_id=labeler_id,
                labeler_count=1,
                task_type=a.task_type,
                rule_index=a.rule_index,
                prompt_response=new_answer,
            ).save()
    else:
        # Clear — delete the row
        prompt_responses.objects.filter(
            asset_id=asset_id,
            task_type=a.task_type,
            rule_index=a.rule_index,
            labeler_id=labeler_id,
        ).delete()

    return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Admin: label comparison tool
# ---------------------------------------------------------------------------

@admin_required
def admin_label_comparison(request):
    """Render the label comparison page."""
    from labeling_api.models import label_data_selected_assets_new, labelling_rules as LR

    features = list(
        LR.objects.exclude(task_type="color_type")
        .values("task_type", "rule_index", "title")
        .order_by("task_type", "rule_index")
    )
    sub_batches = list(
        label_data_selected_assets_new.objects
        .values("task_type", "rule_index", "batch_id", "large_sub_batch")
        .distinct()
        .order_by("task_type", "rule_index", "batch_id", "large_sub_batch")
    )
    return render(request, "admin_label_comparison.html", {
        "features_json": json.dumps(features, default=str),
        "sub_batches_json": json.dumps(sub_batches, default=str),
    })


@admin_required_ajax
def admin_label_comparison_data(request):
    """AJAX: return per-asset labels from all labelers for a given sub-batch."""
    from labeling_api.models import (
        prompt_responses, label_data_selected_assets_new, label_issues_table,
    )

    task_type = request.GET.get("task_type", "")
    rule_index = request.GET.get("rule_index", "")
    batch_id = request.GET.get("batch_id", "")
    large_sub_batch = request.GET.get("large_sub_batch", "")

    if not all([task_type, rule_index, batch_id, large_sub_batch]):
        return JsonResponse({"error": "all params required"}, status=400)

    rule_index = int(rule_index)
    batch_id = int(batch_id)
    large_sub_batch = int(large_sub_batch)

    assets = {
        row["asset_id"]: row["image_link"]
        for row in label_data_selected_assets_new.objects.filter(
            task_type=task_type, rule_index=rule_index,
            batch_id=batch_id, large_sub_batch=large_sub_batch,
        ).values("asset_id", "image_link")
    }

    flagged_ids = set(
        label_issues_table.objects.filter(
            asset_id__in=list(assets.keys()),
        ).values_list("asset_id", flat=True)
    )

    responses = (
        prompt_responses.objects.filter(
            task_type=task_type,
            rule_index=rule_index,
            asset_id__in=list(assets.keys()),
        )
        .order_by("asset_id", "labeler_id", "-datetime_created")
        .values("asset_id", "labeler_id", "prompt_response", "labeler_source")
    )

    # Group by asset — deduplicate per labeler (keep latest)
    per_asset = {}
    all_labelers = set()
    for r in responses:
        aid = r["asset_id"]
        lid = r["labeler_id"]
        if aid not in per_asset:
            per_asset[aid] = {}
        if lid not in per_asset[aid]:
            per_asset[aid][lid] = {
                "response": r["prompt_response"],
                "source": r["labeler_source"],
            }
        all_labelers.add(lid)

    all_labelers.discard("admin_override")
    labelers_sorted = sorted(all_labelers)

    # Load modified (overridden) responses — one per asset
    from labeling_api.models import modified_prompt_table
    mod_qs = modified_prompt_table.objects.filter(
        task_type=task_type, rule_index=rule_index,
        asset_id__in=list(assets.keys()),
    ).values("asset_id", "modified_prompt_response")

    # Map asset_id -> correct answer in yes/no form
    mod_map = {}
    for m in mod_qs:
        val = m["modified_prompt_response"]
        mod_map[m["asset_id"]] = "yes" if val == "1" else "no"

    rows = []
    for asset_id, image_link in sorted(assets.items()):
        labels = per_asset.get(asset_id, {})
        responses_list = {
            lid: labels[lid]["response"] if lid in labels else None
            for lid in labelers_sorted
        }
        unique_answers = set(v for v in responses_list.values() if v)
        correct_answer = mod_map.get(asset_id)

        # Build corrections dict: labelers whose original differs from the correct answer
        corrections = {}
        if correct_answer:
            for lid in labelers_sorted:
                orig = responses_list.get(lid)
                if orig and orig != correct_answer:
                    corrections[lid] = {"original": orig, "correct": correct_answer}

        rows.append({
            "asset_id": asset_id,
            "image_link": image_link,
            "labels": responses_list,
            "flagged": asset_id in flagged_ids,
            "disagreement": len(unique_answers) > 1,
            "num_labeled": sum(1 for v in responses_list.values() if v),
            "corrected": correct_answer is not None,
            "correct_answer": correct_answer,
            "corrections": corrections,
        })

    return JsonResponse({
        "labelers": labelers_sorted,
        "total": len(rows),
        "assets": rows,
        "task_type": task_type,
        "rule_index": rule_index,
    })


@admin_required_ajax
def admin_comparison_override(request):
    """AJAX: set the correct answer for an asset by writing one row to
    modified_prompt_responses (1 or 0). Original prompt_responses stay untouched."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    import json as _json
    from labeling_api.models import prompt_responses, modified_prompt_table
    from django.utils import timezone as tz

    body = _json.loads(request.body)
    task_type = body.get("task_type", "")
    rule_index = body.get("rule_index")
    asset_id = body.get("asset_id")
    answer_yesno = body.get("answer")  # "yes" or "no" from frontend

    if not task_type or rule_index is None or not asset_id or not answer_yesno:
        return JsonResponse({"error": "task_type, rule_index, asset_id, answer required"}, status=400)

    rule_index = int(rule_index)
    mod_val = "1" if answer_yesno == "yes" else "0"
    admin_id = request.user.username

    # Upsert a single row for this asset
    existing = modified_prompt_table.objects.filter(
        asset_id=asset_id, task_type=task_type, rule_index=rule_index,
    )
    if existing.exists():
        existing.update(
            modified_prompt_response=mod_val,
            labeler_id=admin_id,
            date_time_created=tz.now(),
        )
    else:
        modified_prompt_table(
            date_time_created=tz.now(),
            asset_id=asset_id,
            labeler_source="admin_comparison",
            labeler_id=admin_id,
            task_type=task_type,
            rule_index=rule_index,
            modified_prompt_response=mod_val,
        ).save()

    # Determine which labelers had the wrong answer
    responses = list(prompt_responses.objects.filter(
        asset_id=asset_id, task_type=task_type, rule_index=rule_index,
    ).exclude(labeler_id="admin_override").values("labeler_id", "prompt_response"))

    wrong_labelers = [r["labeler_id"] for r in responses if r["prompt_response"] != answer_yesno]

    return JsonResponse({"status": "ok", "corrected": wrong_labelers})


# ---------------------------------------------------------------------------
# Admin: update batch assignment deadline
# ---------------------------------------------------------------------------

@admin_required_ajax
def admin_update_deadline(request):
    """AJAX: update the deadline on a BatchAssignment."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    import json as _json
    body = _json.loads(request.body)
    assignment_id = body.get("assignment_id")
    new_deadline = body.get("deadline")
    if not assignment_id or not new_deadline:
        return JsonResponse({"error": "assignment_id and deadline required"}, status=400)

    from django.utils.dateparse import parse_date
    d = parse_date(new_deadline)
    if not d:
        return JsonResponse({"error": "invalid date format"}, status=400)

    from datetime import datetime, time
    from django.utils import timezone as tz
    deadline_dt = tz.make_aware(datetime.combine(d, time(23, 59, 59)))

    try:
        a = BatchAssignment.objects.get(pk=assignment_id)
    except BatchAssignment.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    a.deadline = deadline_dt
    a.save(update_fields=["deadline"])
    return JsonResponse({"status": "ok", "deadline": a.deadline.strftime("%b %d")})


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

    from labeling_api.models import label_issues_table

    # Assets with at least 1 response for this task_type (any labeler)
    done_ids = set(
        prompt_responses.objects
        .filter(task_type=task_type)
        .values_list("asset_id", flat=True)
        .distinct()
    )
    # Flagged assets also count as done
    flagged_ids = set(
        label_issues_table.objects.values_list("asset_id", flat=True)
    )
    done_ids = done_ids | flagged_ids

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


# ===========================================================================
# Rule Guide — Reference pages
# ===========================================================================

@login_required
def rule_guide(request):
    from .models import RuleGuide
    guides = RuleGuide.objects.prefetch_related("directives", "reference_images").all()
    categories = []
    seen = set()
    for g in guides:
        if g.category not in seen:
            seen.add(g.category)
            categories.append(g.category)

    selected = request.GET.get("category", categories[0] if categories else "")
    filtered = [g for g in guides if g.category == selected]

    return render(request, "rule_guide.html", {
        "categories": categories,
        "selected_category": selected,
        "guides": filtered,
        "user_is_admin": is_admin(request),
    })


@login_required
def rule_guide_api(request):
    """AJAX endpoints for admin CRUD on rule guides, directives, and reference images."""
    from .models import RuleGuide, RuleDirective, RuleReferenceImage

    if not request.user.is_superuser:
        return JsonResponse({"error": "forbidden"}, status=403)

    action = request.POST.get("action") or request.GET.get("action")

    if action == "save_guide":
        guide_id = request.POST.get("guide_id")
        if guide_id:
            guide = RuleGuide.objects.get(id=guide_id)
            guide.title = request.POST.get("title", guide.title)
            guide.description = request.POST.get("description", guide.description)
            guide.category = request.POST.get("category", guide.category)
            guide.save()
        else:
            guide = RuleGuide.objects.create(
                task_type=request.POST["task_type"],
                rule_index=request.POST["rule_index"],
                title=request.POST["title"],
                category=request.POST.get("category", ""),
                description=request.POST.get("description", ""),
            )
        return JsonResponse({"ok": True, "id": guide.id})

    elif action == "delete_guide":
        RuleGuide.objects.filter(id=request.POST["guide_id"]).delete()
        return JsonResponse({"ok": True})

    elif action == "save_directive":
        d_id = request.POST.get("directive_id")
        if d_id:
            d = RuleDirective.objects.get(id=d_id)
            d.text = request.POST.get("text", d.text)
            if request.POST.get("number"):
                d.number = int(request.POST["number"])
            d.save()
        else:
            guide = RuleGuide.objects.get(id=request.POST["guide_id"])
            max_num = guide.directives.order_by("-number").values_list("number", flat=True).first() or 0
            d = RuleDirective.objects.create(
                guide=guide,
                number=int(request.POST.get("number", max_num + 1)),
                text=request.POST["text"],
            )
        return JsonResponse({"ok": True, "id": d.id})

    elif action == "delete_directive":
        RuleDirective.objects.filter(id=request.POST["directive_id"]).delete()
        return JsonResponse({"ok": True})

    elif action == "save_image":
        img_id = request.POST.get("image_id")
        if img_id:
            img = RuleReferenceImage.objects.get(id=img_id)
            img.image_url = request.POST.get("image_url", img.image_url)
            img.caption = request.POST.get("caption", img.caption)
            img.label = request.POST.get("label", img.label)
            img.save()
        else:
            guide = RuleGuide.objects.get(id=request.POST["guide_id"])
            directive = None
            if request.POST.get("directive_id"):
                directive = RuleDirective.objects.get(id=request.POST["directive_id"])
            img = RuleReferenceImage.objects.create(
                guide=guide,
                directive=directive,
                image_url=request.POST["image_url"],
                caption=request.POST.get("caption", ""),
                label=request.POST.get("label", ""),
            )
        return JsonResponse({"ok": True, "id": img.id})

    elif action == "delete_image":
        RuleReferenceImage.objects.filter(id=request.POST["image_id"]).delete()
        return JsonResponse({"ok": True})

    return JsonResponse({"error": "unknown action"}, status=400)


@csrf_exempt
@login_required
def complete_training(request):
    """AJAX: mark a training BatchAssignment as completed and record results."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from .models import BatchAssignment, TrainingResult, TrainingLabelResponse
    task_type = request.POST.get("task_type")
    rule_index = int(request.POST.get("rule_index"))
    correct = int(request.POST.get("correct", 0))
    total = int(request.POST.get("total", 0))
    time_seconds = int(request.POST.get("time_seconds", 0))
    answers_raw = request.POST.get("answers", "[]")

    try:
        answers = json.loads(answers_raw)
    except (json.JSONDecodeError, TypeError):
        answers = []

    from django.utils import timezone as tz
    assignment = BatchAssignment.objects.filter(
        user=request.user,
        task_type=task_type,
        rule_index=rule_index,
        is_training=True,
    ).first()

    # Mark as completed (first time only)
    if assignment:
        BatchAssignment.objects.filter(
            pk=assignment.pk,
            completed_at__isnull=True,
        ).update(completed_at=tz.now())

    training_result = TrainingResult.objects.create(
        user=request.user,
        task_type=task_type,
        rule_index=rule_index,
        total=total,
        correct=correct,
        time_seconds=max(time_seconds, 1),
    )

    if assignment and answers:
        TrainingLabelResponse.objects.bulk_create([
            TrainingLabelResponse(
                assignment=assignment,
                training_result=training_result,
                asset_id=int(item["asset_id"]),
                user_answer=item.get("answer") or "none",
                is_correct=bool(item.get("is_correct")),
            )
            for item in answers
            if item.get("asset_id") is not None
        ])

    return JsonResponse({"ok": True})


@admin_required
def admin_manage_training(request):
    """Admin page to manage training sets per user."""
    from django.contrib.auth.models import User
    from .models import BatchAssignment, TrainingBatchAsset

    labeler_users = list(
        User.objects.filter(is_superuser=False, is_staff=True)
        .order_by("username")
        .values_list("username", flat=True)
    )

    from labeling_api.models import labelling_rules as LR
    rules = list(
        LR.objects.filter(task_type__in=[
            "asset_type", "clip_art_type", "color_fill_type",
            "mono_color_type", "multi_color_type",
        ])
        .values("task_type", "rule_index", "title")
        .order_by("task_type", "rule_index")
    )

    training_assignments = list(
        BatchAssignment.objects.filter(is_training=True)
        .select_related("user")
        .values(
            "id", "user__username", "task_type", "rule_index",
            "completed_at", "payment_amount",
        )
    )

    training_asset_counts = {}
    for ta in TrainingBatchAsset.objects.values("assignment_id").annotate(cnt=Count("id")):
        training_asset_counts[ta["assignment_id"]] = ta["cnt"]

    for a in training_assignments:
        a["asset_count"] = training_asset_counts.get(a["id"], 0)

    return render(request, "admin_manage_training.html", {
        "labeler_users_json": json.dumps(labeler_users),
        "rules_json": json.dumps(rules, default=str),
        "training_assignments_json": json.dumps(training_assignments, default=str),
    })


@admin_required_ajax
def admin_training_create(request):
    """AJAX: create a training batch assignment for a user."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from django.contrib.auth.models import User
    from .models import BatchAssignment, TrainingBatchAsset
    from labeling_api.models import assets_w_rule_labels, label_data_selected_assets_new

    data = json.loads(request.body)
    username = data.get("username")
    task_type = data.get("task_type")
    rule_index = int(data.get("rule_index", 0))
    asset_count = int(data.get("asset_count", 150))

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"error": f"User '{username}' not found"}, status=404)

    from django.utils import timezone
    from datetime import timedelta
    deadline = timezone.now() + timedelta(days=30)

    assignment, created = BatchAssignment.objects.get_or_create(
        user=user,
        task_type=task_type,
        rule_index=rule_index,
        batch_id=0,
        large_sub_batch=0,
        defaults={
            "payment_amount": settings.LABELER_PAY_PER_BATCH,
            "deadline": deadline,
            "is_training": True,
        },
    )

    reconciled = list(
        assets_w_rule_labels.objects
        .filter(task_type=task_type, rule_index=rule_index)
        .values_list("asset_id", "label")
    )

    if not reconciled:
        return JsonResponse({"error": "No reconciled assets found for this rule"}, status=400)

    sampled = random.sample(reconciled, min(asset_count, len(reconciled)))
    sampled_ids = [a[0] for a in sampled]
    label_map = {a[0]: a[1] for a in sampled}

    image_links = dict(
        label_data_selected_assets_new.objects
        .filter(asset_id__in=sampled_ids)
        .values_list("asset_id", "image_link")
    )

    assets_with_links = [
        (aid, image_links[aid], label_map[aid])
        for aid in sampled_ids if aid in image_links
    ]

    if not assets_with_links:
        return JsonResponse({"error": "No images found for sampled assets"}, status=400)

    new_assets = TrainingBatchAsset.objects.bulk_create(
        [
            TrainingBatchAsset(
                assignment=assignment,
                asset_id=aid,
                image_link=link,
                correct_label=label,
            )
            for aid, link, label in assets_with_links
        ],
        ignore_conflicts=True,
    )

    total_count = TrainingBatchAsset.objects.filter(assignment=assignment).count()

    return JsonResponse({
        "ok": True,
        "assignment_id": assignment.id,
        "username": username,
        "task_type": task_type,
        "rule_index": rule_index,
        "assets_added": len(assets_with_links),
        "total_assets": total_count,
        "created": created,
    })


@admin_required_ajax
def admin_training_remove(request):
    """AJAX: remove a training batch assignment (and its assets)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from .models import BatchAssignment, TrainingBatchAsset

    data = json.loads(request.body)
    assignment_id = data.get("assignment_id")

    try:
        assignment = BatchAssignment.objects.get(pk=assignment_id, is_training=True)
    except BatchAssignment.DoesNotExist:
        return JsonResponse({"error": "Training assignment not found"}, status=404)

    asset_count = TrainingBatchAsset.objects.filter(assignment=assignment).count()
    TrainingBatchAsset.objects.filter(assignment=assignment).delete()
    assignment.delete()

    return JsonResponse({"ok": True, "deleted_assets": asset_count})


@admin_required_ajax
def admin_training_assets(request):
    """AJAX: get asset list for a training assignment."""
    from .models import BatchAssignment, TrainingBatchAsset

    assignment_id = request.GET.get("assignment_id")
    try:
        assignment = BatchAssignment.objects.get(pk=assignment_id, is_training=True)
    except BatchAssignment.DoesNotExist:
        return JsonResponse({"error": "Training assignment not found"}, status=404)

    assets = list(
        TrainingBatchAsset.objects.filter(assignment=assignment)
        .values("id", "asset_id", "image_link", "correct_label")
        .order_by("id")
    )
    return JsonResponse({"assets": assets, "assignment_id": assignment.id})


@admin_required_ajax
def admin_training_remove_asset(request):
    """AJAX: remove a single asset from a training set."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from .models import TrainingBatchAsset

    data = json.loads(request.body)
    asset_pk = data.get("asset_pk")

    try:
        asset = TrainingBatchAsset.objects.get(pk=asset_pk)
    except TrainingBatchAsset.DoesNotExist:
        return JsonResponse({"error": "Asset not found"}, status=404)

    asset.delete()
    return JsonResponse({"ok": True})


@login_required
def image_proxy(request):
    """Proxy an image URL so the browser can read its pixels (bypasses CORS).

    Some hosts (Cloudflare/WAF-protected CDNs, hot-link-protected buckets)
    return an HTML "request blocked" page when contacted with the default
    ``python-requests`` user agent. We mimic a real browser and reject any
    response whose content type isn't an image — otherwise the blocked HTML
    would be drawn into the measurement canvas as a corrupt/wrong image.
    """
    from urllib.parse import urlsplit

    url = request.GET.get("url", "")
    if not url:
        return HttpResponse("Missing url param", status=400)

    split = urlsplit(url)
    referer = f"{split.scheme}://{split.netloc}/" if split.scheme and split.netloc else ""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer

    try:
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
    except Exception as exc:
        return HttpResponse(f"Failed to fetch image: {exc}", status=502)

    content_type = (resp.headers.get("Content-Type") or "").lower()
    if not content_type.startswith("image/"):
        return HttpResponse(
            f"Upstream returned non-image content ({content_type or 'unknown'}); "
            "the image host likely blocked the server-side fetch.",
            status=502,
        )

    response = HttpResponse(resp.content, content_type=content_type)
    response["Cache-Control"] = "public, max-age=3600"
    return response
