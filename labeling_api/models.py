"""Django ORM models for the labeling API (all **unmanaged** PostgreSQL tables).

Each subclass of :class:`~django.db.models.Model` maps one database table
(:attr:`Meta.db_table`). These are not created by migrations; they must already
exist in the configured database.

**Inputs / outputs (conceptual):** There are no Python functions here—only model
classes. The ORM maps **table rows ↔ model instances**; managers such as
``.objects`` accept lookup parameters and return :class:`~django.db.models.QuerySet`
results or single instances on read, and persist writes when ``save()`` is used
on managed workflows (these models are unmanaged, so migrations do not apply).
"""

from __future__ import annotations

from typing import Type

from django.db import models


class simulated_assets_color_table(models.Model):
    """Simulated color rows for training/evaluation tooling.

    **Table:** ``simulated_assets_color_table``

    **ORM:** One instance ↔ one row; ``.objects`` yields querysets of these rows.
    """

    index = models.BigIntegerField(primary_key=True)
    asset_id = models.BigIntegerField()
    color_level = models.SmallIntegerField()
    broad_color_label = models.CharField()
    tint = models.CharField()
    specific_color_label = models.CharField(max_length=512)
    hex_code = models.CharField()
    manual_label = models.BooleanField()

    class Meta:
        managed = False
        db_table = "simulated_assets_color_table"


class asset_color_manual_label(models.Model):
    """Manual per-layer color labels and masks for assets.

    **Table:** ``asset_color_manual_label``

    **ORM:** One instance ↔ one manual color label row; filter by ``asset_id`` / ``color_index``.
    """

    index = models.AutoField(primary_key=True)
    asset_id = models.BigIntegerField()
    color_index = models.SmallIntegerField()
    color_type = models.CharField()
    color_rgb_values = models.CharField()
    mask_rgb_values = models.CharField()
    layer_type = models.CharField()
    color_map_link = models.CharField()
    manual_label = models.BooleanField()
    date_created = models.DateTimeField()
    labeler_id = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = "asset_color_manual_label"


class label_data_selected_assets_new(models.Model):
    """Assets queued for labeling batches (metadata + type hints).

    **Table:** ``label_data.selected_assets_new``

    **ORM:** One instance ↔ one selected asset row; primary key ``asset_id``.
    """

    asset_id = models.BigIntegerField(primary_key=True)
    image_link = models.CharField()
    batch_id = models.SmallIntegerField()
    date_created = models.DateField()
    label_count = models.SmallIntegerField()
    asset_type = models.CharField()
    clip_art_type = models.SmallIntegerField()
    count = models.SmallIntegerField()
    line_width = models.SmallIntegerField()
    color_depth = models.SmallIntegerField()
    primary_color = models.SmallIntegerField()
    sub_batch = models.IntegerField()
    large_sub_batch = models.IntegerField()
    color_type = models.CharField()
    multi_element = models.CharField()
    task_type = models.CharField()
    rule_index = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = "label_data.selected_assets_new"


# Same model; keep old name so `from .models import *` and legacy references work.
label_data_selected_assets: Type[label_data_selected_assets_new] = (
    label_data_selected_assets_new
)


class label_data_art_type_labels(models.Model):
    """Human art-type labels tied to assets (labeling pipeline).

    **Table:** ``label_data.art_type.labels``

    **Inputs (ORM):** Filter/update by ``asset_id``, ``label_type``, ``labeler_id``, timestamps.

    **Outputs:** :class:`~django.db.models.QuerySet` rows / instances with string ``label`` and metadata.
    """

    datetime_created = models.DateTimeField()
    labeler_source = models.CharField()
    labeler_id = models.CharField()
    label_type = models.CharField()
    asset_id = models.BigIntegerField()
    label = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.art_type.labels"


class label_data_art_type_prompt_responses(models.Model):
    """Per-task prompt responses for art-type labeling (incl. MTurk metadata).

    **Table:** ``label_data.art_type.prompt_responses``

    **Inputs (ORM):** Lookups on ``asset_id``, ``task_type``, ``rule_index``, ``assignment_id``.

    **Outputs:** Rows with ``prompt_response`` and quality flags (test/lure, batch ids).
    """

    datetime_created = models.DateTimeField()
    labeler_source = models.CharField()
    labeler_id = models.CharField()
    label_type = models.CharField()
    asset_id = models.BigIntegerField()
    task_type = models.CharField()
    rule_index = models.SmallIntegerField()
    prompt_response = models.CharField()
    assignment_id = models.CharField()
    hit_id = models.CharField()
    is_test_question = models.CharField()
    mturk_batch_id = models.IntegerField()
    is_lure_question = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.art_type.prompt_responses"


