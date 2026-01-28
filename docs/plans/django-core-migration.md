# Plan: Django Core Service Migration

## Objective
Migrate Django from changple2 monolith to changple3 Core service (pure REST API, no templates/ASGI).

---

## Decision: Ingestion Location

### Recommendation: Keep Ingestion in Django Core with Celery

**Reasons:**
1. **Django ORM dependency**: Ingestion reads/writes `NaverCafeData`, `AllowedAuthor`, `PostStatus` models
2. **Celery already in Core**: Task orchestration, scheduling, chunked parallel processing
3. **LLM calls are synchronous**: Summarization runs inside Celery tasks (not async)
4. **Simpler architecture**: No inter-service communication needed for ingestion pipeline

**Ingestion Pipeline (stays in Core):**
```
Celery Beat (4 AM) → Scraper Tasks → NaverCafeData (DB)
                          ↓
                   Ingest Tasks → LLM Batch (Gemini) → Embeddings Batch (OpenAI) → Pinecone
```

**Cost Optimization - Provider Batch APIs (50% savings):**

> **Important**: LangChain's `batch()` is client-side parallelization (same cost).
> Use **Provider Batch APIs** for actual 50% cost reduction with 24-hour turnaround.

### Gemini Batch API (Summarization)
```python
# scraper/ingest/batch_summarize.py
import google.generativeai as genai

def submit_summarization_batch(posts: list[NaverCafeData]) -> str:
    """Submit batch job to Gemini - returns job_name for polling."""

    # Prepare inline requests
    requests = [
        {
            "contents": [{"role": "user", "parts": [{"text": build_prompt(post)}]}],
            "generation_config": {"response_mime_type": "application/json"}
        }
        for post in posts
    ]

    # Submit batch (50% cost, 24-hour SLA)
    job = genai.batches.create(
        model="gemini-2.0-flash",
        requests=requests
    )
    return job.name  # Store for polling


def check_and_retrieve_results(job_name: str) -> list[dict] | None:
    """Poll job status and retrieve results when complete."""
    job = genai.batches.get(job_name)

    if job.state == "JOB_STATE_SUCCEEDED":
        return job.response.inline_responses
    elif job.state in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED"):
        raise Exception(f"Batch job failed: {job.state}")

    return None  # Still processing
```

### OpenAI Batch API (Embeddings)
```python
# scraper/ingest/batch_embed.py
from openai import OpenAI

def submit_embedding_batch(texts: list[str]) -> str:
    """Submit embedding batch to OpenAI - returns batch_id."""
    client = OpenAI()

    # Create JSONL file
    requests = [
        {
            "custom_id": f"post-{i}",
            "method": "POST",
            "url": "/v1/embeddings",
            "body": {
                "model": "text-embedding-3-large",
                "input": text
            }
        }
        for i, text in enumerate(texts)
    ]

    # Upload and submit (50% cost, 24-hour SLA)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl') as f:
        for req in requests:
            f.write(json.dumps(req) + '\n')
        f.flush()

        uploaded = client.files.create(file=open(f.name, 'rb'), purpose="batch")
        batch = client.batches.create(
            input_file_id=uploaded.id,
            endpoint="/v1/embeddings",
            completion_window="24h"
        )

    return batch.id
```

### Celery Workflow (2-phase async)
```
Phase 1: Submit batch jobs (runs at 4 AM)
├── submit_summarization_batch() → store job_name in DB
└── Wait for Gemini batch to complete

Phase 2: Process results (polling task every 30 min)
├── check_and_retrieve_results() → update NaverCafeData
├── submit_embedding_batch() → store batch_id in DB
└── Wait for OpenAI batch to complete

Phase 3: Ingest to Pinecone (after embeddings ready)
└── Upsert vectors to Pinecone
```

**What moves to Agent:**
- LangGraph workflow (`bot.py`) - real-time streaming
- WebSocket chat handling
- RAG responses with streaming

---

## Architecture Change: MTV → DRF Only

### Remove (Django MTV/Templates)
- All HTML templates (`templates/`)
- Static files for frontend (`static/`)
- Template views (`views.py` with `render()`)
- Channels/Daphne/ASGI

### Keep (Django REST Framework)
- `api_views.py` → REST API endpoints
- `serializers.py` → Request/response serialization
- Models, Admin, Celery tasks

---

## Package Versions (Latest Stable)

