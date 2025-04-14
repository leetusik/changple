FROM python:3.12.6-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings_production

# Install system dependencies including those needed for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    # Playwright dependencies
    libwebkit2gtk-4.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-tools \
    libwoff1 \
    libopus0 \
    libharfbuzz-icu0 \
    libevent-2.1-7 \
    libfontconfig1 \
    libvpx7 \
    libssl3 \
    libnss3 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxtst6 \
    libxss1 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
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
RUN python manage.py collectstatic --noinput --clear

# Run the command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"] 