import pandas as pd
import numpy as np
import os
import logging
from sqlalchemy import create_engine, text
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration

# Database Connections
DB_CONNECTION_PROD = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db_prod"
DB_CONNECTION_DEV = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db"

# Selection Parameters
SAMPLE_SIZE = 20000
MODEL_VERSION = "CF1_0.01"
RULE_INDEX = 1
PROB_MIN = 0.4
PROB_MAX = 0.6
MODEL_BATCH_LABEL = "CF1_0.01"

# Output Table
OUTPUT_TABLE = "label_data.selected_assets"


def get_engines():
    """Create and return database engines."""
    try:
        engine_prod = create_engine(DB_CONNECTION_PROD)
        engine_dev = create_engine(DB_CONNECTION_DEV)
        return engine_prod, engine_dev
    except Exception as e:
        logger.error(f"Failed to create DB engines: {e}")
        raise


def get_candidate_predictions(engine_prod):
    """Load candidate asset IDs from production DB based on model scores."""
    logger.info("Loading candidate predictions from PROD...")

    predictions_query = text(
        """
        SELECT asset_id
        FROM "model_predictions"."rule_labels"
        WHERE 
            task_type = 'color_fill_type' AND
            rule_index = :rule_index AND
            model_version = :model_version AND
            probability > :prob_min AND
            probability < :prob_max
    """
    )

    params = {
        "rule_index": RULE_INDEX,
        "model_version": MODEL_VERSION,
        "prob_min": PROB_MIN,
        "prob_max": PROB_MAX,
    }

    with engine_prod.connect() as conn:
        predictions_df = pd.read_sql(predictions_query, conn, params=params)

    logger.info(f"Found {len(predictions_df)} candidate predictions.")
    return predictions_df


def fetch_asset_details(engine_prod, asset_ids):
    """Fetch image links for specific asset IDs where s3 is True."""
    logger.info(f"Fetching details for {len(asset_ids)} assets from PROD...")

    if not asset_ids:
        return pd.DataFrame(columns=["asset_id", "image_link"])

    # Convert set to list
    ids_list = list(asset_ids)

    # Process in chunks to avoid query size limits
    chunk_size = 5000
    results = []

    total_chunks = (len(ids_list) + chunk_size - 1) // chunk_size

    with engine_prod.connect() as conn:
        for i in range(total_chunks):
            chunk = ids_list[i * chunk_size : (i + 1) * chunk_size]

            # Use string formatting for IN clause with integer IDs (safe for ints)
            # This avoids creating thousands of named parameters
            ids_str = ",".join(str(int(uid)) for uid in chunk)

            query = text(
                f"""
                SELECT asset_id, image_link
                FROM "content"."assets"
                WHERE s3 = TRUE
                AND asset_id IN ({ids_str})
            """
            )

            chunk_df = pd.read_sql(query, conn)
            results.append(chunk_df)

            if (i + 1) % 5 == 0:
                logger.info(f"Processed {i + 1}/{total_chunks} chunks...")

    if results:
        final_df = pd.concat(results, ignore_index=True)
    else:
        final_df = pd.DataFrame(columns=["asset_id", "image_link"])

    logger.info(f"Retrieved details for {len(final_df)} valid assets (S3=True).")
    return final_df


def get_existing_batch_info(engine_dev):
    """Get set of already selected asset_ids and the next batch_id."""
    logger.info("Checking existing selections in DEV...")

    # Read minimal data: only asset_id and batch_id
    query = f'SELECT asset_id, batch_id FROM "{OUTPUT_TABLE}"'

    try:
        existing_df = pd.read_sql(query, engine_dev)
        existing_ids = set(existing_df["asset_id"].unique())
        next_batch_id = (
            existing_df["batch_id"].max() + 1 if not existing_df.empty else 1
        )
        logger.info(
            f"Found {len(existing_ids)} already selected assets. Next batch ID: {next_batch_id}"
        )
        return existing_ids, int(next_batch_id)
    except Exception as e:
        # Table might not exist yet
        logger.warning(
            f"Could not read existing assets (table might be empty or missing): {e}"
        )
        return set(), 1


def process_new_batch():
    engine_prod, engine_dev = get_engines()

    # 1. Load Candidate IDs (Predictions)
    predictions_df = get_candidate_predictions(engine_prod)
    candidate_ids = set(predictions_df["asset_id"].unique())

    if not candidate_ids:
        logger.error("No predictions found matching criteria. Exiting.")
        return None

    # 2. Filter Existing (local set difference)
    existing_ids, next_batch_id = get_existing_batch_info(engine_dev)

    available_ids = candidate_ids - existing_ids
    logger.info(
        f"Assets available for selection after filtering existing: {len(available_ids)}"
    )

    if not available_ids:
        logger.error(
            "No available assets found after filtering existing ones! Exiting."
        )
        return None

    # 3. Fetch Asset Details (Check S3 status and get links)
    # We fetch details for ALL available candidates to ensure we only sample from valid S3 assets
    # This might load up to ~100k rows, which is acceptable compared to loading the whole table.
    available_assets_df = fetch_asset_details(engine_prod, available_ids)

    if available_assets_df.empty:
        logger.error("No assets found with S3=True among the candidates! Exiting.")
        return None

    logger.info(f"Assets with S3=True: {len(available_assets_df)}")

    # 4. Sample
    sample_n = min(SAMPLE_SIZE, len(available_assets_df))
    selected = available_assets_df.sample(n=sample_n, random_state=42).copy()
    logger.info(f"Selected {len(selected)} assets for Batch {next_batch_id}.")

    # 5. Add Detailed Columns
    date_now = datetime.now().strftime("%Y-%m-%d")

    # Initialize all required columns with default values
    # Metadata
    selected["batch_id"] = next_batch_id
    selected["date_created"] = date_now
    selected["model_batch"] = MODEL_BATCH_LABEL

    # Grouping/Sorting helpers
    selected["sub_batch"] = ((np.arange(len(selected)) // 5) + 1).astype(int)
    selected["large_sub_batch"] = ((np.arange(len(selected)) // 500) + 1).astype(int)

    # Labeling Placeholders (Detailed Columns)
    columns_defaults = {
        "label_count": 0,
        "clip_art_type": 0,  # Placeholder for user label
        "count": 0,  # Generic count tracker
        "line_width": 0,  # Placeholder for user label
        "color_depth": 0,  # Placeholder for user label
        "primary_color": 0,  # Placeholder for user label
        "asset_type": "undetermined",
        "color_type": "undetermined",
        # Add more if needed here
    }

    for col, default_val in columns_defaults.items():
        selected[col] = default_val

    # 6. Save to Database
    logger.info(f"Writing {len(selected)} rows to {OUTPUT_TABLE}...")

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
        # Re-raise or handle? Let's raise to alert user.
        raise

    return selected


# Run the process
if __name__ == "__main__":
    new_batch_df = process_new_batch()
    if new_batch_df is not None:
        print(
            f"Successfully created batch {new_batch_df['batch_id'].iloc[0]} with {len(new_batch_df)} assets."
        )
