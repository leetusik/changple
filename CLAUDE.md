# CLAUDE.md - AI Coding Assistant Guide

## Project Overview

**Changple AI v3.0** - A Naver Cafe content scraping and RAG chatbot system with Notion content management.

This is a **monorepo MSA refactor** of the original Django monolith.

### Reference Codebase

**Old codebase**: `/Users/sugang/projects/personal/changple2` (Django monolith)

Key files to reference during migration:
- `/chatbot/bot.py` - LangGraph workflow → migrate to `services/agent/`
- `/chatbot/consumers.py` - WebSocket logic reference
- `/scraper/` - Scraping logic (stays in Core with Celery)
- `/content/models.py` - Notion content processing logic
- `/users/` - User models and OAuth flow
- `/templates/` - HTML templates for UI reference
- `/static/` - CSS/JS for styling reference (preserve look and feel)
- `/FUTURE_ARCHITECTURE.md` - Original MSA migration plan

---

## Architecture

```
changple4/
├── services/
│   ├── core/      # Django WAS (users, content, auth, scraper) - NO ASGI/Daphne
│   ├── client/    # React frontend (Next.js + assistant-ui)
│   └── agent/     # LangGraph AI agent (FastAPI + WebSocket)
├── nginx/         # Reverse proxy
├── infra/         # PostgreSQL, Redis configs
└── docs/          # Documentation
```

> **Note**: Scraper runs within Core service using Celery for background tasks, leveraging Django ORM.

### Service Communication Flow

```
Client (Next.js) → Nginx → Core (Django + Celery) / Agent (FastAPI)
                                    ↓                     ↓
                                PostgreSQL ←──────────────┘
                                    ↓
                                  Redis (cache + Celery broker)
                                    ↓
                                 Pinecone
```

### Routing

| Route | Service | Port |
|-------|---------|------|
| `/api/v1/auth/*`, `/api/v1/users/*`, `/api/v1/content/*`, `/api/v1/scraper/*` | Core | 8000 |
| `/api/v1/chat/*`, `/ws/chat/*` | Agent | 8001 |
| `/*` (SPA) | Client | 3000 |

---

## Tech Stack

### Client Service (`services/client/`)

| Layer | Technology |
|-------|------------|
| Framework | **Next.js 15** (App Router) |
| UI Components | **shadcn/ui** + custom WebSocket client |
| Styling | **TailwindCSS** (with Changple design tokens) |
| Server State | **TanStack Query** (React Query) |
| UI State | **Zustand** |
| Markdown | **react-markdown** + rehype |
| Package Manager | **pnpm** |
| Language | TypeScript |

> **UI/UX Principle**: Preserve the visual design from changple2. Reference `/templates/` and `/static/` in the old codebase. The framework changes, but the look and feel stays the same.

> **Note**: We chose shadcn/ui + custom WebSocket over assistant-ui because our Agent service uses a custom WebSocket protocol (not SSE). This gives us full control over the chat implementation without protocol translation overhead.

### Core Service (`services/core/`)

| Layer | Technology |
|-------|------------|
| Framework | **Django 6.x** |
| API | **Django REST Framework** |
| Auth | **Django Social Auth** (Naver OAuth) |
| Database | **PostgreSQL 16** |
| Cache/Broker | **Redis 7** |
| Background Tasks | **Celery** (scraper, content processing) |
| Scraping | **Playwright**, **BeautifulSoup4** |

> **IMPORTANT**: NO Channels/Daphne/ASGI. WebSocket is handled entirely by Agent service.

#### Docker Setup for Core

```
services/core/
├── Dockerfile              # Django web server (gunicorn)
├── Dockerfile.celery       # Celery worker (includes Playwright browsers)
└── ...
```

Celery worker uses a dedicated Dockerfile to avoid bloating the web server image with Playwright dependencies.

### Agent Service (`services/agent/`)

| Layer | Technology |
|-------|------------|
| Framework | **FastAPI** |
| AI Orchestration | **LangGraph** + **LangChain** |
| LLM | OpenAI, Google Generative AI |
| Vector DB | **Pinecone** |
| Real-time | WebSocket / SSE (native FastAPI) |
| Checkpoint | PostgreSQL (`langgraph-checkpoint-postgres`) |

---

## Migration Notes

### Django Core Changes

Remove from `changple2` dependencies when migrating:
- `daphne`
- `channels`
- `channels-redis`

The Core service is now pure WSGI. All real-time chat functionality moves to Agent service.

### WebSocket Migration

**Before (changple2)**: Django Channels + Daphne
**After (changple4)**: FastAPI native WebSocket in Agent service

### Scraper & Background Tasks

**Keep Celery** in Core service to leverage Django ORM for scraper logic.