class labelling_rules(models.Model):
    """Configurable labeling rules (title, prompt, status) per task type.

    **Table:** ``label_data.labelling_rules``

    **Inputs (ORM):** Primary key ``id``; filter by ``task_type``, ``rule_index``, ``status``.

    **Outputs:** Rule rows used to drive UI and validation.
    """

    id = models.SmallIntegerField(primary_key=True)
    task_type = models.CharField()
    rule_index = models.SmallIntegerField()
    title = models.CharField()
    description = models.CharField()
    prompt = models.CharField()
    status = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.labelling_rules"


class labelling_rule_filters(models.Model):
    """Key/value filters associated with a labeling rule.

    **Table:** ``label_data.labelling_rules.filters``

    **Inputs (ORM):** ``id`` (rule id), ``task_type``, ``key``, ``value``.

    **Outputs:** Filter rows constraining which assets/tasks a rule applies to.
    """

    id = models.SmallIntegerField(primary_key=True)
    task_type = models.CharField()
    key = models.SmallIntegerField()
    value = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.labelling_rules.filters"


class labeler_table(models.Model):
    """Registered labelers (display names).

    **Table:** ``label_data.labelers``

    **Inputs (ORM):** ``id`` primary key.

    **Outputs:** Labeler identity rows for attribution on labels and responses.
    """

    id = models.SmallIntegerField(primary_key=True)
    display_name = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.labelers"


class rule_examples(models.Model):
    """Example assets illustrating a rule (caption + asset reference).

    **Table:** ``label_data.rule_examples``

    **Inputs (ORM):** ``task_type``, ``rule_index``, ``directive_id``, ``asset_id``.

    **Outputs:** Example rows for training/review UIs.
    """

    id = models.IntegerField(primary_key=True)
    task_type = models.CharField()
    rule_index = models.SmallIntegerField()
    directive_id = models.IntegerField()
    caption = models.CharField()
    asset_id = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.rule_examples"


class rule_directives(models.Model):
    """Directive text and valence for a rule (what to look for).

    **Table:** ``label_data.rule_directives``

    **Inputs (ORM):** ``task_type``, ``rule_index``, ``directive`` text.

    **Outputs:** Directive rows linked from examples and sessions.
    """

    id = models.IntegerField(primary_key=True)
    task_type = models.CharField()
    rule_index = models.CharField()
    valence = models.CharField()
    directive = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.rule_directives"


class test_questions(models.Model):
    """Gold-standard test items for a rule (expected prompt response).

    **Table:** ``label_data.test_questions``

    **Inputs (ORM):** ``asset_id``, ``rule_index``, ``example_id``.

    **Outputs:** Test question rows including ``prompt_response`` for scoring.
    """

    id = models.BigIntegerField(primary_key=True)
    asset_id = models.BigIntegerField()
    rule_index = models.SmallIntegerField()
    prompt_response = models.CharField()
    example_id = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = "label_data.test_questions"


class lure_questions(models.Model):
    """Attention-check / lure questions with correct answers.

    **Table:** ``label_data.lure_questions``

    **Inputs (ORM):** ``task_type``, ``label_type``, ``asset_id``, ``rule_index``.

    **Outputs:** Rows with ``correct_response`` and ``explanation``.
    """

    id = models.BigIntegerField(primary_key=True)
    task_type = models.CharField()
    label_type = models.CharField()
    asset_id = models.BigIntegerField()
    rule_index = models.SmallIntegerField()
    correct_response = models.CharField()
    explanation = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.lure_questions"


class batch_tracker(models.Model):
    """Batch lifecycle tracking (status, labeler, task/rule scope).

    **Table:** ``label_data.batch_tracker``

    **Inputs (ORM):** ``batch_id``, ``batch_type``, ``sub_batch_id``, ``status``.

    **Outputs:** Tracker rows for monitoring labeling batches.
    """

    batch_id = models.BigIntegerField()
    batch_type = models.CharField()
    sub_batch_id = models.CharField()
    status = models.CharField()
    labeler_id = models.CharField()
    task_type = models.CharField()
    rule_index = models.IntegerField()

    class Meta:
        managed = False
        db_table = "label_data.batch_tracker"


