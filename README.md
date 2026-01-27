# Changple AI - v3.0.0 (Monorepo MSA)

## Overview

This document outlines the target architecture for restructuring Changple AI from a Django monolith to a Microservices Architecture (MSA) managed as a monorepo.

---

## Project Root Structure

```
changple/
├── docker-compose.yml              # Main orchestration (dev)
├── docker-compose.prod.yml         # Production orchestration
├── docker-compose.override.yml     # Local dev overrides
├── .env.example                    # Environment template
├── .gitignore
├── README.md
├── Makefile                        # Common commands
│
├── nginx/                          # Main reverse proxy
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── conf.d/
│   │   ├── default.conf
│   │   ├── upstream.conf
│   │   └── ssl.conf
│   └── certs/                      # SSL certificates (gitignored)
│
├── services/
│   ├── core/                       # Django WAS (users, content, auth)
│   ├── client/                     # React frontend
│   ├── agent/                      # LangGraph AI agent (FastAPI)
│   └── scraper/                    # Web scraper service (FastAPI, optional)
│
├── infra/                          # Infrastructure configs
│   ├── postgres/
│   │   └── init.sql
│   ├── redis/
│   │   └── redis.conf
│   └── scripts/
│       ├── deploy.sh
│       └── backup.sh
│
└── docs/                           # Documentation
    ├── architecture.md
    ├── api-spec.md
    └── deployment.md
```

---

## Services Detail

### 1. Core Service (Django WAS)

**Path**: `services/core/`

**Responsibilities**:
- User authentication & authorization (Naver OAuth)
- Content management (Notion exports)
- Session management
- Admin panel
- API gateway coordination

```
services/core/
├── Dockerfile
├── Dockerfile.prod
├── pyproject.toml                  # or requirements.txt
├── manage.py
├── src/
│   ├── _changple/                  # Django project config
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── users/                      # User management app
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── api_views.py
│   │   ├── serializers.py
│   │   ├── services/
│   │   ├── middleware.py
│   │   ├── backends.py
│   │   ├── pipeline.py
│   │   ├── admin.py
│   │   └── urls.py
│   │
│   ├── content/                    # Content management app
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── api_views.py
│   │   ├── serializers.py
│   │   ├── utils.py
│   │   ├── admin.py
│   │   └── urls.py
│   │
│   ├── chat/                       # Chat session management (thin layer)
│   │   ├── __init__.py
│   │   ├── models.py               # ChatSession, ChatMessage
│   │   ├── api_views.py            # Session CRUD, proxy to agent
│   │   ├── serializers.py
│   │   ├── consumers.py            # WebSocket proxy to agent
│   │   └── urls.py
│   │
│   └── common/                     # Shared utilities
│       ├── __init__.py
│       ├── models.py
│       └── utils.py
│
├── static/                         # Admin static files only
├── templates/                      # Admin templates only
├── media/                          # Uploaded files (gitignored)
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── ...
```

**Tech Stack**:
- Django 6.x
- Django REST Framework
- Django Channels (WebSocket proxy)
- PostgreSQL
- Redis (cache)
- Celery (optional, for content processing)

**Ports**: 8000 (internal)

---

### 2. Client Service (React Frontend)

**Path**: `services/client/`

**Responsibilities**:
- User interface
- Real-time chat interface
- Content browsing
- Admin dashboard (optional)