| Package | Version | Notes |
|---------|---------|-------|
| Django | 6.0.x | Latest stable (released Dec 2025) |
| djangorestframework | 3.15.x | Latest stable |
| python-social-auth[django] | 4.5.x | Naver OAuth |
| celery | 5.4.x | Task queue |
| redis | 5.2.x | Broker + cache |
| psycopg[binary] | 3.2.x | PostgreSQL async driver |
| playwright | 1.50.x | Headless browser |
| beautifulsoup4 | 4.12.x | HTML parsing |
| pillow | 11.x | Image processing |
| pillow-heif | 0.21.x | HEIC conversion |
| langchain | 0.3.x | AI framework (for ingestion) |
| langchain-google-genai | 2.1.x | Gemini LLM |
| langchain-openai | 0.3.x | Embeddings |
| langchain-pinecone | 0.2.x | Vector store |

---

## Directory Structure

```
services/core/
├── Dockerfile              # Web server (gunicorn)
├── Dockerfile.celery       # Celery worker (with Playwright)
├── pyproject.toml          # uv dependencies
├── manage.py
├── src/
│   ├── _changple/          # Project config
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── wsgi.py         # WSGI only (no ASGI)
│   │   └── celery.py
│   │
│   ├── users/              # User management
│   │   ├── models.py       # Custom User model
│   │   ├── api_views.py    # DRF views
│   │   ├── serializers.py
│   │   ├── backends.py     # Auth backends
│   │   ├── pipeline.py     # OAuth pipeline
│   │   ├── middleware.py   # Naver auth middleware
│   │   ├── admin.py
│   │   └── urls.py
│   │
│   ├── content/            # Notion content
│   │   ├── models.py       # NotionContent, ViewHistory
│   │   ├── api_views.py
│   │   ├── serializers.py
│   │   ├── admin.py
│   │   └── urls.py
│   │
│   ├── chat/               # Chat session management
│   │   ├── models.py       # ChatSession, ChatMessage
│   │   ├── api_views.py    # History APIs only
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── scraper/            # Scraping + ingestion
│   │   ├── models.py       # NaverCafeData, AllowedAuthor
│   │   ├── api_views.py    # Scraper control APIs
│   │   ├── serializers.py
│   │   ├── tasks.py        # Celery tasks
│   │   ├── ingest/         # Ingestion logic
│   │   │   ├── ingest.py
│   │   │   └── content_evaluator.py
│   │   ├── admin.py
│   │   └── urls.py
│   │
│   └── common/             # Shared utilities
│       ├── models.py       # CommonModel base
│       └── pagination.py
│
├── tests/
└── media/                  # Uploaded files
```

---

## Models to Migrate

### 1. users/models.py
```python
class User(AbstractUser):
    user_type = CharField(choices=[("admin", "Admin"), ("social", "Social User")])
    provider = CharField(max_length=30)      # "naver"
    social_id = CharField(max_length=100)    # Naver unique ID
    profile_image = URLField()
    naver_access_token = TextField()         # For disconnect
    name = CharField(max_length=255)         # Korean full name
    nickname = CharField(max_length=100)
    mobile = CharField(max_length=20)
    information = JSONField(default=dict)
```

### 2. content/models.py
```python
class NotionContent(models.Model):
    title = CharField(max_length=200)
    description = TextField()
    thumbnail_img_path = ImageField()
    zip_file = FileField()
    is_preferred = BooleanField(default=False)
    html_path = CharField(editable=False)
    # Complex save() logic for zip extraction, HEIC conversion

class ContentViewHistory(models.Model):
    user = ForeignKey(User)
    content = ForeignKey(NotionContent)
    viewed_at = DateTimeField(auto_now_add=True)
```

### 3. chat/models.py
```python
class ChatSession(CommonModel):
    user = ForeignKey(User, null=True)
    nonce = UUIDField(unique=True, default=uuid.uuid4)

class ChatMessage(CommonModel):
    role = CharField(choices=[("user", "사용자"), ("assistant", "창플 AI")])
    content = TextField()
    attached_content_ids = JSONField(default=list)
    helpful_documents = ManyToManyField('scraper.NaverCafeData')
    session = ForeignKey(ChatSession)
```

### 4. scraper/models.py
```python
class NaverCafeData(CommonModel):
    title = CharField(max_length=200)
    category = CharField(max_length=200)
    content = TextField()
    author = CharField(max_length=200)
    published_date = DateTimeField()
    post_id = IntegerField(unique=True)
    keywords = JSONField()
    summary = TextField()
    possible_questions = JSONField()
    ingested = BooleanField(default=False)

class PostStatus(CommonModel):
    post_id = IntegerField(unique=True)
    status = CharField(choices=[("DELETED", "Deleted"), ("ERROR", "Error"), ("SAVED", "Saved")])

class AllowedAuthor(models.Model):
    name = CharField(unique=True)
    author_group = CharField(choices=[("창플", "창플"), ...])
    is_active = BooleanField(default=True)

class GoodtoKnowBrands(models.Model):
    name = CharField(unique=True)
    description = TextField()
    is_goodto_know = BooleanField(default=True)

# NEW: Track async batch jobs for 50% cost savings
class BatchJob(CommonModel):
    JOB_TYPE_CHOICES = [("summarize", "Summarization"), ("embed", "Embedding")]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed")
    ]

    job_type = CharField(choices=JOB_TYPE_CHOICES)
    provider = CharField(max_length=20)         # "gemini" or "openai"
    job_id = CharField(max_length=255)          # job_name or batch_id
    status = CharField(choices=STATUS_CHOICES, default="pending")
    post_ids = JSONField(default=list)          # NaverCafeData IDs in this batch
    result_file = CharField(blank=True)         # Path to results if file-based
    error_message = TextField(blank=True)
```

