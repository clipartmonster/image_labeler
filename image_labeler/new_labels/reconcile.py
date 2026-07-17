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

# color_fill_type rule 5 is a graded Color Depth scale, not yes/no. Responses are
# "0" (Flat), an integer >= 1 (counted depth layers), or "gradient" (continuous
# shading). It reuses the same tables and is reconciled by plurality (majority
# vote), exactly like the yes/no rules -- assets with no clear winner are left
# out here and resolved by a human in the reconcile review UI. "gradient" is
# encoded as 99 so it sorts above any countable depth.
GRADIENT_CODE = 99
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

print("loading graded label set (color_fill_type rule 5)")
if len(ordinal_data):
    _o = ordinal_data.assign(
        val=lambda x: pd.to_numeric(
            x.prompt_response.astype(str).str.strip().str.lower()
            .replace({"gradient": str(GRADIENT_CODE)}),
            errors="coerce",
        )
    ).dropna(subset=["val"])
    _o["val"] = _o["val"].astype(int)

    # Reconcile by plurality (majority vote), matching the binary rules. Assets
    # with no strict winner (a tie for the top vote count) are left out here so
    # they surface in the reconcile review UI, just like the 50/50 ties do for
    # yes/no rules.
    _counts = (
        _o.groupby(["asset_id", "task_type", "rule_index", "val"])
        .size().rename("n").reset_index()
    )
    _counts["max_n"] = _counts.groupby(
        ["asset_id", "task_type", "rule_index"]
    )["n"].transform("max")
    _top = _counts[_counts.n == _counts.max_n]
    _agg = (
        _top.groupby(["asset_id", "task_type", "rule_index"])
        .agg(label=("val", "min"), n_top=("val", "size"), max_n=("n", "max"))
        .reset_index()
    )
    _samples = (
        _counts.groupby(["asset_id", "task_type", "rule_index"])["n"]
        .sum().rename("samples").reset_index()
    )
    ordinal_label_set = (
        _agg.merge(_samples, on=["asset_id", "task_type", "rule_index"])
        .query("samples > 1")
        .query("n_top == 1")
        .assign(
            label=lambda x: x.label.astype(int),
            percent_agree=lambda x: x.max_n / x.samples,
            label_strength=lambda x: np.where(x.max_n == x.samples, "strong", "weak"),
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
