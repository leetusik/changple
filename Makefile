# =============================================================================
# Changple AI - Makefile
# =============================================================================

.PHONY: help dev prod down logs clean

# Default target
help:
	@echo "Changple AI - Docker Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make dev        Start development environment"
	@echo "  make dev-build  Build and start development environment"
	@echo "  make prod       Start production environment"
	@echo "  make prod-build Build and start production environment"
	@echo "  make down       Stop all containers"
	@echo "  make down-v     Stop all containers and remove volumes"
	@echo "  make logs       Follow logs (all services)"
	@echo "  make logs-core  Follow Core service logs"
	@echo "  make logs-agent Follow Agent service logs"
	@echo "  make clean      Remove all containers, volumes, and images"
	@echo ""
	@echo "Database:"
	@echo "  make db-shell   Open PostgreSQL shell"
	@echo "  make migrate    Run Django migrations"
	@echo ""
	@echo "Development:"
	@echo "  make shell-core  Open shell in Core container"
	@echo "  make shell-agent Open shell in Agent container"

# =============================================================================
# Development
# =============================================================================

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-d:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# =============================================================================
# Production
# =============================================================================

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up

prod-build:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build

prod-d:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# =============================================================================
# Stop / Clean
# =============================================================================

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true

down-v:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v 2>/dev/null || true

clean:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v --rmi local
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v --rmi local 2>/dev/null || true

# =============================================================================
# Logs
# =============================================================================

logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

logs-core:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f core

logs-agent:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f agent

logs-celery:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f celery celery-beat

# =============================================================================
# Database
# =============================================================================

db-shell:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml exec postgres psql -U changple -d changple

migrate:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml exec core python manage.py migrate

# =============================================================================
# Shell Access
# =============================================================================

shell-core:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml exec core /bin/bash

shell-agent:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml exec agent /bin/bash
