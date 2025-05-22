#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment for Changple app with PostgreSQL...${NC}"

# Source .env to get POSTGRES_ variables for backup
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}Error: .env file not found! Please create it first.${NC}"
    exit 1
fi

# --- IMPORTANT: Docker Cleanup ---
echo -e "${YELLOW}Stopping existing services...${NC}"
docker-compose down # This does NOT remove named volumes by default (good for postgres_data)

# A safer cleanup:
echo -e "${YELLOW}Cleaning up unused Docker images, build cache, and networks...${NC}"
docker image prune -af
docker builder prune -af
docker network prune -f
# If you want to remove ONLY anonymous (unnamed) volumes:
# docker volume prune -f
# --- End Docker Cleanup ---

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p nginx/conf.d
mkdir -p nginx/certbot/conf
mkdir -p nginx/certbot/www
mkdir -p logs
chmod 777 ./logs # Make logs directory world-writable
mkdir -p db_backups/postgres # Changed backup directory


# --- MODIFIED: Backup existing PostgreSQL database ---
# This assumes docker-compose and the 'db' service was up before 'down'
# Or, if you want to backup an *external* DB before migrating, you'd do it differently.
# For backing up the Dockerized Postgres:
echo -e "${YELLOW}Attempting to backup PostgreSQL database (if service exists and is running)...${NC}"
# Check if db service is defined and potentially running, then backup.
# This part is tricky because we've already run 'docker-compose down'.
# A better strategy is to back up *before* 'docker-compose down' or have scheduled backups.
# For now, this will backup from a running container IF it was running.
# A robust backup would be `docker-compose exec -T db pg_dumpall -U ${POSTGRES_USER}`
# For this script, we'll assume a separate cron job or manual backup for an existing DB.
# The cron job setup later is more reliable for ongoing backups.

# Generate a random secret key if the current one is the default
if grep -q "your_django_secret_key_here" .env; then
    echo -e "${YELLOW}Generating a new Django secret key...${NC}"
    NEW_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
    sed -i.bak "s/your_django_secret_key_here/$NEW_SECRET_KEY/" .env
    rm .env.bak
    echo -e "${GREEN}Secret key generated and updated in .env file${NC}"
fi

# Check for domain name
DOMAIN="changple.ai"
echo -e "${YELLOW}Deploying for domain: $DOMAIN${NC}"

# Ensure port 80 is free for certbot
echo -e "${YELLOW}Ensuring port 80 is available for certbot...${NC}"
# docker-compose down was already called, so ports should be free.
# if netstat -tuln | grep -q ":80 "; then
#     echo -e "${RED}Warning: Port 80 is in use. Certbot may fail.${NC}"
# fi

# Get SSL certificates with certbot
echo -e "${YELLOW}Setting up SSL certificates with certbot...${NC}"
docker run --rm -v "$(pwd)/nginx/certbot/conf:/etc/letsencrypt" \
                -v "$(pwd)/nginx/certbot/www:/var/www/certbot" \
                -p 80:80 \
                certbot/certbot certonly --standalone \
                --non-interactive --agree-tos \
                --email swangle2100@gmail.com \
                --domains $DOMAIN \
                --http-01-port=80

echo -e "${YELLOW}Fixing permissions for certbot files...${NC}"
sudo chown -R $(id -u):$(id -g) ./nginx/certbot/conf

# Rebuild the Docker containers with the new configuration
echo -e "${YELLOW}Rebuilding Docker containers...${NC}"
docker-compose build --no-cache

# Start all services
echo -e "${GREEN}Starting all services...${NC}"
docker-compose up -d

# Wait for PostgreSQL to be fully ready (important before migrations)
echo -e "${YELLOW}Waiting for PostgreSQL service to be healthy...${NC}"
MAX_WAIT=60 # seconds
CUR_WAIT=0
until docker-compose exec -T db pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -q || [ ${CUR_WAIT} -eq ${MAX_WAIT} ]; do
  sleep 1
  CUR_WAIT=$((CUR_WAIT+1))
done
if [ ${CUR_WAIT} -eq ${MAX_WAIT} ]; then
  echo -e "${RED}PostgreSQL did not become ready in time. Exiting.${NC}"
  docker-compose logs db
  exit 1
