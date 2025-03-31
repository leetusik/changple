FROM python:3.12.6-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings_production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy project
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Run collectstatic when building the image
RUN mkdir -p /app/static_root
ENV STATIC_ROOT=/app/static_root
RUN python manage.py collectstatic --noinput

# Run the command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"] 