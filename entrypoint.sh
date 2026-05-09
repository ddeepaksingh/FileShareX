#!/bin/sh
set -e

echo ">>> Applying database migrations..."
python manage.py migrate --no-input

echo ">>> Collecting static files..."
python manage.py collectstatic --no-input --clear

echo ">>> Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
