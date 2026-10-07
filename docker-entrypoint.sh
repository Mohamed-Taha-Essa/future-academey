#!/bin/sh
# Container start: apply migrations, then serve with Gunicorn on Railway's $PORT.
set -e

python manage.py migrate --noinput

exec gunicorn project.wsgi \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
