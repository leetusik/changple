#!/bin/bash
set -e

echo "Starting Changple Agent Service..."

# Run uvicorn with reload in development
exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
