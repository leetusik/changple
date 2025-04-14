#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting CSS fix deployment...${NC}"

# Clean up previous static files if any
echo -e "${YELLOW}Cleaning up static_root directory...${NC}"
sudo rm -rf static_root
mkdir -p static_root

# Stop containers
echo -e "${YELLOW}Stopping running containers...${NC}"
docker-compose down

# Rebuild the containers
echo -e "${YELLOW}Rebuilding containers...${NC}"
docker-compose build --no-cache

# Start containers
echo -e "${YELLOW}Starting containers...${NC}"
docker-compose up -d

# Run collectstatic explicitly to ensure all files are collected
echo -e "${YELLOW}Running collectstatic...${NC}"
docker-compose exec web python manage.py collectstatic --noinput --clear

# Check if static files are correctly mounted
echo -e "${YELLOW}Verifying static files...${NC}"
docker-compose exec web ls -la /app/static_root
docker-compose exec web ls -la /app/static

echo -e "${GREEN}Deployment fix completed!${NC}"
echo -e "${YELLOW}Visit your site and check if CSS is working now.${NC}" 