#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! nc -z ${POSTGRES_HOST:-postgres} ${POSTGRES_PORT:-5432}; do
  sleep 1
done
echo "PostgreSQL is ready!"

echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
  sleep 1
done
echo "Redis is ready!"

echo "Starting Celery worker..."
exec uv run celery -A src._changple worker -l INFO -Q default,scraper
