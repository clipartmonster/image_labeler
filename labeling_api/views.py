from __future__ import annotations

import logging

from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)
from django.db.models import Max
from django.db.models import Count
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Subquery, OuterRef
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from rest_framework.decorators import api_view

import requests

from django.utils import timezone


from api.decorators import *

from .validation_functions import *

import pandas as pd
import numpy as np
from collections import defaultdict, OrderedDict
import json

from datetime import datetime
import pytz
import gc

from PIL import Image
from openai import OpenAI
import random

from io import BytesIO

# modules for image proyx server
from django.views.decorators.http import require_GET
from urllib.parse import quote
from django.http import HttpRequest, HttpResponse, JsonResponse
from rest_framework.request import Request

# modules for search results
from .embedding_functions import get_text_scores
from .embedding_functions import get_image_vector
from .embedding_functions import get_image_scores
from .functions import get_asset_design_features
from .functions import load_image


@csrf_exempt
@require_GET
def proxy_image(request: HttpRequest) -> HttpResponse:
    """Fetch a remote image and return it with CORS headers.

    Args:
        request (HttpRequest): GET request. Query parameter ``url`` is the image URL to proxy.

    Returns:
        HttpResponse: Image body and upstream ``Content-Type``, with
        ``Access-Control-Allow-Origin: *``. Status 400 if ``url`` is missing; 500 if the fetch fails.

    Frontend:
        Not referenced from ``image_labeler`` templates/JS in-repo; use GET ``/proxy_image/?url=…``
        for CORS-safe embedding (e.g. external tools or future template img URLs).
    """

    image_url = request.GET.get("url")

    logger.debug("------------")
    logger.debug(image_url)

    if not image_url:
        return HttpResponse("URL parameter is required", status=400)

    try:
        # Fetch the image from the external source
        response = requests.get(image_url, stream=True, verify=False)
        response.raise_for_status()

        # Get the content type (image/jpeg, image/png, etc.)
        content_type = response.headers.get("Content-Type", "image/jpeg")

        # Create the response with the image content
        django_response = HttpResponse(response.content, content_type=content_type)

        # Add CORS headers
        django_response["Access-Control-Allow-Origin"] = "*"
        return django_response

    except requests.exceptions.RequestException as e:
        return HttpResponse(f"Error fetching image: {e}", status=500)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_color_labels(request: Request) -> JsonResponse:
    """Return assets still needing manual color labels for a labeling source.

    Args:
        request (Request): GET body/data. ``source`` (str, e.g. ``initial_training_set``);
            optional ``samples`` (int, default 100) caps the returned list.

    Returns:
        JsonResponse: ``status`` ``success`` with ``total_in_full_set_to_label``,
        ``total_in_set_to_label``, and ``assets_to_label`` (``asset_id``, ``image_link``); or
        ``status`` ``fail`` with ``explanation`` if ``source`` is invalid.

    Frontend:
        ``image_labeler.label_images.views.show_images`` → ``show_images.html`` (initial color
        training grid and totals).
    """

    source = request.data.get("source", None)
    samples = request.data.get("samples", 100)

    if source == "initial_training_set":

        assets_w_labels = asset_color_manual_label.objects.filter(
            manual_label=True
        ).values_list("asset_id", flat=True)

        assets_wo_labels = asset_table.objects.all().exclude(
            asset_id__in=assets_w_labels
        )

        assets_to_label = random.sample(
            list(assets_wo_labels.values("asset_id", "image_link")),
            assets_wo_labels.count(),
        )

        if samples < assets_wo_labels.count():
            assets_to_label = random.sample(
                list(assets_wo_labels.values("asset_id", "image_link")), samples
            )
        else:
            assets_to_label = random.sample(
                list(assets_wo_labels.values("asset_id", "image_link")),
                assets_wo_labels.count(),
            )

        ######################
        # hard code an asset for testing purproses. Needs to be commented out when in production

        # target_assets = [
        #  '10009804', '10004087', '10010211', '10006591', '10004911',
        #  '10006612', '10006501', '10003694', '10001259', '10005016',
        #  '10000003', '10000006', '10006340', '10006360', '10008533',
        #  '10008638', '10008693', '10008727', '10008772', '10001263']

        # assets_to_label = list(asset_table.objects.filter(asset_id__in=target_assets).values())
        ######################

        total_in_full_set_to_label = len(assets_wo_labels)
        total_in_set_to_label = len(assets_to_label)

        return JsonResponse(
            {
                "status": "success",
                "total_in_full_set_to_label": total_in_full_set_to_label,
                "total_in_set_to_label": total_in_set_to_label,
                "assets_to_label": assets_to_label,
            },
            safe=False,
        )

    return JsonResponse({"status": "fail", "explanation": "invalid source"}, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def update_color_labels(request: Request) -> JsonResponse:
    """Create or update manual color layer rows in ``asset_color_manual_label``.

    Args:
        request (Request): POST body. ``asset_id`` and ``color_labels`` (list of dicts:
        ``color_type``, ``layer_type``, ``color_index``, ``color_rgb_values``, ``mask_rgb_values``,
        ``color_map_link``, ``labeler_id``).

    Returns:
        JsonResponse: ``status`` and ``explaination`` from the last processed label entry.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (``api_update_color_labels``), used from the
        color-layer UI on ``show_images.html``.
    """

    logger.debug("updating color labels")

    asset_id = request.data.get("asset_id", None)
    color_labels = request.data.get("color_labels", None)

    logger.debug("-------------vVv---------------")
    logger.debug(asset_id)
    logger.debug(color_labels)

    for label in color_labels:

        logger.debug(label)
        color_type = label.get("color_type", None)
        layer_type = label.get("layer_type", None)
        color_index = label.get("color_index", None)
        color_rgb_values = label.get("color_rgb_values", None)
        mask_rgb_values = label.get("mask_rgb_values", None)
        color_map_link = label.get("color_map_link", None)
        labeler_id = label.get("labeler_id", None)

        date_created = timezone.now()

        # #default hex code
        # hex_code = None

        # #convert rgb values into hex code
        # if rgb_values is not None:
        #       rgb_values = rgb_values.strip('rgb()').split(', ')
        #       # Convert each RGB component to an integer, then format it as a two-digit hex
        #       hex_code = "#{:02x}{:02x}{:02x}".format(int(rgb_values[0]), int(rgb_values[1]), int(rgb_values[2]))

        # remove all entries if the asset is mixed or no fill
        if color_type != "color":
            entries = asset_color_manual_label.objects.filter(asset_id=asset_id)
            for entry in entries:
                entry.delete()

        if color_type == "color":
            entries = asset_color_manual_label.objects.filter(asset_id=asset_id)
            for entry in entries:
                if entry.color_type != "color":
                    entry.delete()

        # either update or create an new color entry
        try:
            entry = asset_color_manual_label.objects.get(
                asset_id=asset_id, color_index=color_index
            )

            if color_type is not None:
                entry.color_type = color_type

            if layer_type is not None:
                entry.layer_type = layer_type

            if color_index is not None:
                entry.color_index = color_index

            if color_rgb_values is not None:
                entry.color_rgb_values = color_rgb_values

            if mask_rgb_values is not None:
                entry.mask_rgb_values = mask_rgb_values

            if color_map_link is not None:
                entry.color_map_link = color_map_link

            if labeler_id is not None:
                entry.labeler_id = labeler_id

            if date_created is not None:
                entry.date_created = date_created

            entry.save()

            result = {
                "status": "success",
                "explaination": "updated colors labels for asset " + asset_id,
            }

        except ObjectDoesNotExist:

            new_entry = asset_color_manual_label(
                asset_id=asset_id,
                color_type=color_type,
                layer_type=layer_type,
                color_index=color_index,
                color_rgb_values=color_rgb_values,
                mask_rgb_values=mask_rgb_values,
                color_map_link=color_map_link,
                manual_label=True,
                labeler_id=labeler_id,
                date_created=date_created,
            )

            new_entry.save()

            result = {
                "status": "success",
                "explaination": "created colors labels for asset " + asset_id,
            }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def remove_color_label(request: Request) -> JsonResponse:
    """Delete one manual color row for an asset and color index.

    Args:
        request (Request): POST body. ``asset_id`` and ``color_index`` identify the row.

    Returns:
        JsonResponse: ``status`` and ``explaination`` for success or missing row.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (``api_remove_color_label``), color layer
        controls on ``show_images.html``.
    """

    asset_id = request.data.get("asset_id", None)
    color_index = request.data.get("color_index", None)

    try:
        entry = asset_color_manual_label.objects.get(
            asset_id=asset_id, color_index=color_index
        )

        entry.delete()

        result = {
            "status": "success",
            "explaination": "asset "
            + str(asset_id)
            + " with color_index:"
            + str(color_index)
            + " removed.",
        }

    except ObjectDoesNotExist:

        result = {
            "status": "failure",
            "explaination": "asset "
            + str(asset_id)
            + " with color_index:"
            + str(color_index)
            + " not found.",
        }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def compute_color_distance_labels(request: Request) -> JsonResponse:
    """Map a hex color to the closest named label using delta-E distance.

    Args:
        request (Request): GET body/data. ``first_color`` (str): hex color to compare to a fixed palette.

    Returns:
        JsonResponse: ``status`` and ``closest_color`` (nearest label name).

    Frontend:
        No ``image_labeler`` template/JS caller in-repo; available for tooling or future color UI.
    """

    from basic_colormath import get_delta_e_hex

    first_color = request.data.get("first_color", None)

    color_labels = [
        {"label": "red", "hex_code": "#ff0000"},
        {"label": "orange", "hex_code": "#ff7d00"},
        {"label": "yellow", "hex_code": "#FFFF00"},
        {"label": "green", "hex_code": "#00FF00"},
        {"label": "blue", "hex_code": "#0000FF"},
        {"label": "purple", "hex_code": "#7D00FF"},
        {"label": "brown", "hex_code": "#9B4B19"},
        {"label": "gray", "hex_code": "#AFAFAF"},
        {"label": "black", "hex_code": "#000000"},
        {"label": "white", "hex_code": "#FFFFFF"},
    ]

    min_distance = float("inf")
    closest_color = ""

    for color in color_labels:
        color_distance = get_delta_e_hex(first_color, color["hex_code"])
        logger.debug(color["label"] + ":" + str(color_distance))
        if color_distance < min_distance:
            min_distance = color_distance
            closest_color = color["label"]

    result = {"status": "success", "closest_color": closest_color}

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_assets_to_label(request: Request) -> JsonResponse:
    """Sample art-type assets the labeler has not yet completed, or return one asset by id.

    Args:
        request (Request): GET body/data. ``samples`` (int, default 25), ``task_type``,
        ``label_type``, ``labeler_id``; optional ``asset_id`` to return only that asset.

    Returns:
        JsonResponse: ``status`` ``success`` and ``assets_to_label`` (list of ``asset_id``, ``image_link``).

    Frontend:
        No ``image_labeler`` template/JS caller in-repo; intended for art-type sampling workflows.
    """

    samples = request.data.get("samples", 25)
    task_type = request.data.get("task_type")
    label_type = request.data.get("label_type")
    labeler_id = request.data.get("labeler_id")
    asset_id = request.data.get("asset_id", None)

    if asset_id is not None:
        sample_of_assets_to_label = label_data_selected_assets_new.objects.filter(
            asset_id=asset_id
        ).values("asset_id", "image_link")

        sample_of_assets_to_label = list(sample_of_assets_to_label)

    else:
        # get a list of all assets that have received two or more responses
        labeled_assets = (
            label_data_art_type_prompt_responses.objects.filter(rule_index=1)
            .values("asset_id")
            .annotate(label_count=Count("id", distinct=True))
            .filter(label_count__gte=2)
            .values_list("asset_id", flat=True)
        )

        labeler_labeled_assets = label_data_art_type_prompt_responses.objects.filter(
            labeler_id=labeler_id
        ).values_list("asset_id", flat=True)

        assets_to_label = label_data_selected_assets_new.objects.exclude(
            asset_id__in=labeled_assets
        ).exclude(asset_id__in=labeler_labeled_assets)
        sample_of_assets_to_label = random.sample(
            list(assets_to_label.values("asset_id", "image_link")), samples
        )

    return JsonResponse(
        {"status": "success", "assets_to_label": sample_of_assets_to_label}, safe=False
    )


@csrf_exempt
@api_authorization
@api_view(["POST"])
def add_label(request: Request) -> JsonResponse:
    """Upsert an art-type label row in ``label_data_art_type`` for an asset.

    Args:
        request (Request): POST body. ``asset_id``, ``labeler_id``, ``task_type`` (must be
        ``art_type``), ``label_type``, ``label_data`` (dict with the label under ``label_type``).

    Returns:
        JsonResponse: ``status`` and ``explanation`` after update or insert.

    Frontend:
        No ``image_labeler`` template/JS caller in-repo; legacy art-type label upsert endpoint.
    """

    asset_id = request.data.get("asset_id")
    labeler_id = request.data.get("labeler_id")
    task_type = request.data.get("task_type")
    label_type = request.data.get("label_type")
    label_data = request.data.get("label_data")

    if task_type == "art_type":

        try:
            entry = label_data_art_type.objects.get(
                asset_id=asset_id, labeler_id=labeler_id
            )

            entry.label = label_data[label_type]

            entry.save()

            result = {
                "status": "success",
                "explanation": "updated colors labels for asset " + str(asset_id),
            }

        except ObjectDoesNotExist:

            new_entry = label_data_art_type(
                asset_id=asset_id,
                datetime_created=timezone.now(),
                labeler_id=labeler_id,
                label=label_data[label_type],
            )

            new_entry.save()

            result = {
                "status": "success",
                "explanation": "added label for asset " + str(asset_id),
            }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_labelling_rules(request: Request) -> JsonResponse:
    """Return labelling rules with nested directives and examples (with image links).

    Args:
        request (Request): GET body/data. Optional ``task_type`` and ``rule_indexes`` to filter rules.

    Returns:
        JsonResponse: ``status``, ``task_type_set``, and ``labelling_rules`` (each entry includes
        ``directives`` with ``examples``), sorted by ``rule_index``.

    Frontend:
        Many pages: ``label_images.views`` (e.g. ``mturk_redirect`` → ``label_content.html``,
        ``view_batch_labels``, ``manage_rules``, ``view_asset``, ``view_label_issues``,
        ``view_prediction_labels``, ``reconcile_labels``, ``correct_mismatch_labels``); also
        ``static/js/api_calls.js`` (``api_get_labelling_rules``).
    """
    # Retrieve the task_type from the request
    task_type = request.data.get("task_type", None)
    rule_indexes = request.data.get("rule_indexes", None)

    filters = {}
    if task_type:
        filters["task_type"] = task_type
    if rule_indexes:
        filters["rule_index__in"] = rule_indexes

    # Retrieve filtered rules or return all if no filters exist
    label_rules = list(labelling_rules.objects.filter(**filters).values())
    examples = rule_examples.objects.filter(**filters).values()
    directives = rule_directives.objects.filter(**filters).values()
    selected_assets_new = label_data_selected_assets_new.objects.values(
        "asset_id", "image_link"
    )

    logger.debug("------------label_rules------------")
    logger.debug(label_rules)

    rule_set = []
    task_type_set = []

    for rule in label_rules:

        task_type_set.append(rule["task_type"])

        entry = {
            "rule_index": rule["rule_index"],
            "task_type": rule["task_type"],
            "title": rule["title"],
            "description": rule["description"],
            "prompt": rule["prompt"],
        }

        # Collect all matching directives
        directive_list = []

        matching_directive = [
            directive
            for directive in directives
            if directive["task_type"] == rule["task_type"]
            and directive["rule_index"] == rule["rule_index"]
        ]

        for directive in matching_directive:
            example_set = []

            for example in examples:
                if example["directive_id"] == directive["id"]:

                    matching_asset = next(
                        (
                            asset
                            for asset in selected_assets_new
                            if asset["asset_id"] == example["asset_id"]
                        ),
                        None,
                    )

                    # Attach image link to the example
                    example["image_link"] = (
                        matching_asset["image_link"] if matching_asset else None
                    )

                    example_set.append(example)

            directive["examples"] = example_set
            directive_list.append(directive)  # Append to list instead of overwriting

        # Always include 'directives', even if empty
        entry["directives"] = directive_list

        rule_set.append(
            entry
        )  # Append entry for every rule, not just matching directives

    rule_set = sorted(rule_set, key=lambda x: x["rule_index"])

    task_type_set = list(set(task_type_set))

    result = {
        "status": "success",
        "task_type_set": task_type_set,
        "labelling_rules": rule_set,
    }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def collect_label(request: Request) -> JsonResponse:
    """Upsert a simple label in the dynamic model ``label_data_{task_type}_labels``.

    Args:
        request (Request): POST body. ``task_type`` (suffix for the dynamic model name),
        ``asset_id``, ``labeler_source``, ``labeler_id``, ``label_type``, ``label``.

    Returns:
        JsonResponse: ``status`` and ``explanation`` for update or insert.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (label collection POST), used from dynamic
        ``label_content.html`` flows (MTurk/internal labeling).
    """

    task_type = request.data.get("task_type", None)
    asset_id = request.data.get("asset_id", None)
    labeler_source = request.data.get("labeler_source", None)
    labeler_id = request.data.get("labeler_id", None)
    label_type = request.data.get("label_type", None)
    label = request.data.get("label", None)

    data_table = apps.get_model("labeling_api", "label_data_" + task_type + "_labels")

    try:
        entry = data_table.objects.get(asset_id=asset_id, labeler_id=labeler_id)

        entry.label = label

        entry.save()

        result = {
            "status": "success",
            "explanation": "updated label for asset " + str(asset_id),
        }

    except ObjectDoesNotExist:

        new_entry = data_table(
            datetime_created=timezone.now(),
            labeler_source=labeler_source,
            labeler_id=labeler_id,
            label_type=label_type,
            asset_id=asset_id,
            label=label,
        )

        new_entry.save()

        result = {
            "status": "success",
            "explanation": "added label for asset " + str(asset_id),
        }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def collect_prompt_internal_source(request: Request) -> JsonResponse:
    """Append an Internal-source prompt response with incremented ``labeler_count``.

    Args:
        request (Request): POST body. ``asset_id``, ``labeler_id``, ``task_type``, ``rule_index``,
        ``prompt_response``; optional ``labeler_source`` (default ``Internal``).

    Returns:
        JsonResponse: ``status`` and ``explanation`` after saving to ``prompt_responses``.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (``collect_prompt`` path for Internal source),
        same labeling UI as ``collect_prompt``.
    """

    asset_id = request.data.get("asset_id", None)
    labeler_source = request.data.get("labeler_source", "Internal")
    labeler_id = request.data.get("labeler_id", None)
    task_type = request.data.get("task_type", None)
    rule_index = request.data.get("rule_index", None)
    prompt_response = request.data.get("prompt_response", None)

    datetime_created = datetime.now(pytz.timezone("America/Chicago")).strftime(
        "%Y-%m-%d %I:%M %p %Z"
    )

    # compute label count for asset by labeler id
    labeler_count = (
        prompt_responses.objects.filter(
            asset_id=asset_id,
            task_type=task_type,
            labeler_id=labeler_id,
            rule_index=rule_index,
        )
        .order_by("-labeler_count")
        .values_list("labeler_count", flat=True)
        .first()
    ) or 0

    labeler_count += 1

    new_entry = prompt_responses(
        datetime_created=timezone.now(),
        asset_id=asset_id,
        labeler_source=labeler_source,
        labeler_id=labeler_id,
        labeler_count=labeler_count,
        task_type=task_type,
        rule_index=rule_index,
        prompt_response=prompt_response,
    )

    new_entry.save()

    result = {
        "status": "success",
        "explanation": "added prompt for asset " + str(asset_id),
    }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def collect_prompt(request: Request) -> JsonResponse:
    """Upsert a prompt response in ``label_data_{task_type}_prompt_responses``.

    Args:
        request (Request): POST body. ``task_type``, ``asset_id``, ``labeler_source``, ``labeler_id``,
        ``label_type``, ``rule_index``, ``prompt_response``, optional MTurk fields
        (``assignment_id``, ``hit_id``, ``is_test_question``, ``mturk_batch_id``, ``is_lure_question``).

    Returns:
        JsonResponse: ``status`` and ``explanation`` for update or insert.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (``collect_prompt``), ``label_content.html`` yes/no
        prompts (MTurk and internal).
    """

    task_type = request.data.get("task_type", None)
    asset_id = request.data.get("asset_id", None)
    labeler_source = request.data.get("labeler_source", None)
    labeler_id = request.data.get("labeler_id", None)
    label_type = request.data.get("label_type", None)
    rule_index = request.data.get("rule_index", None)
    prompt_response = request.data.get("prompt_response", None)
    assignment_id = request.data.get("assignment_id")
    hit_id = request.data.get("hit_id")
    is_test_question = request.data.get("is_test_question", "no")
    mturk_batch_id = request.data.get("mturk_batch_id", None)
    is_lure_question = request.data.get("is_lure_question", "no")

    data_table = apps.get_model(
        "labeling_api", "label_data_" + task_type + "_prompt_responses"
    )

    logger.debug("----------oOo----------")
    logger.debug("rule_index: " + str(rule_index))
    logger.debug("labeler_id: " + str(labeler_id))
    logger.debug("users provided response: " + prompt_response)

    try:
        entry = data_table.objects.get(
            asset_id=asset_id,
            labeler_id=labeler_id,
            task_type=task_type,
            rule_index=rule_index,
        )

        entry.prompt_response = prompt_response

        entry.save()

        result = {
            "status": "success",
            "explanation": "updated prompt for asset " + str(asset_id),
        }

    except ObjectDoesNotExist:

        new_entry = data_table(
            datetime_created=timezone.now(),
            labeler_source=labeler_source,
            labeler_id=labeler_id,
            label_type=label_type,
            asset_id=asset_id,
            task_type=task_type,
            rule_index=rule_index,
            prompt_response=prompt_response,
            assignment_id=assignment_id,
            hit_id=hit_id,
            is_test_question=is_test_question,
            mturk_batch_id=mturk_batch_id,
            is_lure_question=is_lure_question,
        )

        new_entry.save()

        result = {
            "status": "success",
            "explanation": "added prompt for asset " + str(asset_id),
        }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def remove_prompt_responses(request: Request) -> JsonResponse:
    """Delete the most recent Internal ``prompt_responses`` row for an asset/rule.

    Args:
        request (Request): POST body. ``asset_id``, ``labeler_id``, ``rule_index``, ``task_type``;
        ``labeler_source`` (default ``Internal``).

    Returns:
        JsonResponse: ``status`` and ``explanation`` (success or missing entry).

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (undo/remove last prompt), ``label_content.html``.
    """

    asset_id = request.data.get("asset_id")
    labeler_id = request.data.get("labeler_id")
    labeler_source = request.data.get("labeler_source", "Internal")
    rule_index = request.data.get("rule_index")
    task_type = request.data.get("task_type")

    if labeler_source == "Internal":

        entries = prompt_responses.objects.filter(
            asset_id=asset_id,
            labeler_id=labeler_id,
            rule_index=rule_index,
            task_type=task_type,
        )

        most_recent_entry = entries.order_by("-datetime_created").first()

        if most_recent_entry:
            most_recent_entry.delete()

            result = {
                "status": "success",
                "explanation": "removed prompt response from rule "
                + str(rule_index)
                + " for asset "
                + str(asset_id)
                + ".",
            }

        else:
            result = {"status": "failure", "explanation": "Entry does not exist."}

    # else:

    #     if rule_index == None:

    #         entries = label_data_art_type_prompt_responses \
    #                 .objects.filter(asset_id = asset_id,
    #                                 labeler_id = labeler_id)

    #         for entry in entries:
    #             entry.delete()

    #         result = {'status':'success',
    #             'explanation':'removed prompt responses for asset ' + str(asset_id)}

    #     else:

    #         entry = label_data_art_type_prompt_responses \
    #                 .objects.filter(asset_id = asset_id,
    #                             labeler_id = labeler_id,
    #                             rule_index = rule_index)

    #         entry.delete()

    #         result = {'status':'success',
    #             'explanation':'removed prompt response '
    #             + str(rule_index)
    #             + ' for asset '
    #             + str(asset_id)}

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_prompt_responses(request: Request) -> JsonResponse:
    """Return submitted prompt responses grouped by asset and labeler (MTurk export shape).

    Args:
        request (Request): GET; uses fixed filters on ``prompt_responses`` (submitted, batch 3, etc.).

    Returns:
        JsonResponse: Nested mapping keyed by ``asset_id`` with ``labelers`` and rule payloads.

    Frontend:
        ``image_labeler.label_images.views.view_mturk_responses`` → ``view_mturk_responses.html``.
    """

    # prompt_responses_list = list(prompt_responses.objects.values())

    prompt_response_list = prompt_responses.objects.filter(
        submission_status="submitted", is_test_question__isnull=True, mturk_batch_id=3
    ).values()

    prompt_response_list = list(prompt_response_list)

    selected_assets_new_list = list(
        label_data_selected_assets_new.objects.values("asset_id", "image_link")
    )

    # Create a mapping of asset_id to image_link for quick lookup
    asset_to_image_link = {
        asset["asset_id"]: asset["image_link"] for asset in selected_assets_new_list
    }

    # Add image_link to each prompt response if the asset_id exists in selected assets
    for prompt in prompt_response_list:
        prompt["image_link"] = asset_to_image_link.get(prompt["asset_id"], None)

    # Nested data structure: first by asset_id, then by labeler_id.
    grouped_data = defaultdict(
        lambda: defaultdict(
            lambda: {
                "image_link": "",
                "assignment_id": "",
                "hit_id": "",
                "labeler_id": "",
                "rules": {},
            }
        )
    )

    for entry in prompt_response_list:
        asset_id = entry["asset_id"]
        labeler_id = entry["labeler_id"]

        # Set top-level fields for each asset_id under each labeler_id.
        if grouped_data[asset_id][labeler_id]["labeler_id"] == "":
            grouped_data[asset_id][labeler_id]["image_link"] = entry["image_link"]
            grouped_data[asset_id][labeler_id]["assignment_id"] = entry["assignment_id"]
            grouped_data[asset_id][labeler_id]["hit_id"] = entry["hit_id"]
            grouped_data[asset_id][labeler_id]["labeler_id"] = labeler_id

        # Add unique fields for each rule
        rule_data = {
            "rule_index": entry["rule_index"],
            "prompt_response": entry["prompt_response"],
            "datetime_created": entry["datetime_created"],
            "label_type": entry["label_type"],
        }
        grouped_data[asset_id][labeler_id]["rules"][entry["rule_index"]] = rule_data

    # Final structured output without the "data" wrapper, using asset_id as the top-level key
    result = {
        asset_id: {  # Use asset_id as the key
            "asset_id": asset_id,
            "image_link": labelers[next(iter(labelers))][
                "image_link"
            ],  # Get image_link from the first labeler (assuming it's the same for all labelers)
            "hit_id": labelers[next(iter(labelers))][
                "hit_id"
            ],  # Get hit_id from the first labeler (assuming it's the same for all labelers)
            "labelers": {
                labeler_data["labeler_id"]: {
                    "assignment_id": labeler_data["assignment_id"],
                    "rules": labeler_data["rules"],
                }
                for labeler_data in labelers.values()
            },
        }
        for asset_id, labelers in grouped_data.items()
    }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def collect_validation_response(request: Request) -> JsonResponse:
    """Store validator accept/reject and feedback on matching ``prompt_responses`` rows.

    Args:
        request (Request): POST body. ``assignment_id``, ``asset_id``, ``rule_index``, ``response``,
        optional ``feedback`` (default message if omitted).

    Returns:
        JsonResponse: ``status`` and ``explanation`` after updating rows.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (MTurk validation), ``label_content.html``.
    """

    assignment_id = request.data.get("assignment_id", None)
    asset_id = request.data.get("asset_id", None)
    rule_index = request.data.get("rule_index", None)
    response = request.data.get("response", None)
    feedback = request.data.get("feedback", "No feedback provided")

    prompts = prompt_responses.objects.filter(
        assignment_id=assignment_id, asset_id=asset_id, rule_index=rule_index
    )

    for prompt in prompts:
        prompt.accept_response = response
        prompt.feedback = feedback
        prompt.save()

    # mturk = boto3.client(
    #     "mturk",
    #     aws_access_key_id=settings.MTURK_ACCESS_ID,
    #     aws_secret_access_key=settings.MTURK_SECRET_KEY,
    #     region_name="us-east-1",
    #     endpoint_url=settings.MTURK_HOST,
    # )

    # if response == 'yes':
    #     try:
    #         mturk.approve_assignment(AssignmentId=assignment_id)
    #         print(f"Assignment {assignment_id} approved successfully.")
    #     except ClientError as e:
    #         print(f"Failed to approve assignment {assignment_id}: {e.response['Error']['Message']}")

    # else:
    #     try:
    #         mturk.reject_assignment(AssignmentId=assignment_id, RequesterFeedback=feedback)
    #         print(f"Assignment {assignment_id} rejected successfully.")
    #     except ClientError as e:
    #         print(f"Failed to reject assignment {assignment_id}: {e.response['Error']['Message']}")

    result = {
        "status": "success",
        "explanation": "added label for asset " + str(assignment_id),
    }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def update_submission_status(request: Request) -> JsonResponse:
    """Mark all ``prompt_responses`` for an assignment as submitted.

    Args:
        request (Request): POST body. ``assignment_id`` (str).

    Returns:
        JsonResponse: ``status`` ``success`` or ``failed`` with ``explanation``.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (assignment submit), ``label_content.html``.
    """

    assignment_id = request.data.get("assignment_id", None)

    entries = prompt_responses.objects.filter(assignment_id=assignment_id)

    if entries.exists():
        entries.update(submission_status="submitted")

        result = {
            "status": "success",
            "explanation": "updated status submission for assignment "
            + str(assignment_id),
        }

    else:

        result = {"status": "failed", "explanation": "assignmnet id not found"}

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_test_questions(request: Request) -> JsonResponse:
    """Return a random sample of gold-standard test questions with prompts and image links.

    Args:
        request (Request): GET body/data. ``samples`` (int, default 2) count of distinct assets.

    Returns:
        JsonResponse: Per-asset grouped structure with ``rule_data`` and ``prompt`` text.

    Raises:
        ValueError: If ``samples`` exceeds the number of distinct test assets (``random.sample``).

    Frontend:
        ``image_labeler.label_images.views.mturk_redirect`` when ``test_the_labeler`` is true →
        ``label_content.html`` (parallel fetch with rules and ``asset_batch``).
    """

    samples = request.data.get("samples", 2)

    unique_questions = test_questions.objects.values_list(
        "asset_id", flat=True
    ).distinct()

    selected_questions = random.sample(list(unique_questions), samples)

    result = (
        test_questions.objects.filter(asset_id__in=selected_questions)
        .values("id", "asset_id", "rule_index", "prompt_response", "example_id")
        .annotate(
            image_link=Subquery(
                label_data_selected_assets_new.objects.filter(
                    asset_id=OuterRef("asset_id")
                ).values("image_link")[:1]
            )
        )
    )

    result = list(result.values())

    rule_prompts = {
        rule["rule_index"]: rule["prompt"]
        for rule in labelling_rules.objects.values("rule_index", "prompt")
    }

    grouped_result = defaultdict(list)

    for item in result:
        asset_id = item["asset_id"]

        # Check if this asset_id is already in the grouped_result
        if asset_id not in grouped_result:
            grouped_result[asset_id] = {
                "id": item["id"],
                "example_id": item["example_id"],
                "image_link": item["image_link"],
                "rule_data": [],  # Initialize rule_data as an empty list
            }

        # Add the prompt from labelling_rules using rule_index
        rule_data = {
            "rule_index": item["rule_index"],
            "prompt_response": item["prompt_response"],
            "prompt": rule_prompts.get(
                item["rule_index"], ""
            ),  # Get prompt or empty if not found
        }

        # Append the rule data to the rule_data list for this asset_id
        grouped_result[asset_id]["rule_data"].append(rule_data)

    return JsonResponse(grouped_result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_batch_for_viewing(request: Request) -> JsonResponse:
    """Aggregate per-asset agreement labels from prompts, optionally corrected and batch-filtered.

    Args:
        request (Request): GET body/data. ``task_type``, ``rule_index``, optional ``batch_index`` filter.

    Returns:
        JsonResponse: ``assets_w_labels`` list of records with derived ``label`` and ``agree_status``.

    Frontend:
        ``image_labeler.label_images.views.view_batch_labels`` → ``view_batch_labels.html`` (batch QA
        review and label filters).
    """

    task_type = request.data.get("task_type", None)
    rule_index = int(request.data.get("rule_index", None))
    batch_index = request.data.get("batch_index", None)

    corrected_labels = pd.DataFrame(
        list(
            modified_prompt_table.objects.filter(
                task_type=task_type, rule_index=rule_index
            ).values("asset_id", "task_type", "rule_index", "modified_prompt_response")
        )
    )

    logger.debug("-----corrected_labels------")
    logger.debug(corrected_labels)

    labeled_assets = pd.DataFrame(
        list(
            prompt_responses.objects.filter(
                task_type=task_type, rule_index=rule_index
            ).values("asset_id", "prompt_response")
        )
    )

    asset_to_batch = pd.DataFrame(
        label_data_selected_assets_new.objects.values(
            "asset_id", "large_sub_batch", "batch_id", "image_link", "color_type"
        )
    )

    logger.debug("-----labeled_assets-----")
    logger.debug(labeled_assets)

    assets_w_labels = (
        labeled_assets.assign(
            yes_response=lambda x: np.where(x["prompt_response"] == "yes", 1, 0)
        )
        .groupby(["asset_id"])
        .agg(
            samples=("prompt_response", "count"), yes_responses=("yes_response", "sum")
        )
        .assign(no_responses=lambda x: x.samples - x.yes_responses)
        .assign(percent_agree=lambda x: x.yes_responses / x.samples)
        .assign(
            agree_status=lambda x: np.where(
                x["percent_agree"] != 0.5, "agree", "disagree"
            )
        )
        .assign(
            agree_status=lambda x: np.where(
                (x["percent_agree"] == 1.0) | (x["percent_agree"] == 0.0),
                "strongly_agree",
                x["agree_status"],
            )
        )
        .assign(
            agree_status=lambda x: np.where(
                x["samples"] == 1, "indeterminate", x["agree_status"]
            )
        )
        .assign(label="indeterminate")
        .assign(label=lambda x: np.where(x["percent_agree"] < 0.5, "no", x["label"]))
        .assign(
            label=lambda x: np.where(
                (x["percent_agree"] > 0.5) & (x["label"] != "no"), "yes", x["label"]
            )
        )
    )

    # replace incorrect labels with correct ones

    if len(corrected_labels) > 0:

        assets_w_labels = (
            assets_w_labels.merge(corrected_labels, on="asset_id", how="left")
            .assign(
                label=lambda x: np.where(
                    pd.isna(x["modified_prompt_response"]),
                    x["label"],
                    x["modified_prompt_response"],
                )
            )
            .assign(
                agree_status=lambda x: np.where(
                    pd.isna(x["modified_prompt_response"]),
                    x["agree_status"],
                    "potentially_corrected",
                )
            )
            .sort_values("modified_prompt_response")
        )

    logger.debug("------assets_w_labels-------")
    logger.debug(assets_w_labels)

    if batch_index is not None:
        assets_w_labels = assets_w_labels.merge(
            asset_to_batch, on="asset_id", how="left"
        ).query("batch_id == @batch_index")

    logger.debug("------assets_w_labels-------")
    logger.debug(assets_w_labels)

    assets_w_labels = assets_w_labels.to_dict(orient="records")

    # assets_w_labels = {}

    return JsonResponse({"assets_w_labels": assets_w_labels}, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_asset_batch(request: Request) -> JsonResponse:
    """Return incomplete assets for a batch/sub-batch and rule, excluding flagged assets.

    Args:
        request (Request): GET body/data. ``batch_id``, ``large_sub_batch``, ``task_type``,
        ``rule_index``, optional ``remove_flagged_assets`` (default True), ``batch_type``.

    Returns:
        JsonResponse: ``batch_index`` and ``asset_batch`` (``asset_id``, ``image_link``).

    Frontend:
        ``label_images.views.mturk_redirect`` (``label_content.html``), ``select_line_widths``,
        ``select_primary_colors``; ``internal`` view also requests it (incomplete view). Errors in
        logs often surface when the UI calls ``backend_python`` with this route.
    """

    batch_id = int(request.data.get("batch_id", None))
    large_sub_batch = request.data.get("large_sub_batch", [])
    batch_type = request.data.get("batch_type", "sub_batch")
    task_type = request.data.get("task_type", "asset_type")
    rule_index = int(request.data.get("rule_index", None))
    remove_flagged_assets = request.data.get("remove_flagged_assets", True)

    if isinstance(large_sub_batch, str):
        large_sub_batch = [int(x) for x in large_sub_batch.split(",") if x.strip()]
    else:
        large_sub_batch = [int(x) for x in large_sub_batch or []]

    # Assets with 2+ prompt responses for this task/rule are complete — exclude them.
    completed_ids = set(
        prompt_responses.objects.filter(task_type=task_type, rule_index=rule_index)
        .values("asset_id")
        .annotate(_cnt=Count("id"))
        .filter(_cnt__gte=2)
        .values_list("asset_id", flat=True)
    )

    # Optionally exclude assets with known label issues.
    flagged_ids = (
        set(label_issues_table.objects.values_list("asset_id", flat=True))
        if remove_flagged_assets
        else set()
    )

    asset_batch = list(
        label_data_selected_assets_new.objects.filter(
            task_type=task_type,
            rule_index=rule_index,
            batch_id=batch_id,
            large_sub_batch__in=large_sub_batch,
        )
        .exclude(asset_id__in=completed_ids)
        .exclude(asset_id__in=flagged_ids)
        .values("asset_id", "image_link")
    )

    logger.debug("get_asset_batch: %d assets in batch", len(asset_batch))

    return JsonResponse(
        {
            "batch_index": large_sub_batch,
            "asset_batch": asset_batch,
        },
        safe=False,
    )


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_batch_indexes(request: Request) -> JsonResponse:
    """Return a random sample of distinct ``sub_batch`` values.

    Args:
        request (Request): GET body/data. ``samples`` (int, default 5).

    Returns:
        JsonResponse: List of ``sub_batch`` values.

    Raises:
        ValueError: If ``samples`` exceeds the number of distinct sub-batches.

    Frontend:
        No ``image_labeler`` caller found in-repo; utility endpoint for sub-batch sampling.
    """

    samples = request.data.get("samples", 5)

    batch_indexes = label_data_selected_assets_new.objects.values_list(
        "sub_batch", flat=True
    ).distinct()

    batch_indexes = random.sample(list(batch_indexes.values("sub_batch")), samples)

    return JsonResponse(batch_indexes, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_lure_questions(request: Request) -> JsonResponse:
    """Return random lure (attention-check) questions with correct answers and prompts.

    Args:
        request (Request): GET body/data. ``samples`` (int, default 2); ``rule_index`` (default 1).

    Returns:
        JsonResponse: Grouped per-asset data with ``rule_data`` including ``correct_response``.

    Raises:
        ValueError: If ``samples`` exceeds available lure assets for the rule.

    Frontend:
        No ``image_labeler`` caller found in-repo; intended for attention-check items alongside
        ``label_content`` flows if wired later.
    """

    samples = request.data.get("samples", 2)
    rule_index = request.data.get("rule_index", 1)

    unique_questions = (
        lure_questions.objects.filter(rule_index=rule_index)
        .values_list("asset_id", flat=True)
        .distinct()
    )

    selected_questions = random.sample(list(unique_questions), samples)

    logger.debug(selected_questions)

    result = (
        lure_questions.objects.filter(asset_id__in=selected_questions)
        .values("id", "asset_id", "rule_index", "correct_response")
        .annotate(
            image_link=Subquery(
                label_data_selected_assets_new.objects.filter(
                    asset_id=OuterRef("asset_id")
                ).values("image_link")[:1]
            )
        )
    )

    result = list(result.values())

    rule_prompts = {
        rule["rule_index"]: rule["prompt"]
        for rule in labelling_rules.objects.values("rule_index", "prompt")
    }

    grouped_result = defaultdict(list)

    for item in result:
        asset_id = item["asset_id"]

        # Check if this asset_id is already in the grouped_result
        if asset_id not in grouped_result:
            grouped_result[asset_id] = {
                "id": item["id"],
                "image_link": item["image_link"],
                "rule_data": [],  # Initialize rule_data as an empty list
            }

        # Add the prompt from labelling_rules using rule_index
        rule_data = {
            "rule_index": item["rule_index"],
            "correct_response": item["correct_response"],
            "prompt": rule_prompts.get(
                item["rule_index"], ""
            ),  # Get prompt or empty if not found
        }

        # Append the rule data to the rule_data list for this asset_id
        grouped_result[asset_id]["rule_data"].append(rule_data)

    return JsonResponse(grouped_result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_disputed_assets(request: Request) -> JsonResponse:
    """List assets where labelers split 50/50 on yes/no for a rule, excluding flagged issues.

    Args:
        request (Request): GET body/data. ``rule_index`` (default 1), ``task_type``.

    Returns:
        JsonResponse: List of records with ``asset_id`` and ``image_link``.

    Frontend:
        ``image_labeler.label_images.views.reconcile_labels`` → ``label_content.html`` (disputed
        50/50 assets).
    """

    rule_index = request.data.get("rule_index", 1)
    task_type = request.data.get("task_type", None)

    asset_links = label_data_selected_assets_new.objects.values(
        "asset_id", "image_link"
    )

    asset_links = pd.DataFrame(list(asset_links))

    data = prompt_responses.objects.filter(
        rule_index=rule_index, task_type=task_type
    ).values()

    flagged_assets = pd.DataFrame(label_issues_table.objects.values())

    #################################
    # generate list of assets that have been flagged mislabeled

    flagged_assets = flagged_assets.filter(["asset_id"]).assign(has_issue="yes")

    #################################

    dispusted_assets = (
        pd.DataFrame(list(data))
        .filter(["asset_id", "labeler_id", "prompt_response"])
        .assign(samples=lambda x: x.groupby("asset_id")["asset_id"].transform("count"))
        .query("samples > 1")
        .assign(yes_response=lambda x: np.where(x.prompt_response == "yes", 1, 0))
        .groupby(["asset_id", "samples"])
        .agg(yes_response=("yes_response", "sum"))
        .reset_index()
        .assign(percent_agree=lambda x: x.yes_response / x.samples)
        .query("percent_agree == .5")
        .merge(asset_links, on="asset_id", how="left")
        .filter(["asset_id", "image_link"])
    )

    #######
    # Remove flagged assets
    dispusted_assets = dispusted_assets.merge(
        flagged_assets, on="asset_id", how="left"
    ).query('has_issue != "yes"')

    dispusted_assets = dispusted_assets.to_dict("records")

    return JsonResponse(dispusted_assets, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_assets_w_rule_labels(request: Request) -> JsonResponse:
    """Return a sample of fully rule-labeled assets for model training/evaluation.

    Args:
        request (Request): GET body/data. ``task_type`` (controls which rules are required).

    Returns:
        JsonResponse: List of asset rows with pivoted rule labels and image links.

    Frontend:
        ``image_labeler.label_images.views.view_labels`` → ``view_labels.html`` (matrix of rule labels).
    """

    task_type = request.data.get("task_type", "asset_type")

    if task_type == "asset_type":
        selected_rules = [3, 5, 6, 7]
    elif task_type == "clip_art_type":
        selected_rules = [1, 2, 3, 4, 5, 6, 7]
    elif task_type == "mono_color_type":
        selected_rules = [1, 2, 4, 5, 6]

    selected_assets_new = pd.DataFrame(
        list(label_data_selected_assets_new.objects.values("asset_id", "image_link"))
    )

    labeled_assets = (
        pd.DataFrame(
            list(
                assets_w_rule_labels.objects.values(
                    "asset_id", "task_type", "rule_index", "label"
                )
            )
        )
        .query("task_type == @task_type")
        .query("rule_index in @selected_rules")
    )
    logger.debug("-------labeled assets------------")
    logger.debug(labeled_assets.query("rule_index == 4").sum())

    fully_labeled_assets = (
        labeled_assets.query("task_type == @task_type")
        .pivot(index=["asset_id", "task_type"], columns="rule_index", values="label")
        .reset_index()
        .dropna()
        .filter(["asset_id"])
    )

    fully_labeled_assets = (
        fully_labeled_assets.merge(labeled_assets, on="asset_id", how="left")
        .merge(selected_assets_new, on="asset_id", how="left")
        .dropna()
    )
    ##################
    # select a small sample so moving the data doesn't take forever.

    selected_assets_new = fully_labeled_assets.filter(["asset_id"]).drop_duplicates()
    if len(selected_assets_new) < 2000:
        samples = len(selected_assets_new)
    else:
        samples = 2000

    selected_assets_new = selected_assets_new.sample(samples).squeeze()

    data = fully_labeled_assets.query("asset_id in @selected_assets_new").to_dict(
        orient="records"
    )

    logger.debug("---------data----------")
    logger.debug(data)

    # data = {}

    return JsonResponse(data, safe=False)


def _build_session_options(task_type: str, remove_flagged_assets: bool = True) -> dict:
    """Core data-building logic for the setup_session page.

    Separated from the view so it can be (a) called directly without an HTTP round-trip and
    (b) cached independently of request parameters like ``labeler_source``.

    Args:
        task_type: The labeling task to build options for (e.g. ``"asset_type"``).
        remove_flagged_assets: When True, assets in ``label_issues`` are excluded.

    Returns:
        dict with keys ``task_types``, ``labeler_ids``, ``batch_options``,
        ``labeling_rule_options``, ``rule_index_stats``, ``sub_batch_stats``.
    """
    from django.core.cache import cache

    cache_key = f"session_opts_v2::{task_type}::{'excl_flags' if remove_flagged_assets else 'incl_flags'}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug("_build_session_options cache hit: %s", cache_key)
        return cached

    # ── menu lists ──────────────────────────────────────────────────────────
    task_types = list(
        labelling_rules.objects.exclude(task_type="color_type")
        .values("task_type")
        .distinct()
        .order_by("task_type")
    )
    labeler_ids = list(labeler_table.objects.values("id", "display_name"))
    selected_rules = pd.DataFrame(
        labelling_rules.objects.filter(task_type=task_type).values(
            "task_type", "rule_index", "title"
        )
    )
    labeling_rule_options = selected_rules.sort_values("rule_index").reset_index(
        drop=True
    )

    # ── selected assets (batch/sub-batch metadata) ──────────────────────────
    assets_qs = label_data_selected_assets_new.objects.filter(
        task_type=task_type
    ).values("asset_id", "batch_id", "large_sub_batch", "task_type", "rule_index")

    # Exclude flagged assets at the DB level when requested.
    if remove_flagged_assets:
        flagged_ids = label_issues_table.objects.values_list("asset_id", flat=True)
        assets_qs = assets_qs.exclude(asset_id__in=flagged_ids)

    # For line_width_type, only include assets that have lines.
    if task_type == "line_width_type":
        has_lines_ids = line_type_table.objects.filter(
            line_type="has lines"
        ).values_list("asset_id", flat=True)
        assets_qs = assets_qs.filter(asset_id__in=has_lines_ids)

    selected_assets_new = pd.DataFrame(list(assets_qs))

    batch_options = (
        selected_assets_new[["batch_id"]]
        .drop_duplicates()
        .sort_values("batch_id")
        .to_dict(orient="records")
    )

    # ── label counts (ORM aggregation — no full prompt_responses scan) ───────
    label_counts_qs = (
        prompt_responses.objects.filter(task_type=task_type)
        .values("asset_id", "rule_index")
        .annotate(_cnt=Count("id"))
    )
    asset_label_counts = pd.DataFrame(list(label_counts_qs))

    if task_type == "line_width_type":
        # line_width_samples are counted as completions for line_width tasks.
        lw_counts_qs = line_width_sample_table.objects.values("asset_id").annotate(
            _cnt=Count("labeler_id", distinct=True)
        )
        lw_df = pd.DataFrame(list(lw_counts_qs))
        if not lw_df.empty:
            lw_df["rule_index"] = 1
            if not asset_label_counts.empty:
                # Take the maximum count from either source per asset.
                combined = pd.concat(
                    [asset_label_counts, lw_df[["asset_id", "rule_index", "_cnt"]]],
                    ignore_index=True,
                )
                asset_label_counts = combined.groupby(
                    ["asset_id", "rule_index"], as_index=False
                ).agg(_cnt=("_cnt", "max"))
            else:
                asset_label_counts = lw_df[["asset_id", "rule_index", "_cnt"]]

    if not asset_label_counts.empty:
        asset_label_counts = asset_label_counts.rename(columns={"_cnt": "count"})
        asset_label_counts["task_type"] = task_type
        asset_label_counts["completed"] = (asset_label_counts["count"] >= 2).astype(int)
        asset_label_counts["one_label"] = (asset_label_counts["count"] == 1).astype(int)
    else:
        asset_label_counts = pd.DataFrame(
            columns=[
                "asset_id",
                "task_type",
                "rule_index",
                "count",
                "completed",
                "one_label",
            ]
        )

    # ── merge counts onto asset list ─────────────────────────────────────────
    asset_list = selected_assets_new.merge(
        asset_label_counts, on=["asset_id", "task_type", "rule_index"], how="left"
    ).fillna(0)

    # ── stats groupbys ────────────────────────────────────────────────────────
    rule_index_stats = (
        asset_list.groupby(["task_type", "batch_id", "rule_index"])
        .agg(completed_labels=("completed", "sum"), samples=("asset_id", "count"))
        .astype({"completed_labels": "int"})
        .reset_index()
        .merge(labeling_rule_options, on=["task_type", "rule_index"], how="left")
    )

    # Aggregated totals per rule_index (across all batches) — used for rule selection buttons.
    # Falls back to labeling_rule_options (from labelling_rules table) when there are no assets
    # yet, so the rule buttons always appear.
    if not rule_index_stats.empty:
        rule_summary = (
            rule_index_stats.groupby(["task_type", "rule_index"])
            .agg(
                completed_labels=("completed_labels", "sum"), samples=("samples", "sum")
            )
            .astype({"completed_labels": "int"})
            .reset_index()
            .merge(labeling_rule_options, on=["task_type", "rule_index"], how="left")
        )
    else:
        rule_summary = labeling_rule_options.assign(completed_labels=0, samples=0)
    sub_batch_stats = (
        asset_list.groupby(["task_type", "batch_id", "large_sub_batch", "rule_index"])
        .agg(
            completed_labels=("completed", "sum"),
            one_label=("one_label", "sum"),
            samples=("asset_id", "count"),
        )
        .astype({"completed_labels": "int"})
        .reset_index()
        .assign(no_labels=lambda x: x.samples - (x.completed_labels + x.one_label))
        .assign(
            percent_complete=lambda x: np.round(
                (x["completed_labels"] / x["samples"]) * 100, 2
            )
        )
        .assign(
            percent_remaining=lambda x: np.round(
                ((x["samples"] - x["completed_labels"]) / x["samples"]) * 100, 2
            )
        )
        .astype({"no_labels": "int", "one_label": "int"})
    )

    logger.debug(
        "_build_session_options: %d rules, %d sub-batches",
        len(rule_index_stats),
        len(sub_batch_stats),
    )

    data = {
        "task_types": task_types,
        "labeler_ids": labeler_ids,
        "batch_options": batch_options,
        "labeling_rule_options": labeling_rule_options.to_dict(orient="records"),
        "rule_summary": rule_summary.to_dict(orient="records"),
        "rule_index_stats": rule_index_stats.to_dict(orient="records"),
        "sub_batch_stats": sub_batch_stats.to_dict(orient="records"),
    }

    cache.set(cache_key, data, timeout=120)
    return data


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_session_options(request: Request) -> JsonResponse:
    """Build labeling UI options: task types, batches, rules, labelers, and completion stats.

    Args:
        request (Request): GET body/data. ``task_type`` (default ``asset_type``),
        ``labeller_source`` (default ``Internal``), ``remove_flagged_assets`` (default True).

    Returns:
        JsonResponse: ``task_types``, ``labeler_source``, ``labeler_ids``, ``batch_options``,
        ``labeling_rule_options``, ``rule_index_stats``, ``sub_batch_stats``.

    Frontend:
        ``image_labeler.label_images.views.setup_session`` → ``setup_session.html`` (batch/rule/labeler
        menus and progress stats before labeling).
    """
    task_type = str(request.data.get("task_type", "asset_type"))
    labeler_source = str(request.data.get("labeller_source", "Internal"))
    remove_flagged_assets = request.data.get("remove_flagged_assets", True)

    data = _build_session_options(task_type, remove_flagged_assets)
    data = {**data, "labeler_source": labeler_source}
    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def add_a_rule(request: Request) -> JsonResponse:
    """Placeholder endpoint for adding rules; currently returns an empty result.

    Args:
        request (Request): POST body. ``rule`` (list of rule dicts; first element must include ``task_type``).

    Returns:
        JsonResponse: Empty ``result`` object (implementation unfinished; dead code follows ``return``).

    Frontend:
        ``manage_rules.html`` / ``components/add_a_rule.html`` calls ``add_a_rule()`` in
        ``static/js/manage_rules.js``; server route is not fully implemented yet.
    """

    rule = request.data.get("rule", None)

    task_type = rule[0]["task_type"]

    temp = labelling_rules.objects.filter(task_type=task_type)
    logger.debug(temp.values())

    # for directive in rule:
    #     print(directive)

    #     entry = labelling_rules.objects.get(task_type = directive['task_type'],
    #                                         )

    #     print(entry)

    result = {}

    return JsonResponse(result, safe=False)

    labeled_assets = pd.DataFrame(
        list(
            prompt_responses.objects.filter(
                task_type=task_type, rule_index=rule_index
            ).values("asset_id", "prompt_response")
        )
    )

    asset_to_batch = pd.DataFrame(
        label_data_selected_assets_new.objects.values(
            "asset_id", "large_sub_batch", "batch_id", "image_link", "color_type"
        )
    )

    assets_w_labels = (
        labeled_assets.assign(
            yes_response=lambda x: np.where(x["prompt_response"] == "yes", 1, 0)
        )
        .groupby(["asset_id"])
        .agg(
            samples=("prompt_response", "count"), yes_responses=("yes_response", "sum")
        )
        .assign(no_responses=lambda x: x.samples - x.yes_responses)
        .assign(percent_agree=lambda x: x.yes_responses / x.samples)
        .assign(
            agree_status=lambda x: np.where(
                x["percent_agree"] != 0.5, "agree", "disagree"
            )
        )
        .assign(
            agree_status=lambda x: np.where(
                (x["percent_agree"] == 1.0) | (x["percent_agree"] == 0.0),
                "strongly_agree",
                x["agree_status"],
            )
        )
        .assign(
            agree_status=lambda x: np.where(
                x["samples"] == 1, "indeterminate", x["agree_status"]
            )
        )
        .assign(label="indeterminate")
        .assign(label=lambda x: np.where(x["percent_agree"] < 0.5, "no", x["label"]))
        .assign(
            label=lambda x: np.where(
                (x["percent_agree"] > 0.5) & (x["label"] != "no"), "yes", x["label"]
            )
        )
    )

    # replace incorrect labels with correct ones
    assets_w_labels = (
        assets_w_labels.merge(corrected_labels, on="asset_id", how="left")
        .assign(
            label=lambda x: np.where(
                pd.isna(x["modified_prompt_response"]),
                x["label"],
                x["modified_prompt_response"],
            )
        )
        .assign(
            agree_status=lambda x: np.where(
                pd.isna(x["modified_prompt_response"]),
                x["agree_status"],
                "potentially_corrected",
            )
        )
        .sort_values("modified_prompt_response")
    )


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_predictions(request: Request) -> JsonResponse:
    """Compare manual rule labels to model predictions (mismatch filtering) with batch counts.

    Args:
        request (Request): GET body/data. ``task_type``, ``rule_index``, optional ``batch_index``,
        ``label_type`` (``mismatch``, ``only_no``, ``only_yes``).

    Returns:
        JsonResponse: ``batch_counts`` and ``prediction_data`` rows with manual vs model labels.

    Frontend:
        ``image_labeler.label_images.views.view_prediction_labels`` → ``view_prediction_labels.html``.
    """

    task_type = request.data.get("task_type", "asset_type")
    rule_index = request.data.get("rule_index", 1)
    batch_index = request.data.get("batch_index", None)
    label_type = request.data.get("label_type", "mismatch")

    ######################

    image_links = pd.DataFrame(
        label_data_selected_assets_new.objects.values("asset_id", "image_link")
    )

    batch_ids = pd.DataFrame(
        label_data_selected_assets_new.objects.values("asset_id", "batch_id")
    )

    ######################
    corrected_labels = pd.DataFrame(
        list(
            modified_prompt_table.objects.filter(
                task_type=task_type, rule_index=rule_index
            ).values("asset_id", "modified_prompt_response")
        )
    )

    ######################
    # get assets with manual labels. filter for batch id

    asset_w_rule_labels = pd.DataFrame(
        assets_w_rule_labels.objects.filter(
            task_type=task_type, rule_index=rule_index
        ).values("asset_id", "task_type", "rule_index", "label")
    )

    ######################

    batch_counts = (
        asset_w_rule_labels.merge(batch_ids, on="asset_id", how="left")
        .assign(label=lambda x: np.where(x["label"] == 0, "no", "yes"))
        .groupby(["batch_id", "label"])
        .agg(count=("asset_id", "count"))
        .reset_index()
        .assign(batch_id=lambda x: (x["batch_id"]).astype(int))
        .pivot(index="batch_id", columns="label", values="count")
        .reset_index()
    )

    logger.debug("----batch_counts----")
    logger.debug(batch_counts)

    ######################

    if batch_index is not None:
        asset_w_rule_labels = asset_w_rule_labels.merge(
            batch_ids, on="asset_id", how="left"
        ).query("batch_id == @batch_index")

    logger.debug("-----assets_w_rule_labels-------")
    logger.debug(asset_w_rule_labels)

    # check that we have manual labels
    if len(asset_w_rule_labels) > 0:

        ######################

        # need a list of relevant assets ids to reduce the number of entires being pulled from large database table
        asset_ids = asset_w_rule_labels["asset_id"].unique().tolist()

        ######################

        predictions = pd.DataFrame(
            list(
                model_rule_label_predictions.objects.filter(
                    asset_id__in=asset_ids
                ).values("asset_id", "task_type", "rule_index", "probability", "label")
            )
        )

        ######################

        assets_w_label_issues = pd.DataFrame(
            label_issues_table.objects.values(
                "asset_id", "task_type", "rule_index", "issue_status"
            )
        )

        assets_w_label_issues = (
            assets_w_label_issues.query('issue_status == "active"')
            .assign(label_issue="yes")
            .filter(["asset_id", "label_issue"])
            .drop_duplicates()
        )

        ######################

        logger.debug("-----predictions-------")
        logger.debug(predictions)
        logger.debug(len(predictions))

        # connect probability score and model with assets that have a manual label
        prediction_data = (
            predictions.query("task_type == @task_type")
            .query("rule_index == @rule_index")
            .rename(columns={"label": "model_label"})
            .merge(assets_w_label_issues, on="asset_id", how="left")
            .merge(
                asset_w_rule_labels,
                on=["asset_id", "task_type", "rule_index"],
                how="left",
            )
            .merge(image_links, on="asset_id", how="left")
            .fillna("---")
        )

        logger.debug("-----prediction_data-------")
        logger.debug(prediction_data)

        prediction_data = (
            prediction_data.assign(
                model_label=lambda x: np.where(x["model_label"] == 1, "yes", "no")
            )
            .assign(manual_label=lambda x: np.where(x["label"] == 1, "yes", "no"))
            .assign(
                label_match=lambda x: np.where(
                    x["manual_label"] == x["model_label"], "yes", "no"
                )
            )
            .query('label_issue != "yes"')
        )
        # replace with corrected label from modified label table
        if len(corrected_labels) > 0:

            prediction_data = (
                prediction_data.merge(corrected_labels, on="asset_id", how="left")
                .assign(
                    manual_label=lambda x: np.where(
                        pd.isna(x["modified_prompt_response"]),
                        x["manual_label"],
                        x["modified_prompt_response"],
                    )
                )
                .assign(
                    correction_status=lambda x: np.where(
                        pd.isna(x["modified_prompt_response"]),
                        "not_corrected",
                        "potentially_corrected",
                    )
                )
            )

        prediction_data = prediction_data.filter(
            [
                "asset_id",
                "model_label",
                "manual_label",
                "label_match",
                "correction_status",
                "probability",
                "image_link",
            ]
        )

        # filter to the type manual label --> default to mismatch when no option is selected
        if label_type == "only_no":
            prediction_data = prediction_data.query('manual_label == "no"')
        elif label_type == "only_yes":
            prediction_data = prediction_data.query('manual_label == "yes"')
        else:
            prediction_data = prediction_data.query('label_match == "no"')

        logger.debug("----prediction_data-----")
        logger.debug(prediction_data)

    else:
        prediction_data = pd.DataFrame()

    data = {
        "batch_counts": batch_counts.to_dict(orient="records"),
        "prediction_data": prediction_data.to_dict(orient="records"),
    }

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def collect_label_issue(request: Request) -> JsonResponse:
    """Record an active label issue (wrong label) for an asset and rule.

    Args:
        request (Request): POST body. ``asset_id``, ``task_type``, ``rule_index``, ``labeler_id``.

    Returns:
        JsonResponse: ``status`` and ``explanation`` after insert into ``label_issues_table``.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (flag wrong label), ``label_content.html`` and
        related review templates.
    """

    asset_id = request.data.get("asset_id", None)
    task_type = request.data.get("task_type", "asset_type")
    rule_index = request.data.get("rule_index", 1)
    labeler_id = request.data.get("labeler_id", "Steve")

    datetime_created = timezone.localtime(
        timezone.now(), pytz.timezone("America/Chicago")
    ).strftime("%Y-%m-%d %H:%M:%S")

    entry = label_issues_table(
        datetime_created=datetime_created,
        asset_id=asset_id,
        task_type=task_type,
        rule_index=rule_index,
        labeler_id=labeler_id,
        issue_type="wrong label",
        issue_status="active",
    )

    entry.save()

    result = {
        "status": "success",
        "explanation": "recorded label issue for asset " + str(asset_id),
    }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_asset_labels(request: Request) -> JsonResponse:
    """Return consolidated metadata, prompts, rule labels, and issues for one asset.

    Args:
        request (Request): GET body/data. ``asset_id``.

    Returns:
        JsonResponse: ``asset_metadata``, ``asset_data``, ``prompt_responses``, ``rule_labels``,
        ``label_issues``.

    Frontend:
        ``view_asset_labels`` → ``view_asset_labels.html``; ``view_asset`` → ``view_asset.html``
        (single-asset drill-down).
    """

    asset_id = request.data.get("asset_id", None)

    asset_metadata = pd.DataFrame(
        content_asset_table.objects.filter(asset_id=asset_id).values(
            "asset_id", "page_title", "tags", "page_link"
        )
    )

    logger.debug(asset_metadata)

    selected_assets_new = pd.DataFrame(
        label_data_selected_assets_new.objects.filter(asset_id=asset_id).values(
            "asset_id", "large_sub_batch", "asset_type", "color_type", "image_link"
        )
    )

    asset_responses = pd.DataFrame(
        prompt_responses.objects.filter(asset_id=asset_id).values(
            "asset_id", "task_type", "rule_index", "labeler_id", "prompt_response"
        )
    )

    if len(asset_responses) > 0:
        asset_responses = (
            asset_responses.groupby(
                ["asset_id", "task_type", "rule_index", "prompt_response"]
            )
            .agg(count=("prompt_response", "count"))
            .reset_index()
            .pivot(
                index=["asset_id", "task_type", "rule_index"],
                columns="prompt_response",
                values="count",
            )
            .fillna(0)
            .reset_index()
        )

        logger.debug("-----Before------")
        logger.debug(asset_responses)

        for col in ["yes", "no"]:
            if col not in asset_responses.columns:
                asset_responses[col] = 0

        asset_responses[["yes", "no"]] = asset_responses[["yes", "no"]].astype(int)

    asset_rule_labels = pd.DataFrame(
        assets_w_rule_labels.objects.filter(asset_id=asset_id).values(
            "asset_id", "task_type", "rule_index", "label", "label_strength"
        )
    )

    asset_label_issues = pd.DataFrame(
        label_issues_table.objects.filter(asset_id=asset_id).values(
            "asset_id", "task_type", "rule_index", "issue_status"
        )
    )

    asset_model_label = pd.DataFrame(
        model_rule_label_predictions.objects.filter(asset_id=asset_id).values(
            "asset_id", "task_type", "rule_index", "probability", "label"
        )
    )

    asset_model_label = asset_model_label.filter(
        ["asset_id", "task_type", "rule_index", "label"]
    ).rename(columns={"label": "model_label"})

    if len(asset_rule_labels) > 0:

        asset_rule_labels = (
            asset_rule_labels.merge(
                asset_model_label,
                on=["asset_id", "task_type", "rule_index"],
                how="left",
            )
            .fillna("---")
            .assign(
                model_label=lambda x: np.where(
                    x.model_label == 0.0, "no", x.model_label
                )
            )
            .assign(
                model_label=lambda x: np.where(
                    x.model_label == 1.0, "yes", x.model_label
                )
            )
            .assign(label=lambda x: np.where(x.label == 0, "no", x.label))
            .assign(label=lambda x: np.where(x.label == "1", "yes", x.label))
            .assign(match=lambda x: np.where(x.label == x.model_label, "yes", "no"))
            .assign(match=lambda x: np.where(x.model_label == "---", "---", x.match))
        )
    data = {
        "asset_metadata": asset_metadata.to_dict(orient="records"),
        "asset_data": selected_assets_new.to_dict(orient="records"),
        "prompt_responses": asset_responses.to_dict(orient="records"),
        "rule_labels": asset_rule_labels.to_dict(orient="records"),
        "label_issues": asset_label_issues.to_dict(orient="records"),
    }

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_assets_w_label_issues(request: Request) -> JsonResponse:
    """List assets with open label issues for a task/rule, enriched for review UI.

    Args:
        request (Request): GET body/data. ``task_type``, ``rule_index``.

    Returns:
        JsonResponse: ``assets`` list with image links and nested rule summaries.

    Frontend:
        ``image_labeler.label_images.views.view_label_issues`` → ``view_label_issues.html``.
    """

    task_type = request.data.get("task_type", "asset_type")
    rule_index = request.data.get("rule_index", 1)

    issue_table = (
        pd.DataFrame(list(label_issues_table.objects.values()))
        .filter(["asset_id", "task_type", "rule_index"])
        .query("task_type == @task_type")
        .query("rule_index == @rule_index")
        .drop_duplicates()
    )

    asset_type_labels = pd.DataFrame(
        asset_type_table.objects.filter(
            asset_id__in=issue_table["asset_id"].unique().tolist()
        ).values("asset_id", "asset_type", "source")
    ).rename(columns={"source": "asset_type_source"})

    color_type_labels = pd.DataFrame(
        color_type_table.objects.filter(
            asset_id__in=issue_table["asset_id"].unique().tolist()
        ).values("asset_id", "color_type", "source")
    ).rename(columns={"source": "color_type_source"})

    manual_rule_labels = pd.DataFrame(
        assets_w_rule_labels.objects.filter(
            asset_id__in=issue_table["asset_id"].unique().tolist()
        ).values("asset_id", "task_type", "rule_index", "label")
    ).rename(columns={"label": "manual_label"})

    # print('-------manual_rule_labels--------')
    # print(manual_rule_labels)

    model_rule_labels = pd.DataFrame(
        model_rule_label_predictions.objects.filter(
            asset_id__in=issue_table["asset_id"].unique().tolist()
        ).values("asset_id", "task_type", "rule_index", "label")
    ).rename(columns={"label": "model_label"})

    # print('-------model_rule_labels--------')
    # print(model_rule_labels)

    image_links = pd.DataFrame(
        list(label_data_selected_assets_new.objects.values())
    ).filter(["asset_id", "image_link"])

    label_rules = pd.DataFrame(labelling_rules.objects.values()).filter(
        ["task_type", "rule_index", "title"]
    )

    #############################

    issue_counts = (
        issue_table.groupby(["task_type", "rule_index"])
        .agg(count=("asset_id", "count"))
        .reset_index()
    )

    #############################

    asset_rule_labels = (
        model_rule_labels.merge(
            manual_rule_labels, on=["asset_id", "task_type", "rule_index"], how="left"
        )
        .assign(
            label=lambda x: np.where(
                x["manual_label"].isna(), x["model_label"], x["manual_label"]
            )
        )
        .assign(
            label_source=lambda x: np.where(x["manual_label"].isna(), "model", "manual")
        )
        .assign(label=lambda x: np.where(x["label"] == 0, "no", "yes"))
        .drop(["manual_label", "model_label"], axis=1)
    )

    # print('-------asset_rule_labels--------')
    # print(asset_rule_labels)

    clip_art_type_rule_labels = (
        asset_rule_labels.merge(label_rules, on=["task_type", "rule_index"], how="left")
        .query('task_type == "asset_type"')
        .query("rule_index in [3,5,6,7]")
        .groupby(["asset_id"])[["rule_index", "title", "label", "label_source"]]
        .apply(lambda x: x.to_dict(orient="records"))
        .reset_index(name="clip_art_rules")
    )

    # print('-------clip_art_type_rule_labels--------')
    # print(clip_art_type_rule_labels)

    color_type_rule_labels = (
        asset_rule_labels.merge(label_rules, on=["task_type", "rule_index"], how="left")
        .query('task_type == "clip_art_type"')
        .query("rule_index in [1]")
        .groupby(["asset_id"])[["rule_index", "title", "label", "label_source"]]
        .apply(lambda x: x.to_dict(orient="records"))
        .reset_index(name="color_type_rules")
    )

    # print('-------color_type_rule_labels--------')
    # print(color_type_rule_labels)

    selected_assets_new_w_issues = (
        issue_table.filter(["asset_id", "task_type", "rule_index"])
        .merge(image_links, on="asset_id", how="left")
        .merge(asset_type_labels, on="asset_id", how="left")
        .merge(color_type_labels, on="asset_id", how="left")
    )

    assets_for_review = selected_assets_new_w_issues.merge(
        clip_art_type_rule_labels, on="asset_id", how="left"
    ).merge(color_type_rule_labels, on="asset_id", how="left")

    # print('-------assets_for_review--------')
    # print(assets_for_review)

    # model_labels = pd.DataFrame(list(model_asset_type_label_predictions.objects.values())) \
    #     .filter(['asset_id','asset_type'])  \
    #     .rename(columns = {'asset_type':'model_asset_type'})

    # manual_labels = pd.DataFrame(list(label_data_selected_assets_new.objects.values()))  \
    #     .filter(['asset_id','asset_type', 'color_type'])  \
    #     .rename(columns = {'asset_type':'manual_asset_type',
    #                        'color_type':'manual_color_type'})

    # issue_table = issue_table \
    # .merge(model_labels, how = 'left', on = 'asset_id') \
    # .merge(manual_labels, how = 'left', on = 'asset_id') \
    # .assign(asset_type = lambda x: np.where(x.manual_asset_type == 'undetermined',x.model_asset_type,x.manual_asset_type)) \
    # .merge(image_links, how = 'left', on = 'asset_id')

    # print(issue_table)

    data = {"assets": assets_for_review.to_dict(orient="records")}
    # data = {'temp': temp.to_dict(orient = 'records')}
    # data = {"issue_table":issue_table.to_dict(orient = 'records')}

    # data = {}

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_label_testing_options(request: Request) -> JsonResponse:
    """Return nested label-testing experiments, batches, and directives for a session.

    Args:
        request (Request): GET body/data. ``session_id`` (default 1).

    Returns:
        JsonResponse: ``data`` list of experiment dicts with ``batches`` and ``directives``.

    Frontend:
        ``image_labeler.label_images.views.label_testing`` → ``label_testing.html`` (session id
        hard-coded to 2 in the Django view today).
    """

    session_id = request.data.get("session_id", 1)

    session = pd.DataFrame(
        list(label_testing_session.objects.filter(id=session_id).values())
    )

    experiments = pd.DataFrame(
        list(label_testing_experiments.objects.filter(session_id=session_id).values())
    )

    batch = pd.DataFrame(
        list(label_testing_batches.objects.filter(session_id=session_id).values())
    )

    directives = pd.DataFrame(
        list(label_testing_directives.objects.filter(session_id=session_id).values())
    )

    asset_links = pd.DataFrame(
        list(label_data_selected_assets_new.objects.values())
    ).filter(["asset_id", "image_link"])

    batch = batch.merge(asset_links, on="asset_id", how="left")

    nested_data = []

    for _, experiment in experiments.iterrows():

        # compute label counts
        label_counts = (
            batch.query('batch_id == @experiment["batch_id"]')
            .groupby(["label"])
            .agg(count=("asset_id", "count"))
            .reset_index()
        )

        label_counts = label_counts.set_index("label")["count"]

        no_count = label_counts.get("no", 0)
        yes_count = label_counts.get("yes", 0)
        total_count = no_count + yes_count

        images = batch.query('batch_id == @experiment["batch_id"]').to_dict(
            orient="records"
        )

        # add meta data, restructure hiearchy
        experiment_batches = {
            "total_count": int(total_count),
            "yes_count": int(yes_count),
            "no_count": int(no_count),
            "images": images,
        }

        experiment_directives = directives.query(
            'directive_id == @experiment["directive_id"]'
        ).to_dict(orient="records")

        nested_data.append(
            {
                **experiment.to_dict(),
                "batches": experiment_batches,
                "directives": experiment_directives,
            }
        )

    data = {"data": nested_data}

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def create_experiment(request: Request) -> JsonResponse:
    """Create a label-testing experiment row linking session, batch, and directive.

    Args:
        request (Request): POST body. ``session_id``, ``batch_id``, ``directive_id``.

    Returns:
        JsonResponse: ``status`` and ``explanation``.

    Frontend:
        No ``image_labeler`` caller found in-repo; used to register experiments for label-testing UI.
    """

    session_id = request.data.get("session_id", None)
    batch_id = request.data.get("batch_id", None)
    directive_id = request.data.get("directive_id", None)

    new_entry = label_testing_experiments(
        session_id=session_id, batch_id=batch_id, directive_id=directive_id
    )

    new_entry.save()

    result = {"status": "success", "explanation": "created a new experiment"}

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_model_results(request: Request) -> JsonResponse:
    """Return training/validation metrics for all model runs, marked production vs development.

    Args:
        request (Request): GET; no request fields used.

    Returns:
        JsonResponse: ``model_results`` list of metric rows.

    Frontend:
        ``image_labeler.label_images.views.view_model_results`` → ``view_model_results.html``.
    """

    production_models = pd.DataFrame(list(production_models_table.objects.values()))
    model_results = pd.DataFrame(list(model_results_table.objects.values()))

    production_models = production_models.assign(status="production").filter(
        ["dev_id", "status"]
    )

    model_results = (
        model_results.merge(
            production_models, left_on="id", right_on="dev_id", how="left"
        )
        .assign(learning_rate=lambda x: np.round(x.learning_rate, 3))
        .assign(val_loss=lambda x: np.round(x.val_loss, 3))
        .assign(val_accuracy=lambda x: np.round(x.val_accuracy, 3))
        .assign(val_recall=lambda x: np.round(x.val_recall, 3))
        .assign(val_precision=lambda x: np.round(x.val_precision, 3))
        .assign(val_auc=lambda x: np.round(x.val_auc, 3))
        .assign(total_samples=lambda x: x.train_samples + x.val_samples)
        .assign(
            score=lambda x: np.round(
                (x.val_precision + x.val_recall) - abs(x.val_precision - x.val_recall),
                3,
            )
        )
        .assign(val_mae=lambda x: np.round(x.val_mae, 3))
    )

    model_results["status"] = model_results["status"].fillna("development")

    logger.debug(model_results)
    logger.debug(model_results.columns)

    data = {"model_results": model_results.to_dict(orient="records")}

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_dark_ratios(request: Request) -> JsonResponse:
    """Return ray-traced dark-ratio metrics per asset.

    Args:
        request (Request): GET; no request fields used.

    Returns:
        JsonResponse: List of ``asset_id``, ``dark_ratio``, ``dark_label`` records.

    Frontend:
        ``image_labeler.label_images.views.view_labels`` → ``view_labels.html`` (merged with rule
        labels for sorting/filtering).
    """

    ray_trace_table = pd.DataFrame(list(ray_trace_mask_table.objects.values()))
    data = ray_trace_table.filter(["asset_id", "dark_ratio", "dark_label"]).to_dict(
        orient="records"
    )

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def collect_modified_prompt(request: Request) -> JsonResponse:
    """Insert a corrected prompt response override for an asset and rule.

    Args:
        request (Request): POST body. ``asset_id``, ``labeler_source``, ``labeler_id``, ``task_type``,
        ``rule_index``, ``modified_prompt_response``.

    Returns:
        JsonResponse: ``status`` and ``explanation``.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (save correction), ``label_content.html`` flows.
    """

    asset_id = request.data.get("asset_id", None)
    labeler_source = request.data.get("labeler_source", None)
    labeler_id = request.data.get("labeler_id", None)
    task_type = request.data.get("task_type", None)
    rule_index = request.data.get("rule_index", None)
    modified_prompt_response = request.data.get("modified_prompt_response", None)

    new_entry = modified_prompt_table(
        date_time_created=timezone.now(),
        asset_id=asset_id,
        labeler_source=labeler_source,
        labeler_id=labeler_id,
        task_type=task_type,
        rule_index=rule_index,
        modified_prompt_response=modified_prompt_response,
    )

    new_entry.save()

    result = {
        "status": "success",
        "explanation": "added prompt for asset " + str(asset_id),
    }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def remove_modified_prompt(request: Request) -> JsonResponse:
    """Delete a modified-prompt row matching asset, task type, and rule index.

    Args:
        request (Request): POST body. ``asset_id``, ``task_type``, ``rule_index``.

    Returns:
        JsonResponse: ``status`` and ``explanation`` (success or not found).

    Frontend:
        ``image_labeler.static.js.api_calls.js``, correction undo in labeling UI.
    """

    logger.debug(request.data)

    try:

        logger.debug(request.data.get("asset_id", None))
        logger.debug(request.data.get("task_type", None))
        logger.debug(request.data.get("rule_index", None))

        entry = modified_prompt_table.objects.get(
            asset_id=request.data.get("asset_id", None),
            task_type=request.data.get("task_type", None),
            rule_index=request.data.get("rule_index", None),
        )

        entry.delete()

        result = {
            "status": "success",
            "explanation": "removed modifed prompt for asset "
            + str(request.data.get("asset_id", None)),
        }

    except:
        result = {"status": "failed", "explanation": "unable to find the entry"}

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_primary_colors(request: Request) -> JsonResponse:
    """Return primary color clusters per asset with normalized scores and image links.

    Args:
        request (Request): GET; no request fields used.

    Returns:
        JsonResponse: ``assets`` list with nested ``primary_colors`` arrays.

    Frontend:
        ``image_labeler.label_images.views.view_primary_colors`` → ``view_primary_colors.html``.
    """

    selected_assets_new = pd.DataFrame(
        label_data_selected_assets_new.objects.values("asset_id", "image_link")
    )

    primary_colors = (
        pd.DataFrame(list(primary_colors_table.objects.values()))
        .drop(columns=["date_time_created", "id"])
        .merge(selected_assets_new, on="asset_id", how="left")
        .dropna()
    )

    primary_colors["normalized_score"] = np.round(
        primary_colors["score"] / np.max(primary_colors["score"]), 3
    )

    asset_primary_colors = (
        primary_colors.groupby(["asset_id", "image_link"])
        .apply(
            lambda x: x[
                [
                    "r",
                    "g",
                    "b",
                    "score",
                    "normalized_score",
                    "proportion_prominent_color",
                    "proportion_to_all_pixels",
                ]
            ].to_dict("records")
        )
        .reset_index(name="primary_colors")
    )

    data = {"assets": asset_primary_colors.to_dict(orient="records")}

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def collect_line_width_sample(request: Request) -> JsonResponse:
    """Save one line-width sample point for an asset.

    Args:
        request (Request): POST body. ``asset_id``, ``sample_index``, ``x_coord``, ``y_coord``,
        ``radius``, ``image_width``, ``image_height``, ``labeler_id``.

    Returns:
        JsonResponse: ``status`` and ``explanation``.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (line-width sampling), ``select_line_widths.html`` /
        line-width labeling UI.
    """

    entry = line_width_sample_table(
        asset_id=request.data.get("asset_id", None),
        sample_index=request.data.get("sample_index", None),
        x_coord=request.data.get("x_coord", None),
        y_coord=request.data.get("y_coord", None),
        radius=request.data.get("radius", None),
        image_width=request.data.get("image_width", None),
        image_height=request.data.get("image_height", None),
        labeler_id=request.data.get("labeler_id", None),
        status="valid",
    )

    entry.save()

    result = {
        "status": "success",
        "explanation": "recorded line width sample for asset "
        + str(request.data.get("asset_id", None)),
    }

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def remove_line_width_sample(request: Request) -> JsonResponse:
    """Delete one line-width sample by asset and sample index.

    Args:
        request (Request): POST body. ``asset_id``, ``sample_index``.

    Returns:
        JsonResponse: ``status`` and ``explanation``.

    Frontend:
        ``image_labeler.static.js.api_calls.js``, line-width UI undo.
    """

    try:
        entry = line_width_sample_table.objects.get(
            asset_id=request.data.get("asset_id", None),
            sample_index=request.data.get("sample_index", None),
        )

        entry.delete()

        result = {
            "status": "success",
            "explanation": "removed line width sample for asset "
            + str(request.data.get("asset_id", None)),
        }

    except:
        result = {"status": "failed", "explanation": "unable to find the asset"}

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def label_line_width_as_invalid(request: Request) -> JsonResponse:
    """Clear samples for an asset/labeler and record an invalid line-width placeholder row.

    Args:
        request (Request): POST body. ``asset_id``, ``labeler_id``.

    Returns:
        JsonResponse: ``status`` and ``explanation``, or error text on failure.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (``label_line_width_as_invalid``), line-width task
        when an asset cannot be measured.
    """

    asset_id = request.data.get("asset_id")
    labeler_id = request.data.get("labeler_id")

    try:
        # Delete any existing matching entries
        line_width_sample_table.objects.filter(
            asset_id=asset_id, labeler_id=labeler_id
        ).delete()

        # Create invalid entry
        entry = line_width_sample_table(
            asset_id=asset_id,
            sample_index=None,
            x_coord=None,
            y_coord=None,
            radius=None,
            image_width=None,
            image_height=None,
            labeler_id=labeler_id,
            status="invalid",
        )
        entry.save()

        result = {
            "status": "success",
            "explanation": f"Labeled as invalid for asset {asset_id}",
        }

    except Exception as e:
        result = {"status": "failed", "explanation": f"Error: {str(e)}"}

    return JsonResponse(result)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_mismatched_labels(request: Request) -> JsonResponse:
    """Return manual vs model mismatches with optional corrected labels for a task/rule.

    Args:
        request (Request): GET body/data. ``task_type``, ``rule_index``.

    Returns:
        JsonResponse: ``mistmatched_labels`` list (key name retained for API compatibility).

    Frontend:
        ``image_labeler.label_images.views.correct_mismatch_labels`` → ``correct_mismatch_labels.html``.
    """

    task_type = request.data.get("task_type", None)
    rule_index = request.data.get("rule_index", None)

    image_links = pd.DataFrame(
        list(label_data_selected_assets_new.objects.values())
    ).filter(["asset_id", "image_link"])

    corrected_labels = (
        pd.DataFrame(list(modified_prompt_table.objects.values()))
        .query("task_type == @task_type")
        .query("rule_index == @rule_index")
        .rename(columns={"modified_prompt_response": "modified_label"})
        .filter(["asset_id", "modified_label"])
    )

    logger.debug(corrected_labels)

    mismatched_labels = (
        pd.DataFrame(list(mismatched_labels_table.objects.values()))
        .merge(image_links, on="asset_id", how="left")
        .merge(corrected_labels, on="asset_id", how="left")
        .fillna("no change")
        .query("task_type == @task_type")
        .query("rule_index == @rule_index")
    )

    data = {"mistmatched_labels": mismatched_labels.to_dict(orient="records")}

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def collect_mismatch_prompt(request: Request) -> JsonResponse:
    """Mark a mismatch row as reviewed.

    Args:
        request (Request): POST body. ``asset_id``, ``task_type``, ``rule_index``.

    Returns:
        JsonResponse: ``status`` and ``explanation``.

    Frontend:
        ``image_labeler.static.js.api_calls.js``, mismatch review on ``correct_mismatch_labels.html``.
    """

    try:
        entry = mismatched_labels_table.objects.get(
            asset_id=request.data.get("asset_id", None),
            task_type=request.data.get("task_type", None),
            rule_index=request.data.get("rule_index", None),
        )

        entry.status = "reviewed"
        entry.save()

        result = {
            "status": "success",
            "explanation": "updated mismatch status for asset "
            + str(request.data.get("asset_id", None)),
        }

    except:
        result = {"status": "failed", "explanation": "unable to find entry"}

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def reset_mismatch_prompt(request: Request) -> JsonResponse:
    """Reset a mismatch row status back to active for re-review.

    Args:
        request (Request): POST body. ``asset_id``, ``task_type``, ``rule_index``.

    Returns:
        JsonResponse: ``status`` and ``explanation``.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (re-open mismatch), ``correct_mismatch_labels.html``.
    """

    try:
        entry = mismatched_labels_table.objects.get(
            asset_id=request.data.get("asset_id", None),
            task_type=request.data.get("task_type", None),
            rule_index=request.data.get("rule_index", None),
        )

        entry.status = "active"
        entry.save()

        result = {
            "status": "success",
            "explanation": "updated mismatch status for asset "
            + str(request.data.get("asset_id", None)),
        }

    except:
        result = {"status": "failed", "explanation": "unable to find entry"}

    return JsonResponse(result, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_rough_fill_scores(request: Request) -> JsonResponse:
    """Return rough-fill heuristic scores joined to asset image links.

    Args:
        request (Request): GET; no request fields used.

    Returns:
        JsonResponse: ``rough_fill_scores`` list of merged records.

    Frontend:
        ``image_labeler.label_images.views.view_rough_fill`` → ``view_rough_fill.html``.
    """

    selected_assets_new = pd.DataFrame(
        list(label_data_selected_assets_new.objects.values("asset_id", "image_link"))
    )

    logger.debug("-----selected_assets_new------")
    logger.debug(selected_assets_new)

    rough_fill_scores = pd.DataFrame(
        list(rough_fill_score_table.objects.values())
    ).merge(selected_assets_new, on="asset_id", how="left")

    logger.debug("-----rough_fill_scores------")
    logger.debug(rough_fill_scores)

    data = {"rough_fill_scores": rough_fill_scores.to_dict(orient="records")}

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_line_widths(request: Request) -> JsonResponse:
    """Return line-width estimates with source, prominence, and image links.

    Args:
        request (Request): GET; no request fields used.

    Returns:
        JsonResponse: List of ``asset_id``, ``source``, ``image_link``, ``line_width``, ``prominence``.

    Frontend:
        ``image_labeler.label_images.views.view_line_widths`` → ``view_line_widths.html``.
    """

    selected_assets_new = pd.DataFrame(
        list(label_data_selected_assets_new.objects.values("asset_id", "image_link"))
    )

    line_widths = pd.DataFrame(list(line_width_table.objects.values())).merge(
        selected_assets_new, on="asset_id", how="left"
    )

    data = line_widths.filter(
        ["asset_id", "source", "image_link", "line_width", "prominence"]
    ).to_dict(orient="records")

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_search_results(request: Request) -> JsonResponse:
    """Text search then image-similarity ranking for listing discovery.

    Args:
        request (Request): GET body/data. ``search_string`` (default ``owl``),
        ``selected_result_index`` (int, default 0) into text results before image scoring.

    Returns:
        JsonResponse: ``status``, ``selected_image``, ``search_results``; or error payload if no
        valid titles, image load fails, etc.

    Frontend:
        ``image_labeler.label_images.views.label_search_results`` → ``label_search_results.html``
        (server-side fetch; similarity grid and reference image).
    """
    search_string = str(request.data.get("search_string", "owl"))
    selected_result_index = int(request.data.get("selected_result_index", 0))

    # Use text to get listings with same meaning (includes asset type like "clip art")
    text_scores = get_text_scores(search_string)

    # Filter to top 10 listings first to save time
    text_scores = text_scores[:20]

    # Filter text_scores to only include asset_ids that have a non-blank model_generated_title in extracted_features_table
    asset_ids_to_check = [s["asset_id"] for s in text_scores]
    logger.debug(
        f"[DEBUG] Checking {len(asset_ids_to_check)} asset_ids for model_generated_title"
    )

    try:
        # First check how many exist in the table
        existing_assets = set(
            extracted_features_table.objects.filter(
                asset_id__in=asset_ids_to_check
            ).values_list("asset_id", flat=True)
        )
        logger.debug(
            f"[DEBUG] Found {len(existing_assets)} asset_ids in extracted_features_table"
        )

        # Then check which have non-blank model_generated_title
        valid_asset_ids = set(
            extracted_features_table.objects.filter(asset_id__in=asset_ids_to_check)
            .exclude(model_generated_title__isnull=True)
            .exclude(model_generated_title="")
            .values_list("asset_id", flat=True)
        )
        logger.debug(
            f"[DEBUG] Found {len(valid_asset_ids)} asset_ids with non-blank model_generated_title"
        )

        # Debug: Check a sample of model_generated_title values
        if len(existing_assets) > 0:
            sample_assets = list(existing_assets)[:3]
            sample_titles = extracted_features_table.objects.filter(
                asset_id__in=sample_assets
            ).values("asset_id", "model_generated_title")
            logger.debug(
                f"[DEBUG] Sample model_generated_title values: {list(sample_titles)}"
            )
    except (ProgrammingError, OperationalError) as exc:
        logger.debug(
            f"[WARN] content.extracted_features unavailable ({exc}); "
            "skipping model_generated_title filter."
        )
        existing_assets = set()
        valid_asset_ids = {int(s["asset_id"]) for s in text_scores}

    # Debug: Check types and matching before filtering
    text_scores_asset_ids = [s["asset_id"] for s in text_scores]
    logger.debug(f"[DEBUG] text_scores has {len(text_scores)} items before filtering")
    logger.debug(
        f"[DEBUG] Sample text_scores asset_ids (first 3): {text_scores_asset_ids[:3]}"
    )
    logger.debug(
        f"[DEBUG] Sample valid_asset_ids (first 3): {list(valid_asset_ids)[:3]}"
    )
    logger.debug(
        f"[DEBUG] Type of text_scores asset_id: {type(text_scores_asset_ids[0]) if text_scores_asset_ids else 'N/A'}"
    )
    logger.debug(
        f"[DEBUG] Type of valid_asset_ids element: {type(list(valid_asset_ids)[0]) if valid_asset_ids else 'N/A'}"
    )

    # Ensure type consistency for comparison (convert both to same type)
    valid_asset_ids = {int(asset_id) for asset_id in valid_asset_ids}
    text_scores = [s for s in text_scores if int(s["asset_id"]) in valid_asset_ids]
    logger.debug(f"[DEBUG] text_scores has {len(text_scores)} items after filtering")

    # Check if we have any valid results after filtering
    if len(text_scores) == 0:
        return JsonResponse(
            {
                "status": "error",
                "message": "No search results found with valid model_generated_title",
                "search_results": [],
            },
            safe=False,
        )

    # Ensure selected_result_index is within bounds after filtering
    if selected_result_index >= len(text_scores):
        selected_result_index = len(text_scores) - 1
        logger.debug(
            f"[DEBUG] Adjusted selected_result_index to {selected_result_index} (filtered list has {len(text_scores)} items)"
        )

    # Debug: Log the search query and top results
    if len(text_scores) > 0:
        logger.debug(f"[DEBUG] Search query: '{search_string}'")
        logger.debug(
            f"[DEBUG] Top 5 text search results (asset_ids): {[s['asset_id'] for s in text_scores[:5]]}"
        )
        logger.debug(
            f"[DEBUG] Selected result index: {selected_result_index}, asset_id: {text_scores[selected_result_index]['asset_id']}"
        )

    selected_asset_id = text_scores[selected_result_index]["asset_id"]
    listing_data = get_asset_design_features([selected_asset_id])
    image_link = listing_data[0]["image_link"]

    logger.debug("-----listing_data------")
    logger.debug(listing_data)

    logger.debug("-----image_link------")
    logger.debug(image_link)

    # Load image and compute vector
    try:
        image = load_image(image_link)
        image_vector = get_image_vector(image)
    except Exception as e:
        # Update search_term_table status to 'failed_to_load'
        try:
            # Remove suffixes from search_string for matching
            cleaned_search_string = search_string
            suffixes_to_remove = ["Clip Art", "Line Art", "Outline", "Silhouette"]
            for suffix in suffixes_to_remove:
                if cleaned_search_string.endswith(suffix):
                    cleaned_search_string = cleaned_search_string[
                        : -len(suffix)
                    ].strip()

            search_term_entry = search_term_table.objects.filter(
                search_topic=cleaned_search_string,
                selected_index=selected_result_index,
                status="active",
            ).first()

            logger.debug("-----search_string------")
            logger.debug(search_string)
            logger.debug("-----cleaned_search_string------")
            logger.debug(cleaned_search_string)
            logger.debug("-----selected_result_index------")
            logger.debug(selected_result_index)

            logger.debug("-----search_term_entry------")
            logger.debug(search_term_entry)
            if search_term_entry:
                search_term_entry.status = "failed_to_load"
                search_term_entry.save()
        except Exception as update_error:
            # Log the error but don't fail the request
            logger.debug(f"Error updating search_term_table status: {update_error}")

        # Return error status if image cannot be loaded
        return JsonResponse(
            {
                "status": "error",
                "message": f"Failed to load image from {image_link}: {str(e)}",
                "selected_image": listing_data,
                "search_results": [],
            },
            safe=False,
        )

    # Get image similarity scores
    image_scores = get_image_scores(image_vector)

    # Limit number of returned listings for performance
    image_scores = image_scores[:100]
    selected_asset_ids = [asset["asset_id"] for asset in image_scores]

    # Fetch design features for search results
    search_results = get_asset_design_features(selected_asset_ids)

    # Merge and sort results
    search_results = (
        pd.DataFrame(search_results)
        .merge(pd.DataFrame(image_scores), on="asset_id", how="left")
        .sort_values(["score"], ascending=[False])
    )

    search_results_list = search_results.to_dict(orient="records")

    data = {
        "status": "success",
        "selected_image": listing_data,
        "search_results": search_results_list,
    }

    return JsonResponse(data, safe=False)


@csrf_exempt
@api_authorization
@api_view(["GET"])
def get_text_search_results(request: Request) -> JsonResponse:
    """Return raw text embedding similarity scores for a query string.

    Args:
        request (Request): GET body/data. ``search_string`` (default ``owl``).

    Returns:
        JsonResponse: List/dict from ``get_text_scores`` (embedding search hits).

    Frontend:
        No ``image_labeler`` template caller found in-repo; debugging/auxiliary text-search API
        (``get_search_results`` uses embeddings internally).
    """
    search_string = str(request.data.get("search_string", "owl"))

    text_scores = get_text_scores(search_string)

    return JsonResponse(text_scores, safe=False)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def get_search_term(request: Request) -> JsonResponse:
    """Return the next active search term in a batch that the labeler has not yet answered.

    Args:
        request (Request): POST body. ``batch_id``, ``labeler_id``.

    Returns:
        JsonResponse: Search term fields, or 404 JSON error if none remain.

    Frontend:
        ``label_search_results`` Django view may POST here when results are empty; also available to
        ``static/js/api_calls.js`` (search-term helpers) and ``label_search_result.js``.
    """
    batch_id = request.data.get("batch_id", None)
    labeler_id = request.data.get("labeler_id", None)

    logger.debug("-----batch_id------")
    logger.debug(batch_id)
    logger.debug("-----labeler_id------")
    logger.debug(labeler_id)

    labeler_responses = (
        search_term_responses_table.objects.filter(labeler_id=labeler_id)
        .values_list("term_table_id", flat=True)
        .distinct()
    )

    search_terms = search_term_table.objects.filter(
        status="active", batch_id=batch_id
    ).exclude(id__in=labeler_responses)
    logger.debug("-----search_terms------")
    logger.debug(pd.DataFrame(search_terms.values()))

    if search_terms.exists():
        search_term = search_terms.order_by("id").first()

        return JsonResponse(
            {
                "id": search_term.id,
                "search_topic_id": search_term.search_topic_id,
                "search_topic": search_term.search_topic,
                "asset_type": search_term.asset_type,
                "selected_index": search_term.selected_index,
                "status": search_term.status,
            },
            safe=False,
        )
    else:
        return JsonResponse({"error": "No active search terms found"}, status=404)


@csrf_exempt
@api_authorization
@api_view(["POST"])
def get_available_search_batches(request: Request) -> JsonResponse:
    """List batches with counts of remaining (unlabeled) search terms per labeler.

    Args:
        request (Request): POST body. ``labeler_id`` (required).

    Returns:
        JsonResponse: ``batches`` list with ``batch_id`` and ``search_terms_count``, or error JSON
        with HTTP 400/500 on validation or server failure.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (``api_get_available_search_batches``), search
        labeling batch picker UIs.
    """
    labeler_id = request.data.get("labeler_id", None)

    if not labeler_id:
        return JsonResponse(
            {"status": "failed", "explanation": "labeler_id is required"}, status=400
        )

    try:
        # Get all term_table_ids that have been labeled by this labeler
        labeled_term_table_ids = (
            search_term_responses_table.objects.filter(labeler_id=labeler_id)
            .values_list("term_table_id", flat=True)
            .distinct()
        )

        # Get all active search terms
        all_search_terms = pd.DataFrame(
            list(
                search_term_table.objects.filter(status="active").values(
                    "id", "batch_id"
                )
            )
        )

        if all_search_terms.empty:
            return JsonResponse({"batches": []}, safe=False)

        # Mark which terms have been labeled
        all_search_terms["is_labeled"] = all_search_terms["id"].isin(
            labeled_term_table_ids
        )

        # Get available (unlabeled) search terms
        available_search_terms = all_search_terms[~all_search_terms["is_labeled"]]

        # Get all unique batch_ids from all search terms
        all_batches = all_search_terms[["batch_id"]].drop_duplicates()

        # Count available search terms per batch
        available_counts = (
            available_search_terms.groupby("batch_id")
            .agg(search_terms_count=("id", "count"))
            .reset_index()
        )

        # Merge with all batches to include batches with 0 available terms
        batch_counts = (
            all_batches.merge(available_counts, on="batch_id", how="left")
            .fillna(0)  # Fill 0 for batches with no available terms
            .astype({"search_terms_count": "int64"})
            .sort_values("batch_id")
        )

        # Convert to list of dictionaries
        batches = batch_counts.to_dict(orient="records")

        return JsonResponse({"batches": batches}, safe=False)

    except Exception as e:
        return JsonResponse(
            {
                "status": "failed",
                "explanation": f"Error getting available search batches: {str(e)}",
            },
            status=500,
        )


@csrf_exempt
@api_authorization
@api_view(["POST"])
def update_search_result_response(request: Request) -> JsonResponse:
    """Update or create a ``search_term_responses_table`` row for a labeler's choice.

    Args:
        request (Request): POST body. ``id`` (``search_term_table`` id), ``labeler_id``,
        ``response``, ``selected_asset_id``, ``listing_asset_id``.

    Returns:
        JsonResponse: Success with update/create details, or error JSON with HTTP 400/404/500.

    Frontend:
        ``image_labeler.static.js.label_search_result.js`` (listing choice / agreement), paired with
        ``label_search_results.html``.
    """
    search_term_id = request.data.get("id", None)
    labeler_id = request.data.get("labeler_id", None)
    response = request.data.get("response", None)
    selected_asset_id = request.data.get("selected_asset_id", None)
    listing_asset_id = request.data.get("listing_asset_id", None)

    if not search_term_id:
        return JsonResponse(
            {
                "status": "failed",
                "explanation": "id (search_term_table id) is required",
            },
            status=400,
        )

    if not labeler_id:
        return JsonResponse(
            {"status": "failed", "explanation": "labeler_id is required"}, status=400
        )

    if response is None:
        return JsonResponse(
            {"status": "failed", "explanation": "response is required"}, status=400
        )

    try:
        # Fetch search_term_table entry using id
        try:
            search_term_entry = search_term_table.objects.get(id=search_term_id)
        except ObjectDoesNotExist:
            return JsonResponse(
                {
                    "status": "failed",
                    "explanation": f"search_term_table entry with id {search_term_id} not found",
                },
                status=404,
            )

        # Validate required fields for finding/creating entries
        if not selected_asset_id or not listing_asset_id:
            return JsonResponse(
                {
                    "status": "failed",
                    "explanation": "selected_asset_id and listing_asset_id are required",
                },
                status=400,
            )

        # Find entries matching term_table_id, labeler_id, selected_asset_id, and listing_asset_id
        existing_entries = search_term_responses_table.objects.filter(
            term_table_id=search_term_id,
            labeler_id=labeler_id,
            selected_asset_id=selected_asset_id,
            listing_asset_id=listing_asset_id,
        )

        if existing_entries.exists():
            # Update entries that have a different response
            updated_count = 0
            for entry in existing_entries:
                if entry.response != response:
                    entry.response = response
                    entry.status = "active"
                    entry.save()
                    updated_count += 1

            return JsonResponse(
                {
                    "status": "success",
                    "explanation": f"Updated {updated_count} entry/entries with new response",
                    "total_matching_entries": existing_entries.count(),
                    "updated_count": updated_count,
                },
                safe=False,
            )
        else:
            # No existing entries found - create new one
            # Create new entry using data from search_term_table
            new_entry = search_term_responses_table(
                datetime_created=timezone.now(),
                term_table_id=search_term_id,
                labeler_id=labeler_id,
                selected_asset_id=selected_asset_id,
                listing_asset_id=listing_asset_id,
                response=response,
                status="active",
            )
            new_entry.save()

            return JsonResponse(
                {
                    "status": "success",
                    "explanation": "Created new entry with response",
                    "id": new_entry.id,
                    "term_table_id": search_term_id,
                    "search_topic": search_term_entry.search_topic,
                    "selected_index": search_term_entry.selected_index,
                },
                safe=False,
            )

    except Exception as e:
        return JsonResponse(
            {
                "status": "failed",
                "explanation": f"Error updating search result response: {str(e)}",
            },
            status=500,
        )


@csrf_exempt
@api_authorization
@api_view(["POST"])
def update_search_term(request: Request) -> JsonResponse:
    """Update the status field on a ``search_term_table`` row.

    Args:
        request (Request): POST body. ``term_table_id`` (row id), ``status`` (new value).

    Returns:
        JsonResponse: Success payload with ``term_table_id`` and ``new_status``, or error JSON with
        HTTP 400/404/500.

    Frontend:
        ``image_labeler.static.js.api_calls.js`` (``api_update_search_term``), invoked from
        ``label_search_result.js`` when updating term status (e.g. invalid / completed) alongside
        ``label_search_results.html``.
    """
    try:
        term_table_id = request.data.get("term_table_id", None)
        status = request.data.get("status", None)

        if term_table_id is None:
            return JsonResponse(
                {"status": "failed", "explanation": "term_table_id is required"},
                status=400,
            )

        if status is None:
            return JsonResponse(
                {"status": "failed", "explanation": "status is required"}, status=400
            )

        # Find the entry by id (term_table_id)
        entry = search_term_table.objects.get(id=term_table_id)

        # Update the status
        entry.status = status
        entry.save()

        result = {
            "status": "success",
            "explanation": f"Updated status for search term {term_table_id} to {status}",
            "term_table_id": term_table_id,
            "new_status": status,
        }

        return JsonResponse(result, safe=False)

    except search_term_table.DoesNotExist:
        return JsonResponse(
            {
                "status": "failed",
                "explanation": f"Search term with id {term_table_id} not found",
            },
            status=404,
        )

    except Exception as e:
        return JsonResponse(
            {
                "status": "failed",
                "explanation": f"Error updating search term: {str(e)}",
            },
            status=500,
        )


# ---------------------------------------------------------------------------
# Sub-batch creation
# ---------------------------------------------------------------------------

BATCH_MAX_ASSETS = 20_000
SUB_BATCH_SIZE = 500


@csrf_exempt
@api_view(["GET"])
def get_sub_batch_options(request):
    """Return model versions and batch capacities for the sub-batch creation modal.

    Args:
        request: GET with ``task_type`` and ``rule_index`` query params.

    Returns:
        JSON with ``model_versions`` (list of str) and ``batch_capacities``
        (list of ``{batch_id, asset_count, has_room}``).

    Frontend:
        Called by ``setup_session.js`` when the user opens the add-sub-batch
        modal.  Populates the model-version dropdown and the target-batch
        selector.
    """
    task_type = request.GET.get("task_type")
    rule_index = request.GET.get("rule_index")

    if not task_type or rule_index is None:
        return JsonResponse(
            {
                "status": "failed",
                "explanation": "task_type and rule_index are required",
            },
            status=400,
        )

    try:
        rule_index = int(rule_index)
    except (TypeError, ValueError):
        return JsonResponse(
            {"status": "failed", "explanation": "rule_index must be an integer"},
            status=400,
        )

    try:
        _prod_db = "prod" if "prod" in settings.DATABASES else "default"
        model_versions = list(
            model_rule_label_predictions_versioned.objects.using(_prod_db)
            .filter(task_type=task_type, rule_index=rule_index)
            .values_list("model_version", flat=True)
            .distinct()
            .order_by("model_version")
        )

        batch_counts_qs = (
            label_data_selected_assets_new.objects.filter(
                task_type=task_type, rule_index=rule_index
            )
            .values("batch_id")
            .annotate(asset_count=Count("asset_id"))
            .order_by("batch_id")
        )

        batch_capacities = [
            {
                "batch_id": row["batch_id"],
                "asset_count": row["asset_count"],
                "has_room": row["asset_count"] + SUB_BATCH_SIZE <= BATCH_MAX_ASSETS,
            }
            for row in batch_counts_qs
        ]

        return JsonResponse(
            {
                "status": "success",
                "model_versions": model_versions,
                "batch_capacities": batch_capacities,
            }
        )

    except Exception as e:
        logger.exception("get_sub_batch_options error")
        return JsonResponse({"status": "failed", "explanation": str(e)}, status=500)


@csrf_exempt
@api_view(["POST"])
def create_sub_batch(request):
    """Add a new large_sub_batch of 500 assets to an existing batch.

    Args:
        request: POST JSON body with:
            - ``task_type`` (str)
            - ``rule_index`` (int)
            - ``batch_id`` (int)
            - ``source`` (str): ``"model"`` or ``"random"``
            - ``model_version`` (str, required when source=model)
            - ``prob_min`` (float, optional, default 0.4)
            - ``prob_max`` (float, optional, default 0.6)

    Returns:
        JSON with ``status``, ``assets_added``, ``batch_id``,
        ``large_sub_batch``, and ``explanation``.

    Frontend:
        Called by ``setup_session.js`` on modal submit.  On success the page
        is reloaded so the new sub-batch card appears immediately.
    """
    from django.core.cache import cache as _cache

    # model_predictions and content.assets live in the prod DB
    _prod_db = "prod" if "prod" in settings.DATABASES else "default"

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        body = request.data or {}

    task_type = body.get("task_type")
    source = body.get("source", "random")

    try:
        rule_index = int(body.get("rule_index"))
        batch_id = int(body.get("batch_id"))
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "status": "failed",
                "explanation": "rule_index and batch_id must be integers",
            },
            status=400,
        )

    if not task_type:
        return JsonResponse(
            {"status": "failed", "explanation": "task_type is required"}, status=400
        )

    try:
        # 1. Capacity check -------------------------------------------------
        current_count = label_data_selected_assets_new.objects.filter(
            task_type=task_type, rule_index=rule_index, batch_id=batch_id
        ).count()

        if current_count + SUB_BATCH_SIZE > BATCH_MAX_ASSETS:
            return JsonResponse(
                {
                    "status": "failed",
                    "explanation": (
                        f"Batch {batch_id} already has {current_count} assets. "
                        f"Adding {SUB_BATCH_SIZE} would exceed the {BATCH_MAX_ASSETS} limit. "
                        "Please create a new batch_id first."
                    ),
                },
                status=400,
            )

        # 2. Existing asset IDs for this task/rule --------------------------
        existing_ids = set(
            label_data_selected_assets_new.objects.filter(
                task_type=task_type, rule_index=rule_index
            ).values_list("asset_id", flat=True)
        )
        logger.debug(
            "create_sub_batch: %d existing assets for %s/rule %d",
            len(existing_ids),
            task_type,
            rule_index,
        )

        # 3. Candidate pool -------------------------------------------------
        if source == "model":
            model_version = body.get("model_version")
            if not model_version:
                return JsonResponse(
                    {
                        "status": "failed",
                        "explanation": "model_version is required for model source",
                    },
                    status=400,
                )
            prob_min = float(body.get("prob_min", 0.4))
            prob_max = float(body.get("prob_max", 0.6))

            candidates_qs = (
                model_rule_label_predictions_versioned.objects.using(_prod_db)
                .filter(
                    task_type=task_type,
                    rule_index=rule_index,
                    model_version=model_version,
                    probability__gt=prob_min,
                    probability__lt=prob_max,
                )
                .exclude(asset_id__in=existing_ids)
                .values("asset_id")
            )
            candidate_ids = list(candidates_qs.values_list("asset_id", flat=True))
            logger.debug(
                "create_sub_batch model: %d candidate_ids from predictions",
                len(candidate_ids),
            )

            if not candidate_ids:
                return JsonResponse(
                    {
                        "status": "failed",
                        "explanation": (
                            f"No candidate assets found in model_predictions for "
                            f"{task_type}/rule {rule_index}, model={model_version}, "
                            f"prob {prob_min}–{prob_max} (db={_prod_db})."
                        ),
                    },
                    status=400,
                )

            # Verify s3=True and get image_link (content.assets lives in prod)
            pool = list(
                content_asset_table.objects.using(_prod_db)
                .filter(asset_id__in=candidate_ids, s3=True)
                .values("asset_id", "image_link")
            )
            logger.debug(
                "create_sub_batch model: %d assets with s3=True from pool", len(pool)
            )

            if not pool:
                return JsonResponse(
                    {
                        "status": "failed",
                        "explanation": (
                            f"Found {len(candidate_ids)} model candidates but none have s3=True "
                            f"in content.assets (db={_prod_db}). "
                            "Check that PROD_DATABASE_URL points to the production database."
                        ),
                    },
                    status=400,
                )

        else:  # random
            # Pull a window of eligible assets ordered by asset_id (fast, no full sort)
            pool_qs = (
                content_asset_table.objects.using(_prod_db)
                .filter(s3=True)
                .exclude(asset_id__in=existing_ids)
                .values("asset_id", "image_link")
            )
            # Count and pick a random offset window to avoid bias toward low IDs
            pool_count = pool_qs.count()
            logger.debug(
                "create_sub_batch random: pool_count=%d (db=%s)", pool_count, _prod_db
            )
            if pool_count == 0:
                return JsonResponse(
                    {
                        "status": "failed",
                        "explanation": (
                            f"No eligible s3=True assets after excluding {len(existing_ids)} existing IDs "
                            f"(db={_prod_db}). "
                            "Check that PROD_DATABASE_URL points to the production database."
                        ),
                    },
                    status=400,
                )
            window = min(pool_count, max(SUB_BATCH_SIZE * 10, 5000))
            offset = random.randint(0, max(0, pool_count - window))
            pool = list(pool_qs.order_by("asset_id")[offset : offset + window])
            logger.debug(
                "create_sub_batch random: fetched %d from pool (offset=%d window=%d)",
                len(pool),
                offset,
                window,
            )

            if not pool:
                return JsonResponse(
                    {
                        "status": "failed",
                        "explanation": (
                            f"pool_count={pool_count} but fetched 0 rows "
                            f"(offset={offset}, window={window}). Unexpected — retry."
                        ),
                    },
                    status=400,
                )

        # 4. Sample 500 -----------------------------------------------------
        sample_n = min(SUB_BATCH_SIZE, len(pool))
        selected = random.sample(pool, sample_n)

        # 5. Next large_sub_batch for this batch ----------------------------
        max_lsb = (
            label_data_selected_assets_new.objects.filter(
                task_type=task_type, rule_index=rule_index, batch_id=batch_id
            ).aggregate(m=Max("large_sub_batch"))["m"]
            or 0
        )
        next_lsb = max_lsb + 1

        # 6. Build rows -----------------------------------------------------
        date_now = datetime.now().strftime("%Y-%m-%d")
        model_batch_label = (
            body.get("model_version", "random") if source == "model" else "random"
        )

        rows = []
        for i, asset in enumerate(selected):
            rows.append(
                label_data_selected_assets_new(
                    asset_id=asset["asset_id"],
                    image_link=asset["image_link"],
                    batch_id=batch_id,
                    date_created=date_now,
                    label_count=0,
                    asset_type="undetermined",
                    clip_art_type=0,
                    count=0,
                    line_width=0,
                    color_depth=0,
                    primary_color=0,
                    sub_batch=(i // 5) + 1,
                    large_sub_batch=next_lsb,
                    color_type="undetermined",
                    multi_element="undetermined",
                    task_type=task_type,
                    rule_index=rule_index,
                )
            )

        # 7. Insert ---------------------------------------------------------
        label_data_selected_assets_new.objects.bulk_create(rows, batch_size=500)
        logger.debug(
            "create_sub_batch: inserted %d rows → batch %d lsb %d",
            len(rows),
            batch_id,
            next_lsb,
        )

        # 8. Invalidate session options cache --------------------------------
        _cache.clear()

        return JsonResponse(
            {
                "status": "success",
                "assets_added": len(rows),
                "batch_id": batch_id,
                "large_sub_batch": next_lsb,
                "explanation": f"Added {len(rows)} assets as sub-batch {next_lsb} of batch {batch_id}.",
            }
        )

    except Exception as e:
        logger.exception("create_sub_batch error")
        return JsonResponse({"status": "failed", "explanation": str(e)}, status=500)


@csrf_exempt
@api_view(["GET"])
def get_reconcile_count(request):
    """Return the number of disputed (50/50) assets for a task_type + rule_index.

    Args:
        request: GET with ``task_type`` and ``rule_index`` query params.

    Returns:
        JSON with ``disputed_count`` (int).

    Frontend:
        Called by ``setup_session.js`` when a rule is selected, to populate the
        reconciliation section count before the user starts reconciling.
    """
    task_type = request.GET.get("task_type")
    rule_index = request.GET.get("rule_index")

    if not task_type or rule_index is None:
        return JsonResponse({"status": "failed", "explanation": "task_type and rule_index are required"}, status=400)

    try:
        rule_index = int(rule_index)

        flagged_ids = set(label_issues_table.objects.values_list("asset_id", flat=True))

        pr_qs = prompt_responses.objects.filter(
            task_type=task_type, rule_index=rule_index
        ).values("asset_id", "prompt_response")

        pr_df = pd.DataFrame(list(pr_qs))

        if pr_df.empty:
            return JsonResponse({"disputed_count": 0})

        disputed = (
            pr_df.groupby("asset_id")
            .agg(samples=("prompt_response", "count"), yes=("prompt_response", lambda x: (x == "yes").sum()))
            .reset_index()
            .query("samples > 1")
            .assign(pct=lambda x: x.yes / x.samples)
            .query("pct == 0.5")
            .query("asset_id not in @flagged_ids")
        )

        return JsonResponse({"disputed_count": len(disputed)})

    except Exception as e:
        logger.exception("get_reconcile_count error")
        return JsonResponse({"status": "failed", "explanation": str(e)}, status=500)
