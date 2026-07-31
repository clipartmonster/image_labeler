"""Create a select_content labeling batch from the curated clip-art list.

Reads candidate asset IDs from prod ``model_predictions.clip_art``, resolves
``image_link``/``page_link`` from prod ``content.assets`` (s3=True), verifies
the original listing page is still reachable (drops 404/410 links), then
appends rows to dev ``label_data.select_content_assets``.

This is the offline equivalent of Add Sub-batch for the select_content task.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
import urllib3
from sqlalchemy import create_engine, text

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database Connections (same pattern as create_new_batch_cursor.py)
DB_CONNECTION_PROD = "postgresql+psycopg2://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db_prod"
DB_CONNECTION_DEV = "postgresql+psycopg2://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db"

# Selection Parameters
# Total assets to queue in this batch (set to None to take every eligible asset).
SAMPLE_SIZE = 20000
TASK_TYPE = "select_content"
RULE_INDEX = 1
# Each batch is split into large sub-batches of this many assets.
LARGE_SUB_BATCH_SIZE = 500

# Page-link validation. An asset is only queued when its original listing page
# is still reachable (we intend to link to it from social posts).
PAGE_CHECK_WORKERS = 20
PAGE_CHECK_TIMEOUT = 10  # seconds per request
# Status codes that mean the page is gone. Other failures (timeouts, 5xx,
# 429, bot-blocking 403s) are treated as reachable so temporary blips don't
# discard good assets.
DEAD_STATUS_CODES = {404, 410}

OUTPUT_TABLE = "label_data.select_content_assets"


def get_engines():
    """Create and return database engines."""
    try:
        engine_prod = create_engine(DB_CONNECTION_PROD)
        engine_dev = create_engine(DB_CONNECTION_DEV)
        return engine_prod, engine_dev
    except Exception as e:
        logger.error(f"Failed to create DB engines: {e}")
        raise


def get_clip_art_candidates(engine_prod):
    """Load curated clip-art asset IDs from the prod materialized view."""
    logger.info("Loading candidates from model_predictions.clip_art (PROD)...")
    query = text("SELECT asset_id FROM model_predictions.clip_art")
    with engine_prod.connect() as conn:
        df = pd.read_sql(query, conn)
    logger.info(f"Found {len(df)} clip-art candidates.")
    return df


def fetch_asset_details(engine_prod, asset_ids):
    """Fetch image and page links for specific asset IDs where s3 is True."""
    logger.info(f"Fetching details for {len(asset_ids)} assets from PROD...")

    if not asset_ids:
        return pd.DataFrame(columns=["asset_id", "image_link", "page_link"])

    ids_list = list(asset_ids)
    chunk_size = 5000
    results = []
    total_chunks = (len(ids_list) + chunk_size - 1) // chunk_size

    with engine_prod.connect() as conn:
        for i in range(total_chunks):
            chunk = ids_list[i * chunk_size : (i + 1) * chunk_size]
            ids_str = ",".join(str(int(uid)) for uid in chunk)
            query = text(
                f"""
                SELECT asset_id, image_link, page_link
                FROM "content"."assets"
                WHERE s3 = TRUE
                AND asset_id IN ({ids_str})
                """
            )
            results.append(pd.read_sql(query, conn))
            if (i + 1) % 5 == 0:
                logger.info(f"Processed {i + 1}/{total_chunks} chunks...")

    if results:
        final_df = pd.concat(results, ignore_index=True)
    else:
        final_df = pd.DataFrame(columns=["asset_id", "image_link", "page_link"])

    logger.info(f"Retrieved details for {len(final_df)} valid assets (S3=True).")
    return final_df


def page_is_reachable(page_link):
    """Return True when the original listing page does not appear dead.

    Only definitive "gone" statuses (404/410) disqualify an asset. Network
    errors and transient statuses count as reachable to avoid discarding
    assets over temporary problems.
    """
    if not isinstance(page_link, str) or not page_link.startswith("http"):
        return False
    try:
        response = requests.get(
            page_link,
            timeout=PAGE_CHECK_TIMEOUT,
            verify=False,
            allow_redirects=True,
            stream=True,  # don't download the body
            headers={"User-Agent": "Mozilla/5.0 (page-link check)"},
        )
        response.close()
        return response.status_code not in DEAD_STATUS_CODES
    except requests.RequestException:
        return True


def filter_reachable_pages(df):
    """Drop rows whose page_link returns a dead status (404/410)."""
    logger.info(
        f"Checking page links for {len(df)} assets "
        f"({PAGE_CHECK_WORKERS} workers)..."
    )
    reachable_flags = {}
    with ThreadPoolExecutor(max_workers=PAGE_CHECK_WORKERS) as executor:
        futures = {
            executor.submit(page_is_reachable, row.page_link): row.asset_id
            for row in df.itertuples()
        }
        for i, future in enumerate(as_completed(futures), 1):
            asset_id = futures[future]
            reachable_flags[asset_id] = future.result()
            if i % 500 == 0:
                logger.info(f"  Checked {i}/{len(futures)} pages...")

    df = df.copy()
    df["page_ok"] = df["asset_id"].map(reachable_flags)
    dead = int((~df["page_ok"]).sum())
    logger.info(f"Page check complete: {dead} dead links dropped.")
    return df[df["page_ok"]].drop(columns=["page_ok"])


def get_existing_batch_info(engine_dev):
    """Return already-queued asset IDs and the next batch_id for select_content."""
    logger.info(
        f"Checking existing selections for task_type='{TASK_TYPE}', "
        f"rule_index={RULE_INDEX}..."
    )
    try:
        all_df = pd.read_sql(
            f'SELECT asset_id, batch_id, task_type, rule_index FROM "{OUTPUT_TABLE}"',
            engine_dev,
        )
        scoped = all_df[
            (all_df["task_type"] == TASK_TYPE) & (all_df["rule_index"] == RULE_INDEX)
        ]
        existing_ids = set(scoped["asset_id"].unique())
        next_batch_id = int(scoped["batch_id"].max() + 1) if not scoped.empty else 1
        logger.info(
            f"Found {len(existing_ids)} already-selected assets. "
            f"Next batch ID: {next_batch_id}"
        )
        return existing_ids, next_batch_id
    except Exception as e:
        logger.warning(
            f"Could not read existing assets (table may be empty/missing): {e}"
        )
        return set(), 1


def process_new_batch():
    engine_prod, engine_dev = get_engines()

    # 1. Load curated clip-art IDs
    candidates_df = get_clip_art_candidates(engine_prod)
    candidate_ids = set(candidates_df["asset_id"].unique())
    if not candidate_ids:
        logger.error("No clip-art candidates found. Exiting.")
        return None

    # 2. Remove already queued
    existing_ids, next_batch_id = get_existing_batch_info(engine_dev)
    available_ids = candidate_ids - existing_ids
    logger.info(
        f"Assets available after filtering existing: {len(available_ids)}"
    )
    if not available_ids:
        logger.error("No available assets after filtering existing ones. Exiting.")
        return None

    # 3. Resolve image links (s3=True)
    available_assets_df = fetch_asset_details(engine_prod, available_ids)
    if available_assets_df.empty:
        logger.error("No assets found with S3=True among the candidates. Exiting.")
        return None

    # 4. Sample (oversample so dead page links can be replaced), then verify
    #    the original listing pages are reachable.
    if SAMPLE_SIZE is None:
        candidates = available_assets_df.sample(frac=1, random_state=42)
    else:
        # 15% extra to absorb dead links while still hitting SAMPLE_SIZE.
        oversample_n = min(int(SAMPLE_SIZE * 1.15), len(available_assets_df))
        candidates = available_assets_df.sample(n=oversample_n, random_state=42)

    candidates = filter_reachable_pages(candidates.reset_index(drop=True))
    if candidates.empty:
        logger.error("No assets with reachable page links. Exiting.")
        return None

    if SAMPLE_SIZE is not None:
        candidates = candidates.head(SAMPLE_SIZE)

    selected = candidates.drop(columns=["page_link"]).reset_index(drop=True)
    logger.info(f"Selected {len(selected)} assets for Batch {next_batch_id}.")

    # 5. Add columns matching select_content_assets
    now = datetime.now(timezone.utc)
    selected["batch_id"] = next_batch_id
    selected["large_sub_batch"] = (
        (np.arange(len(selected)) // LARGE_SUB_BATCH_SIZE) + 1
    ).astype(int)
    selected["task_type"] = TASK_TYPE
    selected["rule_index"] = RULE_INDEX
    selected["status"] = "queued"
    selected["date_created"] = now
    selected["date_updated"] = now

    selected = selected[
        [
            "asset_id",
            "image_link",
            "batch_id",
            "large_sub_batch",
            "task_type",
            "rule_index",
            "status",
            "date_created",
            "date_updated",
        ]
    ]

    # 6. Write to DEV queue
    logger.info(
        f"Writing {len(selected)} rows to {OUTPUT_TABLE} "
        f"(batch_id={next_batch_id}, "
        f"large_sub_batches=1..{selected['large_sub_batch'].max()})..."
    )
    try:
        with engine_dev.begin() as conn:
            selected.to_sql(
                name=OUTPUT_TABLE,
                con=conn,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi",
            )
        logger.info("Batch write successful!")
    except Exception as e:
        logger.error(f"Failed to write to database: {e}")
        raise

    return selected


if __name__ == "__main__":
    new_batch_df = process_new_batch()
    if new_batch_df is not None:
        print(
            f"Successfully created batch {new_batch_df['batch_id'].iloc[0]} "
            f"with {len(new_batch_df)} assets "
            f"({new_batch_df['large_sub_batch'].max()} large sub-batch(es) of "
            f"up to {LARGE_SUB_BATCH_SIZE})."
        )
