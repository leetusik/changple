#!/bin/bash
set -e

# Fix permissions for media directory
echo "Fixing permissions..."
mkdir -p /app/media /app/staticfiles
chown -R appuser:appuser /app/media /app/staticfiles /app/src

echo "Waiting for PostgreSQL..."
while ! nc -z ${POSTGRES_HOST:-postgres} ${POSTGRES_PORT:-5432}; do
  sleep 1
done
echo "PostgreSQL is ready!"

echo "Making migrations..."
gosu appuser uv run python manage.py makemigrations --noinput

echo "Running migrations..."
gosu appuser uv run python manage.py migrate --noinput

echo "Collecting static files..."
gosu appuser uv run python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gosu appuser uv run gunicorn src._changple.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --access-logfile - \
    --error-logfile -