class assets_w_rule_labels(models.Model):
    """Aggregated rule labels per asset (agreement and strength).

    **Table:** ``label_data.asset_type.rule.labels``

    **Inputs (ORM):** ``asset_id``, ``task_type``, ``rule_index``.

    **Outputs:** Rows with ``label``, ``percent_agree``, ``label_strength``.
    """

    asset_id = models.BigIntegerField()
    task_type = models.CharField()
    rule_index = models.IntegerField()
    label_source = models.CharField()
    label = models.IntegerField()
    percent_agree = models.FloatField()
    label_strength = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.asset_type.rule.labels"


class prompt_responses(models.Model):
    """Stored prompt responses for rule-based labeling tasks.

    **Table:** ``label_data.prompt_responses``

    **Inputs (ORM):** ``asset_id``, ``labeler_id``, ``task_type``, ``rule_index``.

    **Outputs:** Response rows with ``prompt_response`` and ``labeler_count``.
    """

    datetime_created = models.DateTimeField()
    asset_id = models.BigIntegerField()
    labeler_source = models.CharField()
    labeler_id = models.CharField()
    labeler_count = models.IntegerField()
    task_type = models.CharField()
    rule_index = models.SmallIntegerField()
    prompt_response = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.prompt_responses"


class search_term_table(models.Model):
    """Search-topic terms and selection state for asset discovery.

    **Table:** ``label_data.search_results_terms_table``

    **Inputs (ORM):** ``search_topic_id``, ``batch_id``, ``status``, ``selected_index``.

    **Outputs:** Term rows tying topics to ``asset_type`` and batch workflow.
    """

    id = models.BigIntegerField(primary_key=True)
    search_topic_id = models.BigIntegerField()
    search_topic = models.CharField()
    asset_type = models.CharField()
    selected_index = models.IntegerField()
    batch_id = models.IntegerField()
    status = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.search_results_terms_table"


class search_term_responses_table(models.Model):
    """Labeler responses linking selected vs listing assets for search tasks.

    **Table:** ``label_data.search_results_responses``

    **Inputs (ORM):** ``term_table_id``, ``labeler_id``, ``selected_asset_id``, ``listing_asset_id``.

    **Outputs:** Rows with optional ``response`` and ``status`` (nullable response allowed at create).

    **Note:** Uses :class:`~django.db.models.BigAutoField` so ``id`` is treated as DB-generated.
    """

    id = models.BigAutoField(primary_key=True)
    datetime_created = models.DateTimeField()
    term_table_id = models.BigIntegerField()
    labeler_id = models.CharField()
    selected_asset_id = models.BigIntegerField()
    listing_asset_id = models.BigIntegerField()
    # Response is intended to start unset.
    response = models.CharField(null=True, blank=True)
    status = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.search_results_responses"


class model_asset_type_label_predictions(models.Model):
    """Model-predicted asset-type labels (versioned).

    **Table:** ``model_predictions.asset_type``

    **Inputs (ORM):** ``asset_id``, ``model_version``.

    **Outputs:** Rows with predicted ``asset_type`` string.
    """

    asset_id = models.BigIntegerField()
    asset_type = models.CharField()
    model_version = models.FloatField()

    class Meta:
        managed = False
        db_table = "model_predictions.asset_type"


class model_rule_label_predictions(models.Model):
    """Model-predicted rule labels with probability and integer label id.

    **Table:** ``model_predictions.rule.labels``

    **Inputs (ORM):** ``asset_id``, ``task_type``, ``rule_index``.

    **Outputs:** Rows with ``probability``, ``label``, ``created_at``.
    """

    asset_id = models.BigIntegerField()
    task_type = models.CharField()
    rule_index = models.BigIntegerField()
    probability = models.FloatField()
    label = models.IntegerField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "model_predictions.rule.labels"


class model_rule_label_predictions_versioned(models.Model):
    """Model-predicted rule labels including model_version and probability score.

    **Table:** ``model_predictions.rule_labels``

    **Inputs (ORM):** Filter by ``task_type``, ``rule_index``, ``model_version``,
    and ``probability`` range.

    **Outputs:** Rows with ``asset_id`` candidates for batch creation.
    """

    asset_id = models.BigIntegerField()
    task_type = models.CharField()
    rule_index = models.BigIntegerField()
    model_version = models.CharField()
    probability = models.FloatField()
    label = models.IntegerField()

    class Meta:
        managed = False
        db_table = '"model_predictions"."rule_labels"'


