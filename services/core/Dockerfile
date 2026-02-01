# Django Core Service - Web Server
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    netcat-traditional \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml ./

# Install dependencies (generates lock file)
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY . .

# Make entrypoint executable before changing user
RUN chmod +x entrypoint.sh

# Install the project
RUN uv sync --no-dev

# Create non-root user
RUN useradd --create-home appuser
# USER appuser

# Expose port
EXPOSE 8000

# Use entrypoint script with bash
ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]
