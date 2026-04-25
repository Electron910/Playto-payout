#!/bin/bash
set -e

echo "Waiting for DB tables to be ready..."
python wait_for_db.py

echo "Starting Celery worker..."
exec celery -A playto worker -l info --concurrency=4