class label_issues_table(models.Model):
    """Reported labeling issues (status and type) per asset/rule.

    **Table:** ``label_data.label_issues``

    **Inputs (ORM):** ``asset_id``, ``task_type``, ``rule_index``, ``labeler_id``.

    **Outputs:** Issue rows with ``issue_status`` and ``issue_type``.
    """

    datetime_created = models.DateTimeField()
    asset_id = models.BigIntegerField()
    task_type = models.CharField()
    rule_index = models.IntegerField()
    labeler_id = models.CharField()
    issue_status = models.CharField()
    issue_type = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.label_issues"


class content_asset_table(models.Model):
    """Core catalog metadata for scraped/listing assets (content schema).

    **Table:** ``content.assets``

    **Inputs (ORM):** ``asset_id``, ``log_id``, ``site_art_id``, dates and links.

    **Outputs:** Rich metadata rows (tags, categories, pricing, S3 flag, image link).
    """

    asset_id = models.BigIntegerField()
    log_id = models.BigIntegerField()
    site_art_id = models.CharField()
    page_num = models.BigIntegerField()
    listing_rank = models.BigIntegerField()
    original_date = models.DateField()
    cur_date = models.DateField()
    page_title = models.CharField()
    tags = models.CharField()
    formats = models.CharField()
    categories = models.CharField()
    author = models.CharField()
    page_link = models.CharField()
    image_link = models.CharField()
    cost = models.CharField()
    s3 = models.BooleanField()

    class Meta:
        managed = False
        db_table = '"content"."assets"'


class label_testing_session(models.Model):
    """A label-testing session scoped to task type and rule.

    **Table:** ``label_data.label_testing.session``

    **Inputs (ORM):** ``id``, ``task_type``, ``rule_index``.

    **Outputs:** Session header rows for experiments and batches.
    """

    id = models.BigIntegerField(primary_key=True)
    task_type = models.CharField()
    rule_index = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = "label_data.label_testing.session"


class label_testing_directives(models.Model):
    """Directives attached to a label-testing session.

    **Table:** ``label_data.label_testing.directives``

    **Inputs (ORM):** ``session_id``, ``directive_id``, ``valence``.

    **Outputs:** Directive text rows for controlled tests.
    """

    id = models.BigIntegerField(primary_key=True)
    session_id = models.BigIntegerField()
    valence = models.CharField()
    directive = models.CharField()
    directive_id = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = "label_data.label_testing.directives"


class label_testing_experiments(models.Model):
    """Experiment results (confusion counts) for a session/batch/directive.

    **Table:** ``label_data.label_testing.experiments``

    **Inputs (ORM):** ``session_id``, ``batch_id``, ``directive_id``.

    **Outputs:** Rows with ``accuracy``, TP/FP/TN/FN, ``label_source``.
    """

    session_id = models.BigIntegerField()
    batch_id = models.BigIntegerField()
    directive_id = models.CharField()
    accuracy = models.FloatField()
    true_positive = models.BigIntegerField()
    false_positive = models.BigIntegerField()
    true_negative = models.BigIntegerField()
    false_negative = models.BigIntegerField()
    label_source = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.label_testing.experiments"


class label_testing_batches(models.Model):
    """Per-asset batch rows for label-testing runs.

    **Table:** ``label_data.label_testing.batches``

    **Inputs (ORM):** ``session_id``, ``asset_id``, ``batch_id``.

    **Outputs:** Rows with string ``label`` outcome for analysis.
    """

    id = models.BigIntegerField(primary_key=True)
    session_id = models.BigIntegerField()
    asset_id = models.BigIntegerField()
    batch_id = models.BigIntegerField()
    label = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.label_testing.batches"


class model_results_table(models.Model):
    """Training/validation metrics and hyperparameters for a model run.

    **Table:** ``label_data.model_results``

    **Inputs (ORM):** ``id``, ``model_type``, ``task_type``, ``rule_index``.

    **Outputs:** Full metric row (loss, AUC, counts, image metadata, ``best_epoch``).
    """

    id = models.BigIntegerField(primary_key=True)
    model_type = models.CharField()
    rule_index = models.BigIntegerField()
    task_type = models.CharField()
    epochs = models.BigIntegerField()
    batch_size = models.BigIntegerField()
    optimizer = models.CharField()
    learning_rate = models.FloatField()
    weight_decay = models.FloatField()
    val_loss = models.FloatField()
    val_accuracy = models.FloatField()
    val_auc = models.FloatField()
    val_precision = models.FloatField()
    val_recall = models.FloatField()
    val_fp = models.BigIntegerField()
    val_fn = models.BigIntegerField()
    val_tp = models.BigIntegerField()
    val_tn = models.BigIntegerField()
    image_link = models.CharField()
    image_size_width = models.BigIntegerField()
    image_size_height = models.BigIntegerField()
    train_samples = models.BigIntegerField()
    val_samples = models.BigIntegerField()
    created_at = models.DateTimeField()
    best_epoch = models.BigIntegerField()
    outcome_type = models.CharField()
    val_mae = models.FloatField()
    pretrained_model = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.model_results"