Celery worker runs in a separate container with dedicated `Dockerfile.celery` that includes Playwright browsers, avoiding unnecessary dependencies in the web server image.

### Frontend Migration

**Before (changple2)**: Django templates + vanilla JavaScript
**After (changple4)**: Next.js SPA with shadcn/ui components + custom WebSocket client

> **UI/UX Guideline**: Maintain the same visual appearance as changple2. Only the framework changes (React/Next.js), not the look and feel. Reference the old templates and CSS for styling decisions.

---

## Development Commands

### Docker Compose

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d core agent

# View logs
docker compose logs -f agent

# Rebuild after dependency changes
docker compose build --no-cache core
```

### Per-Service Development

#### Client (Next.js)
```bash
cd services/client
pnpm install
pnpm dev          # Development server
pnpm build        # Production build
pnpm lint         # ESLint
pnpm type-check   # TypeScript check
```

#### Core (Django)
```bash
cd services/core
uv sync                          # Install dependencies
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py createsuperuser

```

#### Agent (FastAPI)
```bash
cd services/agent
uv sync
uv run uvicorn src.main:app --reload --port 8001

```

#### Celery Worker (for scraper tasks)
```bash
cd services/core
uv run celery -A src._changple worker -l INFO
uv run celery -A src._changple beat -l INFO   # Scheduler
```

### Database

```bash
# Access PostgreSQL
docker compose exec postgres psql -U changple -d changple

# Reset database
docker compose down -v
docker compose up -d postgres
```

---

## Coding Conventions

### Python (Django / FastAPI)

- **Formatter**: `ruff format`
- **Linter**: `ruff check`
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for complex functions
- **Imports**: Use absolute imports, sorted by ruff

```python
# Good
from src.services.llm import LLMService
from src.models.schemas import ChatRequest

# Avoid
from ..services.llm import LLMService
```

### TypeScript / React

- **Formatter**: Prettier
- **Linter**: ESLint with Next.js config
- **Components**: Functional components with TypeScript
- **Naming**: PascalCase for components, camelCase for functions/variables

```typescript
// Component file: ChatMessage.tsx
export function ChatMessage({ message }: ChatMessageProps) {
  // ...
}

// Hook file: useChat.ts
export function useChat() {
  // ...
}
```

### Git Commit Messages

Follow conventional commits:

```
feat: add user authentication flow
fix: resolve WebSocket reconnection issue
refactor: extract LLM service from bot.py
docs: update API documentation
chore: upgrade langchain to 0.3.x
```

Scope by service when relevant:
```
feat(agent): implement streaming responses
fix(core): handle Naver OAuth callback error
feat(client): add chat history sidebar
```

---

## Testing

No tests are required for this project.


---

## Configuration & Secrets

The project uses a modular configuration structure with service-specific secrets.

### 1. Root Infrastructure
`/.env` (PostgreSQL credentials only)
```bash
POSTGRES_USER=changple
POSTGRES_PASSWORD=<secure_password>
```

### 2. Core Service
`services/core/.env` (Django, Auth, Scraper AI keys)
```bash
DJANGO_SECRET_KEY=<secret>
SOCIAL_AUTH_NAVER_KEY=...
OPENAI_API_KEY=... # For scraper/ingestion
```

### 3. Agent Service
`services/agent/.env` (AI Agent keys & config)
```bash
OPENAI_API_KEY=...
LANGCHAIN_API_KEY=...
```

---

## Key Design Decisions

1. **No ASGI in Django**: Simplifies Core service. All WebSocket handled by Agent.

2. **shadcn/ui + custom WebSocket for chat**: Full control over chat UI with direct WebSocket connection to Agent service. Simpler than assistant-ui adapter pattern since our Agent uses custom WebSocket protocol (not SSE).

3. **Separate Agent service**: Isolates AI/ML dependencies, enables independent scaling.

4. **Scraper stays in Django with Celery**: Leverages Django ORM, simplifies data access. Celery worker uses dedicated Dockerfile with Playwright.

5. **Pinecone for vectors**: Managed service, no self-hosted vector DB maintenance.

6. **langgraph-checkpoint-postgres**: Native LangGraph persistence without custom implementation.

7. **Preserve UI/UX from changple2**: Frontend migration changes only the framework (Next.js), not the visual design. Match the old look and feel.

8. **Session-based auth**: Django session cookies with CSRF tokens. No JWT.

---

## Useful Links

- [shadcn/ui components](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query/latest)
- [Zustand](https://zustand-demo.pmnd.rs/)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [Next.js App Router](https://nextjs.org/docs/app)

## Implementation Plans

- [Django Core Migration Plan](docs/plans/django-core-migration.md)
- [Client Service Plan](docs/plans/client-service.md) - Next.js frontend implementation details
