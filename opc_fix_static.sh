#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if SSH key exists
SSH_KEY="/Users/sugang/Desktop/projects/keys/ssh-key-2025-03-31.key"
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}SSH key not found at $SSH_KEY${NC}"
    exit 1
fi

# Server details
SERVER="opc@134.185.116.242"
REMOTE_DIR="/home/opc/changple"

echo -e "${GREEN}Starting OPC static file fix...${NC}"

# 1. Copy local .env file to ensure environment is correct (uncommenting production settings)
echo -e "${YELLOW}Ensuring .env has production settings...${NC}"
cp .env .env.backup
sed -i '' 's/# SOCIAL_AUTH_NAVER_CLIENT_ID=d6TXsnxhNt3elcu6ASsy/SOCIAL_AUTH_NAVER_CLIENT_ID=d6TXsnxhNt3elcu6ASsy/g' .env
sed -i '' 's/# SOCIAL_AUTH_NAVER_CLIENT_SECRET=6VscYx2u89/SOCIAL_AUTH_NAVER_CLIENT_SECRET=6VscYx2u89/g' .env
sed -i '' 's/# DEBUG=0/DEBUG=0/g' .env
sed -i '' 's/# SECRET_KEY=leesugangiskingoftheworld/SECRET_KEY=leesugangiskingoftheworld/g' .env
sed -i '' 's/# ALLOWED_HOSTS=changple.ai,www.changple.ai/ALLOWED_HOSTS=changple.ai,www.changple.ai/g' .env
sed -i '' 's/# DJANGO_SETTINGS_MODULE=config.settings_production/DJANGO_SETTINGS_MODULE=config.settings_production/g' .env
sed -i '' 's/# REDIS_HOST=redis/REDIS_HOST=redis/g' .env

# 2. Copy updated .env to server
echo -e "${YELLOW}Copying .env to server...${NC}"
scp -i "$SSH_KEY" .env "$SERVER:$REMOTE_DIR/"

# 3. Run remote commands to fix static files
echo -e "${YELLOW}Running static file fix on OPC...${NC}"
ssh -i "$SSH_KEY" "$SERVER" "cd $REMOTE_DIR && \
    echo 'Creating static_root directory...' && \
    mkdir -p static_root && \
    chmod 755 static_root && \
    echo 'Stopping Docker containers...' && \
    docker-compose down && \
    echo 'Building containers...' && \
    docker-compose build --no-cache && \
    echo 'Starting containers...' && \
    docker-compose up -d && \
    echo 'Running collectstatic...' && \
    docker-compose exec -T web python manage.py collectstatic --noinput --clear && \
    echo 'Verifying static files...' && \
    docker-compose exec -T web ls -la /app/static_root"

# 4. Restore local .env
echo -e "${YELLOW}Restoring local .env file...${NC}"
mv .env.backup .env

echo -e "${GREEN}Static file fix completed on OPC!${NC}"
echo -e "${YELLOW}Visit https://changple.ai to check if CSS is working now.${NC}" 