class production_models_table(models.Model):
    """Production model registry (active flag, artifact link).

    **Table:** ``label_data.model_results_prod``

    **Inputs (ORM):** ``version_id`` primary key, ``active``, ``dev_id``.

    **Outputs:** Rows pointing at deployed ``model_link``.
    """

    version_id = models.CharField(primary_key=True)
    active = models.BooleanField()
    dev_id = models.IntegerField()
    model_link = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.model_results_prod"


class color_type_table(models.Model):
    """Human or model color-type labels per asset (versioned source).

    **Table:** ``label_data.color_type.labels``

    **Inputs (ORM):** ``asset_id``, ``source``, ``model_version``.

    **Outputs:** Rows with ``color_type`` classification.
    """

    id = models.BigIntegerField(primary_key=True)
    asset_id = models.BigIntegerField()
    source = models.CharField()
    color_type = models.CharField()
    model_version = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.color_type.labels"


class line_type_table(models.Model):
    """Line-type classification per asset (versioned source).

    **Table:** ``label_data.line_type.labels``

    **Inputs (ORM):** ``asset_id``, ``source``, ``model_version``.

    **Outputs:** Rows with ``line_type`` string.
    """

    id = models.BigIntegerField(primary_key=True)
    asset_id = models.BigIntegerField()
    source = models.CharField()
    line_type = models.CharField()
    model_version = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.line_type.labels"


class asset_type_table(models.Model):
    """Asset-type labels (distinct from model_predictions snapshot tables).

    **Table:** ``label_data.asset_type.labels``

    **Inputs (ORM):** ``asset_id``, ``source``, ``model_version``.

    **Outputs:** Rows with ``asset_type`` string.
    """

    id = models.BigIntegerField(primary_key=True)
    asset_id = models.BigIntegerField()
    source = models.CharField()
    asset_type = models.CharField()
    model_version = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.asset_type.labels"


class ray_trace_mask_table(models.Model):
    """Ray-trace mask statistics (dark ratio) per asset.

    **Table:** ``label_data.ray_trace_masks``

    **Inputs (ORM):** ``asset_id``, ``date_time_created``.

    **Outputs:** Rows with ``dark_ratio`` and ``dark_label``.
    """

    id = models.BigIntegerField(primary_key=True)
    date_time_created = models.DateTimeField()
    asset_id = models.BigIntegerField()
    dark_ratio = models.FloatField()
    dark_label = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.ray_trace_masks"


class modified_prompt_table(models.Model):
    """Overrides/edits to stored prompt responses after initial submission.

    **Table:** ``label_data.modified_prompt_responses``

    **Inputs (ORM):** ``asset_id``, ``labeler_id``, ``task_type``, ``rule_index``.

    **Outputs:** Rows with ``modified_prompt_response``.
    """

    date_time_created = models.DateTimeField()
    asset_id = models.BigIntegerField()
    labeler_source = models.CharField()
    labeler_id = models.CharField()
    task_type = models.CharField()
    rule_index = models.IntegerField()
    modified_prompt_response = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.modified_prompt_responses"


class primary_colors_table(models.Model):
    """Dominant RGB clusters / scores from primary-color model predictions.

    **Table:** ``model_predictions.primary_colors``

    **Inputs (ORM):** ``asset_id``, ``id`` (row id).

    **Outputs:** Rows with ``r``/``g``/``b``, ``score``, proportion fields.
    """

    date_time_created = models.DateTimeField()
    asset_id = models.BigIntegerField()
    r = models.SmallIntegerField()
    g = models.SmallIntegerField()
    b = models.SmallIntegerField()
    score = models.FloatField()
    proportion_prominent_color = models.FloatField()
    proportion_to_all_pixels = models.FloatField()
    id = models.BigIntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = "model_predictions.primary_colors"


