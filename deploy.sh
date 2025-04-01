#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment for Changple app...${NC}"

# Clean up existing containers and volumes
echo -e "${YELLOW}Cleaning up existing deployment...${NC}"
docker-compose down
# More aggressive cleanup to avoid cached issues
echo -e "${YELLOW}Performing deep cleanup of Docker resources...${NC}"
docker system prune -af --volumes
docker builder prune -af

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p nginx/conf.d
mkdir -p nginx/certbot/conf
mkdir -p nginx/certbot/www
mkdir -p logs
mkdir -p db_backups
mkdir -p chatbot/data/whoosh_index
mkdir -p static_root
mkdir -p media

# Set proper permissions for the Whoosh index directory
echo -e "${YELLOW}Setting permissions for Whoosh index directory...${NC}"
# Remove any existing index files to avoid permission conflicts on recreation
if [ -d "chatbot/data/whoosh_index" ]; then
    echo -e "${YELLOW}Checking for existing Whoosh index files...${NC}"
    # Check if directory is empty
    if [ "$(ls -A chatbot/data/whoosh_index 2>/dev/null)" ]; then
        echo -e "${YELLOW}Existing Whoosh index found. Preserving it.${NC}"
    else
        echo -e "${YELLOW}Empty Whoosh index directory. Ready for new index.${NC}"
    fi
fi
# Fix ownership and permissions
sudo chown -R $(whoami):$(whoami) chatbot/data 2>/dev/null || true
chmod -R 777 chatbot/data
chmod -R 777 chatbot/data/whoosh_index

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found! Please create it first.${NC}"
    exit 1
fi

# Check if SQLite database exists, create if not
if [ ! -f db.sqlite3 ]; then
    echo -e "${YELLOW}SQLite database not found, creating an empty one...${NC}"
    touch db.sqlite3
fi

# Backup existing database if it exists and has content
if [ -f db.sqlite3 ] && [ -s db.sqlite3 ]; then
    echo -e "${YELLOW}Backing up existing database...${NC}"
    cp db.sqlite3 "db_backups/db.sqlite3.backup-$(date +%Y%m%d-%H%M%S)"
fi

# Generate a random secret key if the current one is the default
if grep -q "your_django_secret_key_here" .env; then
    echo -e "${YELLOW}Generating a new Django secret key...${NC}"
    NEW_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
    sed -i "s/your_django_secret_key_here_change_this_to_a_new_secure_random_string/$NEW_SECRET_KEY/" .env
    echo -e "${GREEN}Secret key generated and updated in .env file${NC}"
fi

# Check for domain name
DOMAIN="ggulmae.com"
echo -e "${YELLOW}Deploying for domain: $DOMAIN${NC}"

# Ensure port 80 is free for certbot
echo -e "${YELLOW}Ensuring port 80 is available for certbot...${NC}"
if netstat -tuln | grep -q ":80 "; then
    echo -e "${RED}Warning: Port 80 is in use. Certbot may fail.${NC}"
    echo -e "${YELLOW}Trying to stop any services using port 80...${NC}"
    docker-compose down
fi

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

# Rebuild the Docker containers with the new configuration
echo -e "${YELLOW}Rebuilding Docker containers...${NC}"
docker-compose build --no-cache

# Start all services
echo -e "${GREEN}Starting all services...${NC}"
docker-compose up -d

# Check if Whoosh index needs to be synced from container to host
echo -e "${YELLOW}Checking if Whoosh index needs to be synced...${NC}"
if docker-compose exec -T web bash -c '[ -f "/app/chatbot/data/whoosh_index/_MAIN_1.toc" ] && echo "exists"' | grep -q "exists"; then
    if [ ! -f "./chatbot/data/whoosh_index/_MAIN_1.toc" ]; then
        echo -e "${YELLOW}Whoosh index exists in container but not on host. Copying to host...${NC}"
        # Get container ID
        CONTAINER_ID=$(docker-compose ps -q web)
        # Copy files from container to host
        docker cp $CONTAINER_ID:/app/chatbot/data/whoosh_index/. ./chatbot/data/whoosh_index/
        echo -e "${GREEN}Whoosh index files copied from container to host${NC}"
        # Set permissive permissions on host files
        echo -e "${YELLOW}Setting permissions for copied Whoosh index files...${NC}"
        chmod -R 777 ./chatbot/data/whoosh_index
    else
        echo -e "${GREEN}Whoosh index exists both in container and on host${NC}"
    fi
fi

# Create directory with proper permissions for Whoosh index
echo -e "${YELLOW}Setting up Whoosh index directory with proper permissions...${NC}"
docker-compose exec web mkdir -p /app/chatbot/data/whoosh_index
docker-compose exec web chmod -R 777 /app/chatbot/data

