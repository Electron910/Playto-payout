#!/usr/bin/env bash
set -o errexit

celery -A playto worker -l info --concurrency=2 --beat --scheduler django_celery_beat.schedulers:DatabaseScheduler &

exec gunicorn playto.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 2 --timeout 120