class line_width_label_table(models.Model):
    """Line-width label with prominence (versioned source).

    **Table:** ``label_data.line_width.labels`` (parallel naming to ``line_width_table``; distinct model).

    **Inputs (ORM):** ``asset_id``, ``source``, ``model_version``.

    **Outputs:** Rows with ``line_width`` and ``prominence``.
    """

    id = models.AutoField(primary_key=True)
    asset_id = models.BigIntegerField()
    source = models.CharField()
    line_width = models.IntegerField()
    prominence = models.FloatField()
    model_version = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.line_width.labels"


class line_width_sample_table(models.Model):
    """Sampled points used for line-width measurement/QA.

    **Table:** ``label_data.line_width_samples``

    **Inputs (ORM):** ``asset_id``, ``sample_index``, ``labeler_id``.

    **Outputs:** Rows with coordinates, ``radius``, image dimensions, ``status``.
    """

    id = models.AutoField(primary_key=True)
    asset_id = models.BigIntegerField()
    sample_index = models.IntegerField()
    x_coord = models.IntegerField()
    y_coord = models.IntegerField()
    radius = models.IntegerField()
    image_width = models.IntegerField()
    image_height = models.IntegerField()
    labeler_id = models.CharField()
    status = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.line_width_samples"


class mismatched_labels_table(models.Model):
    """Manual vs model label disagreements flagged for review.

    **Table:** ``label_data.mismatched_labels``

    **Inputs (ORM):** ``asset_id``, ``task_type``, ``rule_index``, ``batch_id``.

    **Outputs:** Rows with ``manual_label``, ``model_label``, ``status``.
    """

    id = models.AutoField(primary_key=True)
    asset_id = models.BigIntegerField()
    task_type = models.CharField()
    rule_index = models.BigIntegerField()
    batch_id = models.BigIntegerField()
    manual_label = models.CharField()
    model_label = models.CharField()
    status = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.mismatched_labels"


class rough_fill_score_table(models.Model):
    """Rough-fill / texture heuristic scores for paint-fill analysis.

    **Table:** ``label_data.rough_fill_scores``

    **Inputs (ORM):** ``asset_id`` primary key.

    **Outputs:** Rows with roughness metrics, histogram group, ``label``, ``score``.
    """

    asset_id = models.BigIntegerField(primary_key=True)
    roughness = models.FloatField()
    mean_dif = models.FloatField()
    percent_rough = models.FloatField()
    mean_roughness = models.FloatField()
    histogram_group = models.IntegerField()
    estimated_peak_count = models.IntegerField()
    identical_count = models.FloatField()
    lg_identical_count = models.FloatField()
    blur_measure = models.FloatField()
    label = models.IntegerField()
    score = models.FloatField()

    class Meta:
        managed = False
        db_table = "label_data.rough_fill_scores"


class line_width_table(models.Model):
    """Line-width estimates (BigInteger id variant of line-width labels).

    **Table:** ``label_data.line_width.labels`` (same DB table name as ``line_width_label_table``; use one model consistently).

    **Inputs (ORM):** ``asset_id``, ``source``, ``model_version``.

    **Outputs:** Rows with ``line_width`` (bigint) and ``prominence``.
    """

    id = models.BigIntegerField(primary_key=True)
    asset_id = models.BigIntegerField()
    source = models.CharField()
    line_width = models.BigIntegerField()
    prominence = models.FloatField()
    model_version = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.line_width.labels"


class paint_fill_table(models.Model):
    """Paint fill type classification per asset.

    **Table:** ``label_data.paint_fill_type.labels``

    **Inputs (ORM):** ``asset_id``, ``source``, ``model_version``.

    **Outputs:** Rows with ``fill_type``.
    """

    id = models.BigIntegerField(primary_key=True)
    asset_id = models.BigIntegerField()
    source = models.CharField()
    fill_type = models.CharField()
    model_version = models.CharField()

    class Meta:
        managed = False
        db_table = "label_data.paint_fill_type.labels"


class extracted_features_table(models.Model):
    """Optional extracted features / generated title for search flows.

    **Table:** ``content.extracted_features``

    **Inputs (ORM):** ``asset_id`` primary key.

    **Outputs:** Rows with ``mono_color`` and ``model_generated_title`` (nullable).

    **Note:** May be absent in some DBs; ``get_search_results`` can use this while session/batch
    flows often read from ``label_data.selected_assets_new`` instead.
    """

    asset_id = models.BigIntegerField(primary_key=True)
    mono_color = models.SmallIntegerField(null=True)
    model_generated_title = models.CharField(max_length=4096, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "content.extracted_features"


# Legacy name used across views (formerly imported from api.models)
asset_table: Type[content_asset_table] = content_asset_table