```
services/client/
├── Dockerfile
├── Dockerfile.prod
├── nginx.conf                      # Client-specific nginx config
├── package.json
├── pnpm-lock.yaml                  # or yarn.lock / package-lock.json
├── tsconfig.json
├── vite.config.ts                  # or next.config.js
├── .env.example
│
├── public/
│   ├── favicon.ico
│   └── assets/
│       ├── images/
│       └── icons/
│
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button/
│   │   │   ├── Modal/
│   │   │   ├── Input/
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── Header/
│   │   │   ├── Sidebar/
│   │   │   └── Footer/
│   │   ├── chat/
│   │   │   ├── ChatContainer/
│   │   │   ├── MessageList/
│   │   │   ├── MessageInput/
│   │   │   └── ...
│   │   └── content/
│   │       ├── ContentCard/
│   │       ├── ContentViewer/
│   │       └── ...
│   │
│   ├── pages/                      # or routes/
│   │   ├── Home/
│   │   ├── Chat/
│   │   ├── Content/
│   │   ├── Login/
│   │   └── Admin/
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useChat.ts
│   │   ├── useWebSocket.ts
│   │   └── ...
│   │
│   ├── services/                   # API clients
│   │   ├── api.ts                  # Axios/fetch instance
│   │   ├── authService.ts
│   │   ├── chatService.ts
│   │   ├── contentService.ts
│   │   └── websocket.ts
│   │
│   ├── stores/                     # State management
│   │   ├── authStore.ts
│   │   ├── chatStore.ts
│   │   └── ...
│   │
│   ├── types/
│   │   ├── api.ts
│   │   ├── chat.ts
│   │   ├── content.ts
│   │   └── user.ts
│   │
│   ├── utils/
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   │
│   └── styles/
│       ├── globals.css
│       ├── variables.css
│       └── ...
│
└── tests/
    ├── setup.ts
    ├── components/
    └── pages/
```

**Tech Stack**:
- React 18+
- TypeScript
- Vite (or Next.js if SSR needed)
- TailwindCSS (or styled-components)
- Zustand / Redux Toolkit (state)
- React Query / SWR (data fetching)
- Nginx (production serving)

**Ports**: 3000 (dev), 80 (nginx container)

---

### 3. Agent Service (LangGraph AI)

**Path**: `services/agent/`

**Responsibilities**:
- LangGraph workflow orchestration
- LLM interactions (OpenAI, Google)
- Vector search (Pinecone)
- Streaming responses
- WebSocket handling for real-time chat

```
services/agent/
├── Dockerfile
├── Dockerfile.prod
├── pyproject.toml
├── alembic.ini                     # DB migrations (if needed)
│
├── src/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry
│   ├── config.py                   # Settings management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py               # Main router
│   │   ├── deps.py                 # Dependencies
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py             # Chat endpoints
│   │   │   ├── health.py           # Health checks
│   │   │   └── websocket.py        # WebSocket handlers
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py             # JWT/API key validation
│   │       └── logging.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── bot.py                  # LangGraph workflow (from current chatbot/bot.py)
│   │   ├── prompts.py              # Prompt templates
│   │   ├── chains.py               # LangChain chains
│   │   └── tools.py                # Custom tools
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm.py                  # LLM client abstraction
│   │   ├── vector_store.py         # Pinecone interactions
│   │   ├── embeddings.py           # Embedding service
│   │   └── streaming.py            # SSE/WebSocket streaming
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py              # Pydantic models
│   │   └── state.py                # LangGraph state definitions
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py              # DB session management
│   │   └── models.py               # SQLAlchemy models (if needed)
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   └── test_core/
│
└── scripts/
    └── init_db.py
```

**Tech Stack**:
- FastAPI
- LangGraph
- LangChain
- OpenAI / Google Generative AI
- Pinecone
- PostgreSQL (checkpoint storage)
- Redis (caching)
- WebSocket / SSE

**Ports**: 8001 (internal)

---

### 4. Scraper Service (Optional Separation)

**Path**: `services/scraper/`

**Responsibilities**:
- Naver Cafe web scraping
- Content preprocessing (keywords, summary)
- Vector ingestion
- Scheduled tasks

> **Note**: This service can remain in Django core if resource constraints exist. Separate only if:
> - Scraping needs independent scaling
> - Playwright resource usage affects other services
> - Different deployment lifecycle needed