fi
echo -e "${GREEN}PostgreSQL is ready!${NC}"

# Apply migrations
echo -e "${YELLOW}Applying database migrations...${NC}"
docker-compose exec web python manage.py makemigrations # Usually not needed in deploy, but harmless
docker-compose exec web python manage.py migrate

# Run collectstatic
echo -e "${YELLOW}Collecting static files...${NC}"
docker-compose exec web python manage.py collectstatic --noinput

# Install Playwright browsers
echo -e "${YELLOW}Installing Playwright browsers...${NC}"
docker-compose exec web playwright install chromium
docker-compose exec rq_worker playwright install chromium # Assuming rq_worker also needs it

# --- MODIFIED: Setup PostgreSQL db backup cron job ---
echo -e "${YELLOW}Setting up PostgreSQL database backup cron job...${NC}"
# Ensure POSTGRES_USER is set from .env sourcing earlier
BACKUP_SCRIPT_PATH="$(pwd)/backup_postgres.sh"
DB_BACKUP_DIR="$(pwd)/db_backups/postgres"

# Create backup script
cat << EOF > ${BACKUP_SCRIPT_PATH}
#!/bin/bash
# Script to backup PostgreSQL database from Docker container
# Load .env from the script's directory or parent if not found
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="\$SCRIPT_DIR/.env"
if [ ! -f "\$ENV_FILE" ]; then
    ENV_FILE="\$SCRIPT_DIR/../.env" # Try parent dir
fi

if [ -f "\$ENV_FILE" ]; then
  export \$(grep -v '^#' "\$ENV_FILE" | xargs)
else
  echo "Error: .env file not found for backup script at \$ENV_FILE or \$SCRIPT_DIR/../.env"
  exit 1
fi

BACKUP_DIR="${DB_BACKUP_DIR}"
DATE=\$(date +%Y%m%d-%H%M%S)
mkdir -p "\$BACKUP_DIR"
# Use docker-compose exec to run pg_dump inside the db container
# Ensure the 'db' service name and POSTGRES_USER/POSTGRES_DB are correct
# Note: -T disables pseudo-tty allocation, good for scripting
docker-compose -f "\$SCRIPT_DIR/docker-compose.yml" exec -T db pg_dump -U "\${POSTGRES_USER}" -d "\${POSTGRES_DB}" | gzip > "\$BACKUP_DIR/\${POSTGRES_DB}-backup-\$DATE.sql.gz"
# Optional: Clean up old backups (e.g., older than 7 days)
find "\$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +7 -delete
EOF
chmod +x ${BACKUP_SCRIPT_PATH}

CRON_JOB="0 2 * * * ${BACKUP_SCRIPT_PATH}" # Backup at 2 AM daily
(crontab -l 2>/dev/null | grep -v "${BACKUP_SCRIPT_PATH}" | grep -v "db.sqlite3.backup"; echo "$CRON_JOB") | crontab -
echo -e "${GREEN}PostgreSQL backup cron job set up. Backups will be in ${DB_BACKUP_DIR}${NC}"
# --- End DB backup cron job ---

# Schedule crawler
echo -e "${YELLOW}Setting up crawler to run 5 minutes after deployment...${NC}"
FUTURE_TIME=$(date -u -d "+5 minutes" "+%H %M")
FUTURE_HOUR=$(echo $FUTURE_TIME | cut -d' ' -f1)
FUTURE_MINUTE=$(echo $FUTURE_TIME | cut -d' ' -f2)
docker-compose exec web python manage.py schedule_crawler start --hour $FUTURE_HOUR --minute $FUTURE_MINUTE

echo -e "${GREEN}Crawler scheduled to run at $(date -u -d "+5 minutes" "+%H:%M") UTC ($(TZ=Asia/Seoul date -d "+5 minutes" "+%H:%M") KST)${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Your application is now available at https://$DOMAIN${NC}"
echo -e "${YELLOW}NOTE: To create a superuser, run: docker-compose exec web python manage.py createsuperuser${NC}"
echo -e "${YELLOW}PostgreSQL database backups will be stored in ${DB_BACKUP_DIR} daily${NC}"