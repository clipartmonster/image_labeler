import json
import pathlib
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from elasticsearch import Elasticsearch

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

DB_CONNECTION_PROD = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db_prod"
DB_CONNECTION_DEV = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db"

ES_HOST = "http://localhost:9200"  # Update to your ES host
ES_INDEX = "minimum_comprehensive_index"

# Target unique similar images to add per misclassified asset
SIMILAR_PER_ASSET = 10
# How many candidates to fetch from ES before deduplication (buffer for cross-asset overlap)
SIMILAR_FETCH_SIZE = 15

# Model version / task scope to pull misclassifications for
MODEL_VERSION = "CF1_0.01"
TASK_TYPE = "color_fill_type"
RULE_INDEX = 1

# Batch label stamped on every written row
MODEL_BATCH_LABEL = f"misclassification_{MODEL_VERSION}"

OUTPUT_TABLE = "label_data.selected_assets_new"

# Optional: path to the JSON produced by embedding_labels.ipynb for assets
# that have no dino_embedding in ES. Set to None to skip.
LOCAL_SIMILAR_JSON = pathlib.Path(__file__).parent / "local_similar_results.json"

# ── Clients ──────────────────────────────────────────────────────────────────

es = Elasticsearch(ES_HOST)


def get_engines():
    """Create and return database engines for prod and dev."""
    try:
        engine_prod = create_engine(DB_CONNECTION_PROD)
        engine_dev = create_engine(DB_CONNECTION_DEV)
        return engine_prod, engine_dev
    except Exception as e:
        logger.error(f"Failed to create DB engines: {e}")
        raise


# ── Data Loading ─────────────────────────────────────────────────────────────


def get_misclassifications(engine_dev):
    """Load misclassified asset IDs from the dev DB for the configured model/task/rule."""
    logger.info(
        f"Loading misclassifications for model_version='{MODEL_VERSION}', "
        f"task_type='{TASK_TYPE}', rule_index={RULE_INDEX}..."
    )

    query = text(
        """
        SELECT asset_id
        FROM label_data.misclassifications
        WHERE model_version = :model_version
          AND task_type     = :task_type
          AND rule_index    = :rule_index
        """
    )
    with engine_dev.connect() as conn:
        df = pd.read_sql(
            query, conn,
            params={"model_version": MODEL_VERSION, "task_type": TASK_TYPE, "rule_index": RULE_INDEX},
        )

    logger.info(f"Found {len(df)} misclassified assets.")
    return df["asset_id"].unique().tolist()


def fetch_asset_details(engine_prod, asset_ids):
    """Fetch image_link for asset IDs where s3 = TRUE."""
    if not asset_ids:
        return pd.DataFrame(columns=["asset_id", "image_link"])

    logger.info(f"Fetching asset details for {len(asset_ids)} candidates from PROD...")

    chunk_size = 5000
    ids_list = list(asset_ids)
    results = []
    total_chunks = (len(ids_list) + chunk_size - 1) // chunk_size

    with engine_prod.connect() as conn:
        for i in range(total_chunks):
            chunk = ids_list[i * chunk_size : (i + 1) * chunk_size]
            ids_str = ",".join(str(int(uid)) for uid in chunk)
            query = text(
                f"""
                SELECT asset_id, image_link
                FROM content.assets
                WHERE s3 = TRUE
                AND asset_id IN ({ids_str})
                """
            )
            results.append(pd.read_sql(query, conn))
            if (i + 1) % 5 == 0:
                logger.info(f"  Processed {i + 1}/{total_chunks} chunks...")

    final_df = (
        pd.concat(results, ignore_index=True)
        if results
        else pd.DataFrame(columns=["asset_id", "image_link"])
    )
    logger.info(f"Retrieved {len(final_df)} assets with S3=True.")
    return final_df


def get_existing_batch_info(engine_dev):
    """Return asset IDs already selected for this task_type/rule_index, and the next batch_id scoped to this feature."""
    logger.info(
        f"Checking existing selections for task_type='{TASK_TYPE}', rule_index={RULE_INDEX}..."
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
            f"Found {len(existing_ids)} already-selected assets for this task/rule. "
            f"Next batch ID (scoped to {TASK_TYPE}/rule {RULE_INDEX}): {next_batch_id}"
        )
        return existing_ids, next_batch_id
    except Exception as e:
        logger.warning(
            f"Could not read existing assets (table may be empty/missing): {e}"
        )
        return set(), 1


# ── Elasticsearch ─────────────────────────────────────────────────────────────


def fetch_dino_embedding(asset_id):
    """Return the dino_embedding vector for a single asset, or None if missing."""
    query = {
        "size": 1,
        "_source": ["dino_embedding"],
        "query": {"term": {"asset_id": asset_id}},
    }
    result = es.search(index=ES_INDEX, body=query)
    hits = result["hits"]["hits"]
    if not hits:
        return None
    return hits[0]["_source"].get("dino_embedding")