```
services/scraper/
├── Dockerfile
├── Dockerfile.prod                 # Includes Playwright browsers
├── pyproject.toml
│
├── src/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry + APScheduler setup
│   ├── config.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── scraper.py          # Scraping control endpoints
│   │       ├── stats.py            # Statistics endpoints
│   │       └── health.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scraper.py              # Playwright scraping logic
│   │   ├── parser.py               # HTML parsing
│   │   └── preprocessor.py         # AI preprocessing
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── browser.py              # Playwright browser management
│   │   ├── ingest.py               # Vector DB ingestion
│   │   └── scheduler.py            # APScheduler job definitions
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py              # Pydantic models
│   │   └── db.py                   # SQLAlchemy models
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── tests/
│   └── ...
│
└── scripts/
    ├── export_data.py
    └── import_data.py
```

**Tech Stack**:
- FastAPI
- Playwright
- BeautifulSoup4
- APScheduler (scheduled tasks)
- Pinecone
- PostgreSQL

**Ports**: 8002 (internal)

---

## Infrastructure

### nginx/ (Main Reverse Proxy)

```
nginx/
├── Dockerfile
├── nginx.conf
└── conf.d/
    ├── default.conf
    ├── upstream.conf              # Service upstreams
    └── ssl.conf                   # SSL configuration
```

**Routing Example** (`conf.d/default.conf`):
```nginx
# API routes
location /api/v1/auth/ {
    proxy_pass http://core:8000;
}

location /api/v1/content/ {
    proxy_pass http://core:8000;
}

location /api/v1/chat/ {
    proxy_pass http://agent:8001;
}

location /api/v1/scraper/ {
    proxy_pass http://scraper:8002;
}

# WebSocket
location /ws/chat/ {
    proxy_pass http://agent:8001;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

# Frontend (SPA)
location / {
    proxy_pass http://client:80;
}
```

### infra/postgres/

```
infra/postgres/
└── init.sql                        # Initial DB setup
```

```sql
-- init.sql
CREATE DATABASE changple;
CREATE DATABASE changple_langgraph;

-- User permissions
GRANT ALL PRIVILEGES ON DATABASE changple TO changple;
GRANT ALL PRIVILEGES ON DATABASE changple_langgraph TO changple;
```

---

## Docker Compose Structure

### docker-compose.yml (Development)

```yaml
version: '3.8'

services:
  # Infrastructure
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  # Services
  core:
    build:
      context: ./services/core
      dockerfile: Dockerfile
    volumes:
      - ./services/core/src:/app/src
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/changple
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  client:
    build:
      context: ./services/client
      dockerfile: Dockerfile
    volumes:
      - ./services/client/src:/app/src
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8080

  agent:
    build:
      context: ./services/agent
      dockerfile: Dockerfile
    volumes:
      - ./services/agent/src:/app/src
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/changple_langgraph
      - REDIS_URL=redis://redis:6379/1
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
    ports:
      - "8001:8001"
    depends_on:
      - postgres
      - redis

  scraper:
    build:
      context: ./services/scraper
      dockerfile: Dockerfile
    volumes:
      - ./services/scraper/src:/app/src
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/changple
      - REDIS_URL=redis://redis:6379/2
    ports:
      - "8002:8002"
    depends_on:
      - postgres
      - redis

  nginx:
    build:
      context: ./nginx
    ports:
      - "8080:80"
    depends_on:
      - core
      - client
      - agent
      - scraper

volumes:
  postgres_data:
  redis_data:
```

---

## Service Communication

