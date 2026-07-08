-- Performance indexes for the labeling app.
-- Run once against the production PostgreSQL database.
-- All tables are unmanaged (Django does not create or migrate them),
-- so indexes must be added manually.

-- -------------------------------------------------------------------------
-- label_data.selected_assets_new
-- -------------------------------------------------------------------------

-- Primary filter in get_asset_batch and get_session_options
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_san_task_rule
    ON label_data.selected_assets_new (task_type, rule_index);

-- Secondary filter for sub-batch selection in get_asset_batch
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_san_batch_subbatch
    ON label_data.selected_assets_new (batch_id, large_sub_batch);

-- -------------------------------------------------------------------------
-- label_data.prompt_responses
-- -------------------------------------------------------------------------

-- Used in both get_asset_batch (exclude completed) and get_session_options (count per rule)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pr_task_rule
    ON label_data.prompt_responses (task_type, rule_index);

-- Fine-grained lookup by asset when counting per-rule completions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pr_asset_task_rule
    ON label_data.prompt_responses (asset_id, task_type, rule_index);

-- -------------------------------------------------------------------------
-- label_data.label_issues
-- -------------------------------------------------------------------------

-- Used to exclude flagged assets in every batch/session query
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_li_asset
    ON label_data.label_issues (asset_id);

-- -------------------------------------------------------------------------
-- label_data.labelling_rules
-- -------------------------------------------------------------------------

-- Filtered by task_type on every setup_session load
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lr_task_type
    ON label_data.labelling_rules (task_type);

-- -------------------------------------------------------------------------
-- label_data.line_width_samples  (line_width_type path)
-- -------------------------------------------------------------------------

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lws_asset
    ON label_data.line_width_samples (asset_id);
