import pandas as pd
import numpy as np
import time

from sqlalchemy import create_engine, text

DB_CONNECTION_PROD = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db_prod"
DB_CONNECTION_DEV = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db"

engine = create_engine(DB_CONNECTION_PROD)
engine_dev = create_engine(DB_CONNECTION_DEV)

connection = engine.connect()
connection_dev = engine_dev.connect()

t = time.time()
prompt_data = pd.read_sql('SELECT * FROM "label_data.prompt_responses"', connection_dev)
print(f"prompt_data: {len(prompt_data)} rows in {time.time()-t:.1f}s")

t = time.time()
current_data = pd.read_sql(
    'SELECT * FROM "label_data.asset_type.rule.labels"', connection_dev
)
print(f"current_data: {len(current_data)} rows in {time.time()-t:.1f}s")

_COLS = ["asset_id", "task_type", "rule_index", "label", "percent_agree",
         "label_strength", "label_source"]

# color_fill_type rule 5 is an ordinal 0-3 scale (graded Color Depth), not yes/no.
# It reuses the same tables but is reconciled by median instead of yes-rate.
ordinal_mask = (prompt_data.task_type == "color_fill_type") & (prompt_data.rule_index == 5)
binary_data = prompt_data[~ordinal_mask]
ordinal_data = prompt_data[ordinal_mask]

print("loading binary label set")
binary_label_set = (
    binary_data.assign(
        yes_response=lambda x: np.where(x.prompt_response == "yes", 1, 0)
    )
    .groupby(["asset_id", "task_type", "rule_index"])
    .agg(agree_count=("yes_response", "sum"), samples=("asset_id", "count"))
    .query("samples > 1")
    .assign(percent_agree=lambda x: x.agree_count / x.samples)
    .query("percent_agree != .5")
    .assign(label=lambda x: np.where(x.percent_agree < 0.5, 0, 1))
    .filter(["asset_id", "label", "percent_agree"])
    .assign(label_strength="weak")
    .assign(
        label_strength=lambda x: np.where(
            (x.percent_agree == 0) | (x.percent_agree == 1), "strong", x.label_strength
        )
    )
    .assign(label_source="Internal")
    .reset_index()
)[_COLS]

print("loading ordinal label set (color_fill_type rule 5)")
if len(ordinal_data):
    _o = ordinal_data.assign(
        val=lambda x: pd.to_numeric(x.prompt_response, errors="coerce")
    ).dropna(subset=["val"])
    _grp = _o.groupby(["asset_id", "task_type", "rule_index"])["val"]
    _med = _grp.median().round().astype(int).rename("label")
    _samples = _grp.size().rename("samples")
    _tmp = _o.merge(_med.reset_index(), on=["asset_id", "task_type", "rule_index"])
    _tmp["match"] = _tmp.val.round().astype(int) == _tmp.label
    _agree = (
        _tmp.groupby(["asset_id", "task_type", "rule_index"])["match"]
        .mean()
        .rename("percent_agree")
    )
    ordinal_label_set = (
        pd.concat([_med, _samples, _agree], axis=1)
        .reset_index()
        .query("samples > 1")
        .assign(
            label_strength=lambda x: np.where(x.percent_agree == 1, "strong", "weak"),
            label_source="Internal",
        )
    )[_COLS]
else:
    ordinal_label_set = pd.DataFrame(columns=_COLS)

label_set = pd.concat([binary_label_set, ordinal_label_set], ignore_index=True)

print("loading current count")
current_count = (
    current_data.groupby(["task_type", "rule_index"])
    .agg(current_count=("rule_index", "count"))
    .reset_index()
)

soon_to_be_count = (
    label_set.groupby(["task_type", "rule_index"])
    .agg(soon_to_be_count=("rule_index", "count"))
    .reset_index()
)

current_count.merge(
    soon_to_be_count, on=["task_type", "rule_index"], how="left"
).assign(difference=lambda x: x.soon_to_be_count - x.current_count)

new_rows = (
    label_set.merge(
        current_data[["asset_id", "task_type", "rule_index"]],
        on=["asset_id", "task_type", "rule_index"],
        how="left",
        indicator=True,
    )
    .query('_merge == "left_only"')
    .drop(columns="_merge")
)

print(f"new rows to insert: {len(new_rows)} of {len(label_set)} total")

t = time.time()
new_rows.to_sql(
    "label_data.asset_type.rule.labels",
    con=engine_dev,
    if_exists="append",
    index=False,
    method="multi",
    chunksize=1000,
)
print(f"saved in {time.time()-t:.1f}s")

print("done")
# prompt_data \
#     .query('task_type == "color_fill_type"') \
#     .query('rule_index == 2') \
#     .groupby(['asset_id', 'labeler_id']) \
#     .agg(count = ('asset_id','count')) \
#     .reset_index() \
#     .query('count == 1') \
#     .groupby('labeler_id') \
#     .agg(count = ('asset_id','count'))
