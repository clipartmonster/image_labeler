from django.urls import path
from . import views


urlpatterns = [
    path("get_color_labels/", views.get_color_labels, name="get_color_labels"),
    path("update_color_labels/", views.update_color_labels, name="update_color_labels"),
    path("remove_color_label/", views.remove_color_label, name="remove_color_label"),
    path(
        "compute_color_distance_labels/",
        views.compute_color_distance_labels,
        name="compute_color_distance_labels",
    ),
    path("get_assets_to_label/", views.get_assets_to_label, name="get_assets_to_label"),
    path("add_label/", views.add_label, name="add_label"),
    path("collect_label/", views.collect_label, name="collect_label"),
    path("collect_prompt/", views.collect_prompt, name="collect_prompt"),
    path("get_labelling_rules/", views.get_labelling_rules, name="get_labelling_rules"),
    path(
        "remove_prompt_responses/",
        views.remove_prompt_responses,
        name="remove_prompt_responses",
    ),
    path(
        "get_prompt_responses/", views.get_prompt_responses, name="get_prompt_responses"
    ),
    path(
        "collect_prompt_internal_source/",
        views.collect_prompt_internal_source,
        name="collect_prompt_internal_source",
    ),
    path(
        "collect_validation_response/",
        views.collect_validation_response,
        name="collect_validation_response",
    ),
    path(
        "update_submission_status/",
        views.update_submission_status,
        name="update_submission_status",
    ),
    path("get_test_questions/", views.get_test_questions, name="get_test_questions"),
    path("get_lure_questions/", views.get_lure_questions, name="get_lure_questions"),
    path("get_asset_batch/", views.get_asset_batch, name="get_asset_batch"),
    path("get_batch_indexes/", views.get_batch_indexes, name="get_batch_indexes"),
    path("get_asset_labels/", views.get_asset_labels, name="get_asset_labels"),
    path("get_disputed_assets/", views.get_disputed_assets, name="get_disputed_assets"),
    path(
        "get_assets_w_rule_labels/",
        views.get_assets_w_rule_labels,
        name="get_assets_w_rule_labels",
    ),
    path("get_session_options/", views.get_session_options, name="get_session_options"),
    path(
        "get_batch_for_viewing/",
        views.get_batch_for_viewing,
        name="get_batch_for_viewing",
    ),
    path("get_predictions/", views.get_predictions, name="get_predictions"),
    path(
        "get_assets_w_label_issues/",
        views.get_assets_w_label_issues,
        name="get_assets_w_label_issues",
    ),
    path("get_model_results/", views.get_model_results, name="get_model_results"),
    path("collect_label_issue/", views.collect_label_issue, name="collect_label_issue"),
    path(
        "collect_modified_prompt/",
        views.collect_modified_prompt,
        name="collect_modified_prompt",
    ),
    path(
        "remove_modified_prompt/",
        views.remove_modified_prompt,
        name="remove_modified_prompt",
    ),
    path("get_dark_ratios/", views.get_dark_ratios, name="get_dark_ratios"),
    path("get_primary_colors/", views.get_primary_colors, name="get_primary_colors"),
    path(
        "get_rough_fill_scores/",
        views.get_rough_fill_scores,
        name="get_rough_fill_scores",
    ),
    path("get_line_widths/", views.get_line_widths, name="get_line_widths"),
    path(
        "collect_line_width_sample/",
        views.collect_line_width_sample,
        name="collect_line_sample_width",
    ),
    path(
        "remove_line_width_sample/",
        views.remove_line_width_sample,
        name="remove_line_sample_width",
    ),
    path(
        "label_line_width_as_invalid/",
        views.label_line_width_as_invalid,
        name="label_line_width_as_invalid",
    ),
    path(
        "get_mismatched_labels/",
        views.get_mismatched_labels,
        name="get_mismatched_labels",
    ),
    path(
        "collect_mismatch_prompt/",
        views.collect_mismatch_prompt,
        name="collect_mismatch_prompt",
    ),
    path(
        "reset_mismatch_prompt/",
        views.reset_mismatch_prompt,
        name="reset_mismatch_prompt",
    ),
    path(
        "get_label_testing_options/",
        views.get_label_testing_options,
        name="get_label_testing_options",
    ),

    ##################################################
    #Label search Results

    path(
        "get_text_search_results/", 
         views.get_text_search_results, 
         name = 'get_text_search_results'
    ),

     path(
        "get_search_results/", 
         views.get_search_results, 
         name = 'get_search_results'
    ),

    path(
        "get_search_term/",
        views.get_search_term,
        name="get_search_term"
    ),

    path(
        "get_available_search_batches/",
        views.get_available_search_batches,
        name="get_available_search_batches"
    ),

    path(
        "update_search_result_response/",
        views.update_search_result_response,
        name="update_search_result_response"
    ),

    path(
        "update_search_term/",
        views.update_search_term,
        name="update_search_term"
    ),





    ##################################################
    path("create_experiment/", views.create_experiment, name="create_experiment"),
    path("add_a_rule/", views.add_a_rule, name="add_a_rule"),
    path("proxy_image/", views.proxy_image, name="proxy_image"),
    path("get_sub_batch_options/", views.get_sub_batch_options, name="get_sub_batch_options"),
    path("create_sub_batch/", views.create_sub_batch, name="create_sub_batch"),
    path("get_reconcile_count/", views.get_reconcile_count, name="get_reconcile_count"),
]
