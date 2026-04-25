#!/bin/bash
set -e

echo "Waiting for DB tables to be ready..."
python wait_for_db.py

echo "Starting Celery beat..."
exec celery -A playto beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler