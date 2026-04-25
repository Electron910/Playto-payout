#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py makemigrations ledger --noinput
python manage.py migrate --noinput
python manage.py seed_merchants