# Changple Deployment Guide

This guide explains how to deploy the Changple Django application on Oracle Cloud Infrastructure using Docker.

## Prerequisites

- Oracle Cloud Infrastructure account
- Oracle Linux VM instance set up with proper networking (see [Oracle Cloud Documentation](https://docs.oracle.com/en-us/iaas/Content/home.htm))
- Docker and Docker Compose installed on the VM
- Basic knowledge of Docker and Django

## Deployment Steps

### 1. Clone the Repository

On your Oracle Cloud VM, clone the repository:

```bash
git clone https://your-repository-url.git changple
cd changple
```

### 2. Configure Environment Variables

Review and update the `.env` file:

```
DEBUG=0
SECRET_KEY=your_django_secret_key_here_change_this_to_a_new_secure_random_string
ALLOWED_HOSTS=134.185.116.242
DJANGO_SETTINGS_MODULE=config.settings_production
```

Replace `your_django_secret_key_here_change_this_to_a_new_secure_random_string` with a strong random string. The deployment script will do this automatically if you haven't changed it.

### 3. Run the Deployment Script

Make the deployment script executable and run it:

```bash
chmod +x deploy.sh
./deploy.sh
```

This script will:
- Create necessary directories
- Generate a random Django secret key
- Set up SSL certificates using certbot
- Start all Docker services
- Apply database migrations
- Collect static files

### 4. Create a Superuser

After deployment, create a superuser account to access the Django admin interface:

```bash
docker-compose exec web python manage.py createsuperuser
```

## What's Included

The deployment setup includes:

- **Web Service**: Django application running with Gunicorn
- **Redis**: For caching and as a message broker for RQ
- **RQ Worker**: For processing background tasks
- **RQ Scheduler**: For scheduling recurring tasks
- **Nginx**: As a web server and reverse proxy with SSL termination

## File Structure

- `Dockerfile`: Defines the Python environment for running the Django app
- `docker-compose.yml`: Defines all services and their relationships
- `nginx/conf.d/app.conf`: Nginx configuration for HTTPS and proxying
- `config/settings_production.py`: Production-specific Django settings
- `.env`: Environment variables for configuration
- `deploy.sh`: Automation script for deployment

## SSL Certificate Renewal

SSL certificates from Let's Encrypt are valid for 90 days. Set up automatic renewal by adding a cron job:

```bash
echo "0 0 * * * cd /path/to/changple && docker-compose run --rm certbot renew && docker-compose exec nginx nginx -s reload" | sudo tee -a /etc/crontab
```

## Troubleshooting

### Viewing Logs

To view logs for the different services:

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs web
docker-compose logs rq_worker
docker-compose logs nginx
```

### Common Issues

1. **SSL Certificate Issues**:
   - Ensure port 80 is open on your firewall for the initial certificate creation
   - Check certbot logs: `docker-compose logs certbot`

2. **Redis Connection Issues**:
   - Check if Redis is running: `docker-compose ps redis`
   - Check Redis logs: `docker-compose logs redis`

3. **RQ Worker Not Processing Jobs**:
   - Check if RQ worker is running: `docker-compose ps rq_worker`
   - Check RQ worker logs: `docker-compose logs rq_worker`

## Maintenance

### Updates and Redeployment

To update the application:

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

### Backing Up Data

Since the application uses SQLite, back up the database file:

```bash
cp db.sqlite3 db.sqlite3.backup-$(date +%Y%m%d)
```

For a more comprehensive backup:

```bash
tar -czf changple-backup-$(date +%Y%m%d).tar.gz db.sqlite3 .env
```

## SQLite Database Synchronization

The application is configured to share the SQLite database file between the host system and all Docker containers that need database access.

### How Database Synchronization Works

In the docker-compose.yml file, each service that needs database access has a volume mount for the SQLite database:

```yaml
volumes:
  - ./db.sqlite3:/app/db.sqlite3
```

This configuration means:
- The database file on your host system (`./db.sqlite3`) is mapped to `/app/db.sqlite3` inside each container
- Any changes made to the database by the application inside the container are immediately reflected in the file on the host system
- All services (web, rq_worker, rq_scheduler) see the same database file

### Database Considerations

1. **Concurrent Access**: SQLite handles concurrent access, but it's not designed for high concurrency. In production with high traffic, consider migrating to PostgreSQL or MySQL.

2. **Database Backup**: The deployment script now automatically:
   - Creates daily backups of your database in the `db_backups` directory
   - Takes a backup before each deployment

3. **Database Migration**: If you need to move your database to another server:
   - Stop all containers: `docker-compose down`
   - Copy your db.sqlite3 file to the new server
   - Deploy on the new server with the copied database file

4. **Database Corruption Prevention**:
   - Always use `docker-compose down` to properly stop all services before any system shutdown
   - Consider implementing a write-ahead log by adding to your Django settings:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.sqlite3',
             'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
             'OPTIONS': {
                 'timeout': 20,  # in seconds
                 'pragmas': {
                     'journal_mode': 'wal',
                     'synchronous': 'normal',
                 }
             }
         }
     }
     ```

## Scheduled Tasks

The application is configured with several scheduled tasks:

### Daily Crawler

The deployment script automatically sets up a daily crawler job that runs at midnight KST (15:00 UTC). This job crawls data from the source website and stores it in the database.

You can view, modify, or cancel these schedules using the following commands:

```bash
# List all scheduled jobs
docker-compose exec web python manage.py schedule_crawler list

# Cancel all scheduled jobs
docker-compose exec web python manage.py schedule_crawler cancel

# Create a new schedule with different parameters
docker-compose exec web python manage.py schedule_crawler start --hour 15 --minute 0

# Check the status of the queue and jobs
docker-compose exec web python manage.py schedule_crawler status
```

### Custom Crawler Jobs

You can also create custom crawler jobs for specific ranges:

```bash
# Run a custom crawler job immediately for a specific range
docker-compose exec web python manage.py schedule_crawler custom --start-id 10000 --end-id 20000 --now

# Schedule a custom crawler job to run once in the future
docker-compose exec web python manage.py schedule_crawler custom --start-id 10000 --end-id 20000
```

### RQ Worker and Scheduler

The RQ worker and scheduler services handle the execution of these scheduled jobs. You can check their logs to monitor job execution:

```bash
docker-compose logs rq_worker
docker-compose logs rq_scheduler
```

If you need to modify the scheduling logic, you can edit:
- `scraper/services/scheduler.py`: Contains the scheduling implementation
- `scraper/tasks.py`: Contains the actual job that gets executed 