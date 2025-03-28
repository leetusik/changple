# Oracle Cloud Deployment Guide

This guide will help you deploy your Django application on Oracle Cloud Infrastructure (OCI) using Docker, and configure Redis and RQ Worker for scheduled tasks.

## Table of Contents
1. [Oracle Cloud Infrastructure Setup](#oracle-cloud-infrastructure-setup)
2. [Docker Configuration](#docker-configuration)
3. [Redis Setup](#redis-setup)
4. [RQ Worker Configuration](#rq-worker-configuration)
5. [Deployment Process](#deployment-process)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Oracle Cloud Infrastructure Setup

### Account Setup
1. Sign up for Oracle Cloud at [https://www.oracle.com/cloud/free/](https://www.oracle.com/cloud/free/)
2. Complete the verification process
3. Access the OCI Console

### Networking Setup
1. Create a Virtual Cloud Network (VCN):
   - Navigate to **Networking** → **Virtual Cloud Networks**
   - Click **Create VCN**
   - Enter a name and CIDR block (e.g., 10.0.0.0/16)
   - Click **Create**

2. Configure Security Lists:
   - In your VCN, go to **Security Lists**
   - Add Ingress Rules for:
     - TCP port 22 (SSH) - Source: 0.0.0.0/0 (allows access from anywhere)
     - TCP port 80 (HTTP) - Source: 0.0.0.0/0 (required for public web access)
     - TCP port 443 (HTTPS) - Source: 0.0.0.0/0 (required for secure web access)
     - TCP port 8000 (Django dev server, optional) - Source: Your specific IP or VPN IP for security
     - TCP port 6379 (Redis) - Source: 10.0.0.0/16 (restrict to VCN internal traffic only)

   > **Security Note**: For production environments, always use the principle of least privilege:
   > - Use 0.0.0.0/0 (open to internet) only for services that need to be publicly accessible (HTTP/HTTPS)
   > - Use 10.0.0.0/16 (VCN CIDR) for internal services like Redis to prevent external access
   > - Consider using a more restricted source for SSH (your specific IP) rather than 0.0.0.0/0 for better security

### Create a Compute Instance
1. Navigate to **Compute** → **Instances**
2. Click **Create Instance**
3. Configure:
   - Name: `changple-app`
   - Image: Oracle Linux 8
   - Shape: VM.Standard.E2.1.Micro (free tier)
   - Network: Select your VCN
   - Assign a public IP
   - Add your SSH key
4. Click **Create**

### Connect to Your Instance
```bash
ssh -i /path/to/your/private/key opc@<your-instance-public-ip>
```

## Docker Configuration

### Install Docker on Oracle Linux 8
```bash
# Update system
sudo dnf update -y

# Add Docker repository
sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker
sudo dnf install -y docker-ce docker-ce-cli containerd.io

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to the docker group
sudo usermod -aG docker opc
```
Log out and log back in for the group changes to take effect.

### Install Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/download/v2.25.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Project Setup

### Create Docker Configuration Files

#### 1. Dockerfile
Create a Dockerfile in your project root:

```Dockerfile
FROM python:3.12.6-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Run collectstatic when building the image
RUN python manage.py collectstatic --noinput

# Run the command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
```

#### 2. docker-compose.yml
Create a docker-compose.yml file in your project root:

```yaml
version: '3.8'

services:
  web:
    build: .
    restart: always
    depends_on:
      - redis
    environment:
      - DEBUG=0
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
    networks:
      - app_network

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data
    networks:
      - app_network

  rq_worker:
    build: .
    restart: always
    depends_on:
      - redis
      - web
    command: python manage.py rqworker default
    environment:
      - DEBUG=0
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - REDIS_URL=redis://redis:6379/0
    networks:
      - app_network

  rq_scheduler:
    build: .
    restart: always
    depends_on:
      - redis
      - web
    command: python manage.py rqscheduler
    environment:
      - DEBUG=0
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - REDIS_URL=redis://redis:6379/0
    networks:
      - app_network

  nginx:
    image: nginx:1.25-alpine
    restart: always
    depends_on:
      - web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - static_volume:/app/static
      - media_volume:/app/media
      - ./nginx/certbot/conf:/etc/letsencrypt
      - ./nginx/certbot/www:/var/www/certbot
    networks:
      - app_network

volumes:
  static_volume:
  media_volume:
  redis_data:

networks:
  app_network:
```

#### 3. Nginx Configuration
Create a directory for Nginx configurations:

```bash
mkdir -p nginx/conf.d
```

Create an Nginx configuration file at `nginx/conf.d/app.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    server_tokens off;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    server_tokens off;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 20M;

    location /static/ {
        alias /app/static/;
    }

    location /media/ {
        alias /app/media/;
    }

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 4. Create a .env file
Create a .env file for environment variables:

```
SECRET_KEY=your_django_secret_key_here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

## Redis Setup

Redis will be set up through Docker as specified in the docker-compose.yml file. Make sure your Django settings are configured to use Redis:

In your `settings.py`:

```python
# Redis and RQ configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

RQ_QUEUES = {
    'default': {
        'URL': REDIS_URL,
        'DEFAULT_TIMEOUT': 360,
    }
}
```

## RQ Worker Configuration

### Setting Up Scheduled Tasks

1. Ensure your `tasks.py` files are properly configured with the `@job` decorator for RQ jobs.

2. For scheduling recurring tasks, use `django-rq-scheduler`. If not already installed, add it to your requirements.txt:
```
django-rq-scheduler
```

3. Create scheduled jobs through the admin interface or using a management command:

```python
# In a management command or migration
from django_rq_scheduler.models import ScheduledJob

ScheduledJob.objects.create(
    name='Run Crawler',
    callable='scraper.tasks.run_scheduled_crawler',
    enabled=True,
    # Schedule: run every day at 2 AM
    cron_string='0 2 * * *',
    # Optional arguments
    kwargs={"batch_size": 100},
)
```

## Deployment Process

### Initial Deployment

1. Clone your repository on the Oracle Cloud instance:
```bash
git clone https://your-repo-url.git changple
cd changple
```

2. Create the necessary configuration files (Dockerfile, docker-compose.yml, nginx configs) as described above.

3. Set up SSL certificates with Certbot:
```bash
mkdir -p nginx/certbot/conf nginx/certbot/www
```

4. Start the Nginx service first:
```bash
docker-compose up -d nginx
```

5. Run Certbot:
```bash
docker run -it --rm \
  -v $(pwd)/nginx/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/nginx/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d your-domain.com
```

6. Start all services:
```bash
docker-compose up -d
```

7. Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

8. Create a superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

### Updates and Maintenance

To update your application:

1. Pull the latest changes:
```bash
git pull
```

2. Rebuild and restart containers:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

3. Run migrations if needed:
```bash
docker-compose exec web python manage.py migrate
```

## Monitoring and Maintenance

### Viewing Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs web
docker-compose logs rq_worker
```

### Monitoring Redis and RQ
You can use the Django RQ admin interface to monitor queues and jobs:

1. Make sure django-rq's admin views are enabled in your Django project.
2. Access the admin interface at: https://your-domain.com/admin/django-rq/

### SSL Certificate Renewal
Set up an automatic renewal using a cron job:

```bash
echo "0 0 * * * cd /path/to/your/project && docker-compose run --rm certbot renew && docker-compose exec nginx nginx -s reload" | sudo tee -a /etc/crontab
```

## Troubleshooting

### Common Issues

1. **Connection issues with Redis**:
   - Check if Redis container is running: `docker-compose ps redis`
   - Check Redis logs: `docker-compose logs redis`
   - Verify REDIS_URL in your Django settings and environment variables

2. **RQ Worker not processing jobs**:
   - Check if RQ Worker container is running: `docker-compose ps rq_worker`
   - Check RQ Worker logs: `docker-compose logs rq_worker`
   - Make sure tasks are properly decorated with @job

3. **Scheduled tasks not running**:
   - Check if RQ Scheduler container is running: `docker-compose ps rq_scheduler`
   - Check scheduler logs: `docker-compose logs rq_scheduler`
   - Verify scheduled jobs in the admin interface

4. **Database connections**:
   - Ensure the database is accessible from the Docker containers
   - Check database logs if available
   - Verify database connection settings

### Getting Help
If you encounter issues specific to Oracle Cloud:
- Consult the [Oracle Cloud Documentation](https://docs.oracle.com/en-us/iaas/Content/home.htm)
- Use the [Oracle Cloud Support Portal](https://support.oracle.com/)
- Join the [Oracle Developer Discord](https://discord.com/invite/oracle-developers)

For Django, Redis, or RQ issues:
- Refer to the [Django Documentation](https://docs.djangoproject.com/)
- Check the [Django-RQ Documentation](https://github.com/rq/django-rq)
- Consult the [Redis Documentation](https://redis.io/documentation) 