def fetch_similar_by_dino(asset_id, fetch=SIMILAR_FETCH_SIZE):
    """Fetch `fetch` nearest DINO neighbors from ES, excluding the source asset itself."""
    dino_embedding = fetch_dino_embedding(asset_id)
    if dino_embedding is None:
        logger.debug(f"No dino_embedding found for asset_id={asset_id}, skipping.")
        return []

    knn_query = {
        "size": fetch + 1,  # +1 in case the source asset appears in results
        "knn": {
            "field": "dino_embedding",
            "query_vector": dino_embedding,
            "k": fetch + 1,
            "num_candidates": 10000,
        },
        "_source": ["asset_id"],
    }
    knn_results = es.search(index=ES_INDEX, body=knn_query)
    similar_ids = [
        hit["_source"]["asset_id"]
        for hit in knn_results["hits"]["hits"]
        if hit["_source"]["asset_id"] != asset_id
    ]
    return similar_ids[:fetch]


# ── Main Process ──────────────────────────────────────────────────────────────


def process_misclassification_batch():
    engine_prod, engine_dev = get_engines()

    # 1. Load misclassified asset IDs
    misclassified_ids = get_misclassifications(engine_dev)
    if not misclassified_ids:
        logger.error("No misclassifications found. Exiting.")
        return None

    # 2. Load locally-computed similar results (from embedding_labels.ipynb) if available
    local_similar: dict = {}
    if LOCAL_SIMILAR_JSON and LOCAL_SIMILAR_JSON.exists():
        with open(LOCAL_SIMILAR_JSON) as f:
            raw = json.load(f)
        local_similar = {int(k): v for k, v in raw.items()}
        logger.info(
            f"Loaded local similar results for {len(local_similar)} assets from {LOCAL_SIMILAR_JSON.name}."
        )

    # 3. Find similar images for each misclassified asset
    # The misclassified assets themselves are always included; similar images are supplementary.
    logger.info(
        f"Fetching {SIMILAR_PER_ASSET} DINO-similar images for each of "
        f"{len(misclassified_ids)} misclassified assets..."
    )
    candidate_ids = set(misclassified_ids)  # always include the misclassified assets
    no_embedding_count = 0
    for i, asset_id in enumerate(misclassified_ids, 1):
        # Prefer ES; fall back to locally-computed results from the notebook
        similar = fetch_similar_by_dino(asset_id)
        if not similar:
            similar = local_similar.get(asset_id, [])
            if not similar:
                no_embedding_count += 1

        # Add up to SIMILAR_PER_ASSET IDs that are not already in the candidate set
        new_added = 0
        for sid in similar:
            if sid not in candidate_ids:
                candidate_ids.add(sid)
                new_added += 1
                if new_added == SIMILAR_PER_ASSET:
                    break

        if i % 100 == 0:
            logger.info(
                f"  Processed {i}/{len(misclassified_ids)} misclassified assets..."
            )

    logger.info(
        f"Collected {len(candidate_ids)} unique candidates "
        f"({len(misclassified_ids)} misclassified + similar images). "
        f"{no_embedding_count}/{len(misclassified_ids)} misclassified assets had no embedding in ES or local cache."
    )

    # 3. Filter out already-selected assets
    existing_ids, next_batch_id = get_existing_batch_info(engine_dev)
    available_ids = candidate_ids - existing_ids
    logger.info(f"Available candidates after removing existing: {len(available_ids)}")

    if not available_ids:
        logger.error("No new candidates available after filtering. Exiting.")
        return None

    # 4. Fetch asset details (validates S3=True and gets image_link)
    assets_df = fetch_asset_details(engine_prod, available_ids)
    if assets_df.empty:
        logger.error("No candidates have S3=True. Exiting.")
        return None

    # 5. Assign batch metadata
    date_now = datetime.now().strftime("%Y-%m-%d")
    assets_df = assets_df.copy().reset_index(drop=True)

    assets_df["batch_id"] = next_batch_id
    assets_df["date_created"] = date_now
    assets_df["model_batch"] = MODEL_BATCH_LABEL
    assets_df["task_type"] = TASK_TYPE
    assets_df["rule_index"] = RULE_INDEX

    assets_df["sub_batch"] = ((np.arange(len(assets_df)) // 5) + 1).astype(int)
    assets_df["large_sub_batch"] = ((np.arange(len(assets_df)) // 500) + 1).astype(int)

    # Labeling placeholders
    assets_df["label_count"] = 0
    assets_df["clip_art_type"] = 0
    assets_df["count"] = 0
    assets_df["line_width"] = 0
    assets_df["color_depth"] = 0
    assets_df["primary_color"] = 0
    assets_df["asset_type"] = "undetermined"
    assets_df["color_type"] = "undetermined"

    logger.info(
        f"Writing {len(assets_df)} rows across "
        f"{assets_df['large_sub_batch'].max()} large sub-batch(es) to {OUTPUT_TABLE}..."
    )

    # 6. Write to dev DB
    try:
        with engine_dev.begin() as conn:
            assets_df.to_sql(
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

    return assets_df


if __name__ == "__main__":
    result_df = process_misclassification_batch()
    if result_df is not None:
        print(
            f"Successfully created batch {result_df['batch_id'].iloc[0]} "
            f"with {len(result_df)} assets "
            f"({result_df['large_sub_batch'].max()} large sub-batches of up to 500)."
        )
