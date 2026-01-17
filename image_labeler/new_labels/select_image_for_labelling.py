import pandas as pd
import numpy as np

import random
import string
import os
import boto3

import functions as f

from sqlalchemy import text
import requests

from datetime import datetime, timedelta
import random

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from concurrent.futures import ThreadPoolExecutor, as_completed

import time
import random
from io import BytesIO


def download_and_upload(row, label_directory, batch_id):
    index = row.name  # If using iterrows()
    if not row.image_link.startswith("http"):
        return None

    try:
        # Random sleep between 0.5 and 2.5 seconds
        time.sleep(random.uniform(0.5, 2.5))

        response = requests.get(row.image_link, verify=False, timeout=10)
        if response.status_code == 200:
            file_name = f"{row.asset_id}.jpg"
            file_path = os.path.join(label_directory, file_name)

            with open(file_path, "wb") as f:
                f.write(response.content)

            s3.upload_file(
                file_path,
                "clip-art-monster-images-for-labeling",
                f"batch_{batch_id}/{file_name}",
            )
            return index
        else:
            print(f"[{index}] Failed: Status code {response.status_code}")
    except Exception as e:
        print(f"[{index}] Exception: {e}")
    return None


db_connection_string = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db_prod"
db_connection_string_dev = "postgresql+pg8000://clipart_monster_db_user:iV0BUFPv0rMLu5MKVXesLlvFT3E6MneJ@dpg-cocp8eq0si5c73an4rp0-a.ohio-postgres.render.com/clipart_monster_db"

# Create engine
engine = create_engine(db_connection_string)
engine_dev = create_engine(db_connection_string_dev)

connection_prod = engine.connect()
asset_data = pd.read_sql('SELECT * FROM "content"."assets"', connection)

image_links = asset_data.query("s3 == True").filter(["asset_id", "image_link"])


model_scores = pd.read_sql(
    'SELECT * FROM "model_predictions"."rule_labels"', connection
)

filtered_assets = (
    model_scores.query('task_type == "color_fill_type"')
    .query("rule_index == 1")
    .query('model_version == "CF1_0.01"')
    .query("probability > .4")
    .query("probability < .6")
)

# Get the table that contains all images avaiable for labelling
connection_dev = engine_dev.connect()
label_image_table = pd.read_sql(
    'SELECT * FROM "label_data.selected_assets"', connection
)


######################
# increment batch id by 1
batch_id = np.max(label_image_table.batch_id) + 1

######################
# remove already selected assets
is_selected = label_image_table.filter(["asset_id"]).assign(selected="yes")

avaiable_assets = (
    filtered_assets.merge(image_links, on="asset_id", how="left")
    .merge(is_selected, on="asset_id", how="left")
    .query('selected != "yes"')
)


# set the label directory
label_directory = "C:/Documents/labeling/batch_" + str(batch_id) + "/"

os.makedirs(label_directory)

######################
# build asset table

date = datetime.now().strftime("%Y-%m-%d")

selected_assets = (
    avaiable_assets.sample(20000)
    .filter(["asset_id", "image_link"])
    .assign(batch_id=batch_id)
    .assign(date_created=date)
    .assign(label_count=0)
    .assign(clip_art_type=0)
    .assign(count=0)
    .assign(line_width=0)
    .assign(color_depth=0)
    .assign(primary_color=0)
    .assign(model_batch="A5_0.02")
    .reset_index()
    .drop(["index"], axis=1)
)


successful_downloads = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = [
        executor.submit(download_and_upload, row, label_directory, batch_id)
        for _, row in selected_assets.iterrows()
    ]

    for i, future in enumerate(as_completed(futures), 1):
        result = future.result()
        print(f"{i} out of {len(selected_assets)}")
        if result is not None:
            successful_downloads.append(result)

# for index, row in selected_assets.iterrows():

#     # if index < 1414:
#     #     continue

#     print( str(index) + ' out of ' + str(len(selected_assets)))

#     if row.image_link.startswith('http'):

#         response = requests.get(row.image_link, verify = False)

#         file_name = str(row.asset_id) + '.jpg'
#         file_path = label_directory + file_name

#         if response.status_code == 200:
#             # Write the image content to the file
#             with open(file_path, 'wb') as file:
#                 file.write(response.content)
#             # print(f"Image downloaded successfully: {file_path}")
#             successful_downloads.append(index)


#             s3_bucket = 'clip-art-monster-images-for-labeling'
#             object_name = 'batch_' + str(batch_id) + '/' + file_name

#             s3.upload_file(file_path, s3_bucket, object_name)


#         else:
#             print(f"Failed to download image. Status code: {response.status_code}")
#             print(f"Image link: {row.image_link}")
#             print(f"Asset ID: {row.asset_id}")

# Filter the DataFrame to keep only the rows with successful downloads
selected_assets = selected_assets.loc[successful_downloads]

# Reset the index if needed
selected_assets = selected_assets.reset_index(drop=True)

temp = selected_assets.copy()

temp["sub_batch"] = ((temp.index // 5) + 1).astype(int)
temp["large_sub_batch"] = ((temp.index // 500) + 1).astype(int)
temp["asset_type"] = "undetermined"
temp["color_type"] = "undetermined"


# temp \
#     .to_sql('label_data.selected_assets',
#             con = connection,
#             if_exists='append',index = False)
