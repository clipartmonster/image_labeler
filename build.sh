#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

cd image_labeler
python manage.py collectstatic --noinput