```
                                    ┌─────────────┐
                                    │   Client    │
                                    │   (React)   │
                                    └──────┬──────┘
                                           │
                                           ▼
                                    ┌─────────────┐
                        ┌──────────►│    Nginx    │◄──────────┐
                        │           │  (Gateway)  │           │
                        │           └──────┬──────┘           │
                        │                  │                  │
              ┌─────────┴─────┐   ┌────────┴────────┐   ┌─────┴─────────┐
              │               │   │                 │   │               │
              ▼               ▼   ▼                 ▼   ▼               ▼
       ┌──────────┐    ┌──────────┐          ┌──────────┐        ┌──────────┐
       │   Core   │    │  Agent   │          │ Scraper  │        │  Static  │
       │ (Django) │◄──►│(FastAPI) │          │(FastAPI) │        │  Files   │
       └────┬─────┘    └────┬─────┘          └────┬─────┘        └──────────┘
            │               │                     │
            │               │                     │
            ▼               ▼                     ▼
       ┌─────────────────────────────────────────────────┐
       │                   PostgreSQL                     │
       │  ┌──────────┐  ┌──────────────┐  ┌───────────┐  │
       │  │ changple │  │  langgraph   │  │  scraper  │  │
       │  │    db    │  │  checkpoints │  │    db     │  │
       │  └──────────┘  └──────────────┘  └───────────┘  │
       └─────────────────────────────────────────────────┘
                              │
                              ▼
       ┌─────────────────────────────────────────────────┐
       │                     Redis                        │
       │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
       │  │  DB 0    │  │  DB 1    │  │  DB 2    │       │
       │  │  Core    │  │  Agent   │  │ Scraper  │       │
       │  └──────────┘  └──────────┘  └──────────┘       │
       └─────────────────────────────────────────────────┘
                              │
                              ▼
       ┌─────────────────────────────────────────────────┐
       │                   Pinecone                       │
       │              (Vector Database)                   │
       └─────────────────────────────────────────────────┘
```

---

## API Versioning & Routes

| Route Pattern | Service | Description |
|--------------|---------|-------------|
| `/api/v1/auth/*` | Core | Authentication endpoints |
| `/api/v1/users/*` | Core | User management |
| `/api/v1/content/*` | Core | Content CRUD |
| `/api/v1/chat/*` | Agent | Chat sessions & messages |
| `/api/v1/scraper/*` | Scraper | Scraping control |
| `/ws/chat/{session_id}` | Agent | WebSocket chat |
| `/*` | Client | React SPA |

---

## Migration Strategy

### Phase 1: Setup Monorepo Structure
1. Create new directory structure
2. Move Django project to `services/core/`
3. Setup shared packages

### Phase 2: Extract Frontend
1. Create React application in `services/client/`
2. Migrate static files and templates to React components
3. Implement API service layer
4. Setup nginx routing

### Phase 3: Extract Agent Service
1. Create FastAPI service in `services/agent/`
2. Move LangGraph workflow from `chatbot/bot.py`
3. Implement WebSocket handling
4. Update Core to proxy chat requests

### Phase 4: Extract Scraper Service (Optional)
1. Create FastAPI service in `services/scraper/`
2. Move scraping logic
3. Setup Celery for scheduled tasks
4. Update data synchronization

### Phase 5: Production Deployment
1. Create production Docker configurations
2. Setup CI/CD pipelines
3. Configure monitoring & logging
4. Implement health checks

---

## Environment Variables

```bash
# .env.example

# Database
POSTGRES_USER=changple
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379

# Django (Core)
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=changple.ai,localhost

# Agent Service
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX=changple-index

# Scraper Service
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...

# OAuth
SOCIAL_AUTH_NAVER_KEY=...
SOCIAL_AUTH_NAVER_SECRET=...
```

---

## Recommended Tech Stack Summary

| Layer | Technology |
|-------|------------|
| **Gateway** | Nginx |
| **Frontend** | React + TypeScript + Vite |
| **Core WAS** | Django 5 + DRF + Channels |
| **Agent** | FastAPI + LangGraph + LangChain |
| **Scraper** | FastAPI + Playwright + Celery |
| **Database** | PostgreSQL 16 |
| **Cache** | Redis 7 |
| **Vector DB** | Pinecone |
| **Container** | Docker + Docker Compose |
| **Package Manager** | uv (Python), pnpm (Node) |

---

## Notes

1. **Scraper Service**: Can remain in Django Core if separation overhead is not justified. The architecture supports both approaches.

2. **Shared Database**: Services share PostgreSQL but use separate databases/schemas to maintain loose coupling.

3. **Authentication**: JWT tokens issued by Core service, validated by all services using shared secret/public key.

4. **Monitoring**: Consider adding Prometheus + Grafana for metrics, and centralized logging (ELK stack or similar).

5. **CI/CD**: Each service can have independent CI/CD pipelines while sharing common infrastructure configs.
