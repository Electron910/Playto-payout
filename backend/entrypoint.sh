#!/bin/bash
set -e

echo "Running migrations..."
python manage.py makemigrations ledger --noinput
python manage.py migrate --noinput

echo "Seeding merchants..."
python manage.py seed_merchants

echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000