# Create an empty Whoosh index schema file before migrations
echo -e "${YELLOW}Creating empty Whoosh index before migrations...${NC}"
docker-compose exec web python -c "
import os
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID, STORED
# Create directory
os.makedirs('/app/chatbot/data/whoosh_index', exist_ok=True)
# Define schema
schema = Schema(
    post_id=ID(stored=True),
    title=TEXT(stored=True),
    content=TEXT(stored=True),
    author=TEXT(stored=True),
    category=TEXT(stored=True),
    published_date=STORED(),
    url=ID(stored=True)
)
# Create index
create_in('/app/chatbot/data/whoosh_index', schema)
print('Empty Whoosh index created successfully')
"

# Apply migrations
echo -e "${YELLOW}Applying database migrations...${NC}"
docker-compose exec web python manage.py migrate

# Install Playwright browsers if they're needed for the scraper
echo -e "${YELLOW}Installing Playwright browsers...${NC}"
docker-compose exec web playwright install chromium

# Run ingest to populate the index after migrations
echo -e "${YELLOW}Running ingest to populate index with documents...${NC}"
docker-compose exec web python manage.py run_ingest || {
    echo -e "${RED}Warning: Ingest failed, but continuing deployment...${NC}"
    echo -e "${YELLOW}You may need to run 'docker-compose exec web python manage.py run_ingest' manually later${NC}"
}

# Create logs directory inside the container
docker-compose exec web mkdir -p /app/logs

# Collect static files (should already be done in Dockerfile, but just in case)
echo -e "${YELLOW}Collecting static files...${NC}"
docker-compose exec web python manage.py collectstatic --noinput

# Setup db backup cron job
echo -e "${YELLOW}Setting up database backup cron job...${NC}"
CRON_JOB="0 0 * * * cd $(pwd) && cp db.sqlite3 db_backups/db.sqlite3.backup-\$(date +\%Y\%m\%d)"
(crontab -l 2>/dev/null | grep -v "db.sqlite3.backup"; echo "$CRON_JOB") | crontab -

# # Schedule the scraper to run daily at midnight KST (15:00 UTC)
# echo -e "${YELLOW}Setting up daily crawler schedule to run at midnight KST...${NC}"
# docker-compose exec web python manage.py schedule_crawler start --hour 15 --minute 0
# echo -e "${GREEN}Crawler scheduled to run daily at midnight KST (15:00 UTC)${NC}"

# Schedule the scraper to run daily at midnight KST (13:10 UTC)
echo -e "${YELLOW}Setting up daily crawler schedule to run at 11:15 KST...${NC}"
docker-compose exec web python manage.py schedule_crawler start --hour 2 --minute 15
echo -e "${GREEN}Crawler scheduled to run daily at 11:15 KST (02:15 UTC)${NC}"

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Your application is now available at https://$DOMAIN${NC}"
echo -e "${YELLOW}NOTE: To create a superuser, run: docker-compose exec web python manage.py createsuperuser${NC}"
echo -e "${YELLOW}Database backups will be stored in the db_backups directory daily${NC}"

# Verify Whoosh index is properly synced
echo -e "${YELLOW}Verifying Whoosh index is properly synced...${NC}"
if [ -f "./chatbot/data/whoosh_index/_MAIN_1.toc" ]; then
    echo -e "${GREEN}✓ Whoosh index found on host system${NC}"
    HOST_INDEX_SIZE=$(du -sh ./chatbot/data/whoosh_index | cut -f1)
    echo -e "${GREEN}✓ Host Whoosh index size: $HOST_INDEX_SIZE${NC}"
    
    # Check container index size
    CONTAINER_INDEX_SIZE=$(docker-compose exec -T web bash -c "du -sh /app/chatbot/data/whoosh_index | cut -f1")
    echo -e "${GREEN}✓ Container Whoosh index size: $CONTAINER_INDEX_SIZE${NC}"
    
    echo -e "${GREEN}✓ Whoosh index is properly mounted and synced${NC}"
else
    echo -e "${RED}✗ Whoosh index files not found on host system${NC}"
    echo -e "${YELLOW}Check container for index: docker-compose exec web ls -la /app/chatbot/data/whoosh_index${NC}"
    echo -e "${YELLOW}If index exists in container but not on host, manually sync with:${NC}"
    echo -e "${YELLOW}docker cp \$(docker-compose ps -q web):/app/chatbot/data/whoosh_index/. ./chatbot/data/whoosh_index/${NC}"
fi 