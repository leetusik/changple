#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! nc -z ${POSTGRES_HOST:-postgres} ${POSTGRES_PORT:-5432}; do
  sleep 1
done
echo "PostgreSQL is ready!"

echo "Making migrations..."
uv run python manage.py makemigrations --noinput

echo "Running migrations..."
uv run python manage.py migrate --noinput

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec uv run gunicorn src._changple.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --access-logfile - \
    --error-logfile -
