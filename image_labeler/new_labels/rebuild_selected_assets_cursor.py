import pandas as pd
import numpy as np
import logging
from sqlalchemy import create_engine, text
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DB_CONNECTION_PROD = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db_prod"
DB_CONNECTION_DEV = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db"

OUTPUT_TABLE = "label_data.selected_assets_new"
BATCH_SIZE = 20000
LARGE_SUB_BATCH_SIZE = 500
SUB_BATCH_SIZE = 5


def get_engines():
    engine_prod = create_engine(DB_CONNECTION_PROD)
    engine_dev = create_engine(DB_CONNECTION_DEV)
    return engine_prod, engine_dev


def load_reconciled_labels(engine_dev):
    """Load all reconciled labels grouped by (task_type, rule_index)."""
    logger.info("Loading reconciled labels from rule.labels...")
    df = pd.read_sql(
        'SELECT DISTINCT asset_id, task_type, rule_index FROM "label_data.asset_type.rule.labels"',
        engine_dev,
    )
    logger.info(f"Loaded {len(df)} label rows across {df.groupby(['task_type','rule_index']).ngroups} features.")
    return df


def fetch_image_links(engine_prod, asset_ids):
    """Fetch image_link for asset_ids from content.assets (prod) in chunks."""
    logger.info(f"Fetching image links for {len(asset_ids)} unique assets...")
    ids_list = list(asset_ids)
    chunk_size = 5000
    results = []

    with engine_prod.connect() as conn:
        for i in range(0, len(ids_list), chunk_size):
            chunk = ids_list[i : i + chunk_size]
            ids_str = ",".join(str(int(uid)) for uid in chunk)
            query = text(
                f'SELECT asset_id, image_link FROM "content"."assets" WHERE s3 = TRUE AND asset_id IN ({ids_str})'
            )
            results.append(pd.read_sql(query, conn))
            done = min(i + chunk_size, len(ids_list))
            if done % 25000 < chunk_size:
                logger.info(f"  ...fetched {done}/{len(ids_list)}")

    links_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=["asset_id", "image_link"])
    logger.info(f"Got image links for {len(links_df)} assets (s3=True).")
    return links_df


def build_batched_rows(labels_df, links_df):
    """For each (task_type, rule_index), assign batch_id, sub_batch, large_sub_batch."""
    merged = labels_df.merge(links_df, on="asset_id", how="inner")
    dropped = len(labels_df) - len(merged)
    if dropped:
        logger.warning(f"{dropped} assets dropped (no s3 image link).")

    date_now = datetime.now().strftime("%Y-%m-%d")
    all_rows = []

    features = merged.groupby(["task_type", "rule_index"])
    logger.info(f"Building batches for {features.ngroups} features...")

    for (task_type, rule_index), group in features:
        group = group.sample(frac=1, random_state=42).reset_index(drop=True)
        n = len(group)

        batch_ids = (np.arange(n) // BATCH_SIZE) + 1
        within_batch_idx = np.arange(n) % BATCH_SIZE
        large_sub_batches = (within_batch_idx // LARGE_SUB_BATCH_SIZE) + 1
        sub_batches = (within_batch_idx // SUB_BATCH_SIZE) + 1

        group = group.copy()
        group["batch_id"] = batch_ids.astype(int)
        group["sub_batch"] = sub_batches.astype(int)
        group["large_sub_batch"] = large_sub_batches.astype(int)
        group["date_created"] = date_now
        group["task_type"] = task_type
        group["rule_index"] = int(rule_index)

        group["label_count"] = 0
        group["clip_art_type"] = 0
        group["count"] = 0
        group["line_width"] = 0
        group["color_depth"] = 0
        group["primary_color"] = 0
        group["asset_type"] = "undetermined"
        group["color_type"] = "undetermined"
        group["model_batch"] = None
        group["multi_element"] = None

        num_batches = batch_ids.max()
        logger.info(
            f"  {task_type}/rule_{rule_index}: {n} assets -> {num_batches} batch(es), "
            f"max large_sub_batch={large_sub_batches.max()}"
        )
        all_rows.append(group)

    final = pd.concat(all_rows, ignore_index=True)

    column_order = [
        "asset_id", "image_link", "batch_id", "date_created",
        "label_count", "clip_art_type", "count", "line_width",
        "color_depth", "primary_color", "sub_batch", "large_sub_batch",
        "asset_type", "color_type", "model_batch", "multi_element",
        "task_type", "rule_index",
    ]
    final = final[column_order]
    return final


def write_to_db(engine_dev, df):
    """Write the dataframe to the output table, replacing any existing data."""
    logger.info(f"Writing {len(df)} rows to {OUTPUT_TABLE}...")
    with engine_dev.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{OUTPUT_TABLE}"'))

    with engine_dev.begin() as conn:
        df.to_sql(
            name=OUTPUT_TABLE,
            con=conn,
            if_exists="append",
            index=False,
            chunksize=2000,
            method="multi",
        )
    logger.info("Write complete.")


def main():
    engine_prod, engine_dev = get_engines()

    labels_df = load_reconciled_labels(engine_dev)
    unique_assets = labels_df["asset_id"].unique()
    links_df = fetch_image_links(engine_prod, unique_assets)

    final_df = build_batched_rows(labels_df, links_df)

    summary = (
        final_df.groupby(["task_type", "rule_index"])
        .agg(assets=("asset_id", "count"), batches=("batch_id", "nunique"))
        .reset_index()
    )
    logger.info(f"\n--- Summary ---\n{summary.to_string(index=False)}\n")
    logger.info(f"Total rows: {len(final_df)}")

    confirm = input(f"Write {len(final_df)} rows to {OUTPUT_TABLE}? (yes/no): ").strip().lower()
    if confirm != "yes":
        logger.info("Aborted.")
        return

    write_to_db(engine_dev, final_df)
    logger.info("Done! Table created: " + OUTPUT_TABLE)


if __name__ == "__main__":
    main()