---

## API Endpoints

### Users (`/api/v1/users/`, `/api/v1/auth/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/naver/login/` | Initiate Naver OAuth |
| GET | `/auth/naver/callback/` | OAuth callback |
| POST | `/auth/logout/` | Logout |
| GET | `/users/me/` | Current user profile |
| DELETE | `/users/withdraw/` | Delete account + disconnect Naver |

### Content (`/api/v1/content/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/content/columns/` | List content (paginated) |
| GET | `/content/preferred/` | Featured content |
| GET | `/content/recommended/{id}/` | Recommendations |
| GET | `/content/history/` | User view history |
| POST | `/content/view/` | Record view |
| POST | `/content/attachment/` | Get content text for chat |

### Chat (`/api/v1/chat/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/chat/history/` | User's chat sessions |
| GET | `/chat/{nonce}/messages/` | Messages in session |

### Scraper (`/api/v1/scraper/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scraper/run/` | Trigger scraping |
| POST | `/scraper/ingest/` | Trigger ingestion |
| GET | `/scraper/status/` | Task status |

---

## Implementation Steps

### Phase 1: Project Setup
1. Create `services/core/pyproject.toml` with dependencies
2. Create Django project structure under `src/`
3. Configure settings (base, dev, prod)
4. Create Dockerfiles (web + celery)

### Phase 2: Models Migration
1. Migrate `users/models.py` with User model
2. Migrate `content/models.py` with NotionContent
3. Migrate `chat/models.py` (ChatSession, ChatMessage)
4. Migrate `scraper/models.py` (NaverCafeData, etc.)
5. Create and run migrations

### Phase 3: Authentication
1. Configure social-auth-app-django for Naver
2. Migrate OAuth pipeline (`users/pipeline.py`)
3. Migrate auth backends (`users/backends.py`)
4. Migrate middleware (`users/middleware.py`)
5. Create auth API views

### Phase 4: API Views
1. Migrate content APIs (columns, preferred, history)
2. Migrate chat history APIs
3. Create scraper control APIs
4. Add OpenAPI schema (drf-spectacular)

### Phase 5: Celery Tasks
1. Configure Celery with Redis
2. Migrate scraper tasks
3. **Refactor ingestion to use Provider Batch APIs (50% savings)**:
   - Create `scraper/ingest/batch_summarize.py` for Gemini Batch API
   - Create `scraper/ingest/batch_embed.py` for OpenAI Batch API
   - Create `BatchJob` model to track job_name/batch_id and status
   - Create polling task to check batch completion every 30 min
4. Configure Celery Beat schedule:
   - `submit_batch_jobs` - 4:00 AM (submit to providers)
   - `poll_batch_status` - every 30 min (check completion)
   - `ingest_completed_batches` - after polling detects completion

### Phase 6: File Processing
1. Migrate NotionContent.save() logic
2. Test zip extraction, HEIC conversion
3. Configure media file serving

---

## CLAUDE.md Updates Needed

Add to CLAUDE.md:
1. **Ingestion decision**: Stays in Core with Celery (not Agent)
2. **No templates**: Pure DRF API (MTV → DRF)
3. **Celery worker Dockerfile**: Separate from web server

---

## Verification

1. **Unit tests**: Run `uv run pytest`
2. **API tests**: Test all endpoints with httpie/curl
3. **OAuth flow**: Test Naver login end-to-end
4. **Celery tasks**: Verify scraping and ingestion work
5. **Batch API tests**: Submit small batch, verify 50% billing
6. **Docker**: Build and run both containers
7. **Database**: Verify migrations apply cleanly

---

## Sources

- [Gemini Batch API](https://ai.google.dev/gemini-api/docs/batch-api) - 50% cost, 24-hour SLA
- [Google Blog: Batch Mode](https://developers.googleblog.com/scale-your-ai-workloads-batch-mode-gemini-api/) - Cost savings details
- [OpenAI Batch API Reference](https://platform.openai.com/docs/api-reference/batch) - JSONL format, endpoints
- [openbatch Python library](https://www.daniel-gomm.com/blog/2025/openbatch/) - Simplified batch workflow
