# Changple AI v3.0 - Architecture Refactoring & Scaling Plan

> **Date**: 2026-02-16
> **Status**: Proposal (not yet implemented)
> **Scope**: WebSocket→SSE migration, scraper decoupling, memory upgrade, architectural cleanup

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [New Architecture Overview](#2-new-architecture-overview)
3. [WebSocket → SSE Migration](#3-websocket--sse-migration)
4. [Scraper Pipeline Decoupling](#4-scraper-pipeline-decoupling)
5. [Memory System Upgrade](#5-memory-system-upgrade)
6. [Authentication Between Services](#6-authentication-between-services)
7. [Refactored Directory Structure](#7-refactored-directory-structure)
8. [Migration Roadmap](#8-migration-roadmap)
9. [Risk Mitigation](#9-risk-mitigation)
10. [Key Design Decisions & Rationale](#10-key-design-decisions--rationale)

---

## 1. Current Architecture Analysis

### Architecture Diagram (Current)

```
Client (Next.js:3000)
  │
  ├── REST (axios) ──► Nginx ──► Core (Django:8000)
  │                                 ├── Users / Auth (Naver OAuth)
  │                                 ├── Content (Notion)
  │                                 ├── Chat History
  │                                 └── Scraper + Ingestion (Celery)
  │
  └── WebSocket ─────► Nginx ──► Agent (FastAPI:8001)
                                    ├── LangGraph RAG workflow
                                    ├── Pinecone retrieval
                                    └── PostgreSQL checkpointing
```

### Identified Issues

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | Global mutable `_resources` dict instead of FastAPI DI | `agent/src/main.py` | Medium |
| 2 | Singleton graph app with stale references | `agent/src/graph/builder.py` | Medium |
| 3 | No authentication on WebSocket endpoint | `agent/src/api/websocket.py` | **High** |
| 4 | Fire-and-forget `asyncio.create_task` for message handling | `agent/src/api/websocket.py` | Medium |
| 5 | Redis polled on every `astream_events` chunk (hundreds of round-trips) | `agent/src/api/websocket.py` | Medium |
| 6 | `os.environ` mutation for API keys (not thread-safe) | `agent/src/graph/nodes.py`, `vectorstore.py` | Medium |
| 7 | Hardcoded `[-5:]` message trimming with no summarization | `agent/src/graph/nodes.py` (5 locations) | **High** |
| 8 | Internal APIs use `AllowAny` (no service auth) | Core's internal views | **High** |
| 9 | Scraper + ingestion tightly coupled in one module | `core/src/scraper/ingest/` | Medium |
| 10 | WebSocket is stateful, complicating HA/load balancing | Architecture-level | Medium |

---

## 2. New Architecture Overview

### Architecture Diagram (Proposed)

```
┌──────────────┐  POST /api/v1/chat/{nonce}/messages   ┌─────────────┐
│              │ ─────────────────────────────────────► │             │
│   Client     │  ◄── SSE: text/event-stream ──────── │   Agent     │
│  (Next.js)   │                                       │  (FastAPI)  │
│              │  POST /api/v1/chat/{nonce}/stop        │             │
│              │ ─────────────────────────────────────► │             │
└──────────────┘                                       └──────┬──────┘
       │                                                      │
       │   GET /api/v1/chat/history (etc)                    │ httpx +
       │ ──────────────► Core (Django) ◄─────────────────────┘ X-Internal-Auth
       │                       │
       │                  ┌────┴─────┐
       │                  │ Pipeline │
       │                  │Orchestr. │
       │                  │ (Celery) │
       │                  └────┬─────┘
       │               ┌──────┼──────┐
       │               ▼      ▼      ▼
       │            Scrape  Process  Embed/Store
       │           (Naver)  (Gemini) (OpenAI + Pinecone)
       │           (YouTube*)
       │           (Blog*)        * = future sources
       │
       └──── PostgreSQL ──── Redis ──── Pinecone
```

### SSE Event Flow

```
Client                              Agent
  │  POST /chat/{nonce}/messages      │
  │  {content, content_ids, user_id}  │
  │ ──────────────────────────────►   │
  │                                   │── route_query()
  │  event: status                    │
  │  data: {"message":"분석 중..."}   │◄─┘
  │◄──────────────────────────────    │
  │                                   │── generate_queries() → retrieve → filter
  │  event: status (x3)              │
  │◄──────────────────────────────    │
  │                                   │── respond_with_docs() streaming
  │  event: chunk                     │
  │  data: {"content":"답변 토큰"}    │
  │◄────────────── (repeated) ────    │
  │                                   │
  │  event: end                       │
  │  data: {source_documents, ...}    │
  │◄──────────────────────────────    │
  │                                   │── save messages to Core
```

### Memory System Flow

```
Before compaction (22 messages):
  [msg_1, msg_2, ..., msg_12, msg_13, ..., msg_22]
   └──── to summarize ────┘   └── sliding window ──┘

After compaction (11 messages):
  [summary_of_1_to_12, msg_13, msg_14, ..., msg_22]
   └─ SystemMessage ──┘  └──── sliding window ────┘

Trigger: total messages > 20 (SUMMARIZE_THRESHOLD)
Window:  keep last 10 messages (WINDOW_SIZE)
```

---

## 3. WebSocket → SSE Migration

### Why SSE over WebSocket?

| Aspect | WebSocket | SSE (Proposed) |
|--------|-----------|----------------|
| Load balancing | Sticky sessions required | Standard HTTP LB works |
| Connection state | Persistent, server tracks | Stateless per-request |
| Reconnection | Manual with exponential backoff | Built-in retry or per-request |
| HTTP/2 compatibility | Requires upgrade handshake | Native multiplexing |
| Proxy/CDN support | Requires explicit config | Works by default |
| Bidirectional | Yes (not needed for chat) | No (we use POST for input) |
| Scalability | One connection per user | No persistent connections |

### API Endpoints (Agent Service)

#### Send Message + Stream Response
```
POST /api/v1/chat/{nonce}/messages
Content-Type: application/json

Request Body:
{
  "content": "창플에서 추천하는 프랜차이즈가 있나요?",
  "content_ids": [123, 456],    // Optional: user-selected content for RAG
  "user_id": 42                  // From authenticated session
}

Response: text/event-stream
Headers:
  Cache-Control: no-cache
  Connection: keep-alive
  X-Accel-Buffering: no

Event stream:
  event: status
  data: {"message": "어떤 정보가 필요한지 분석하고 있습니다"}

  event: status
  data: {"message": "관련 문서를 검색하고 있습니다"}

  id: 1
  event: chunk
  data: {"content": "창플에서 추천하는 "}

  id: 2
  event: chunk
  data: {"content": "프랜차이즈는 "}

  ... (many chunks)

  event: end
  data: {"source_documents": [{"id": 789, "title": "...", "source": "https://..."}], "processed_content": "full response text"}
```

#### Stop Generation
```
POST /api/v1/chat/{nonce}/stop

Response:
{"status": "stop_requested"}
```

### SSE Server Implementation (FastAPI)

```python
@router.post("/{nonce}/messages")
async def send_and_stream(
    nonce: str,
    request: ChatSendRequest,
    core_client: CoreClient = Depends(get_core_client),
    redis_service: RedisService = Depends(get_redis_service),
    app = Depends(get_graph_app),
):
    """Send a message and receive SSE stream response."""

    async def event_generator() -> AsyncGenerator[str, None]:
        # 1. Validate session, manage memory
        # 2. Clear stop flag, set generating guard
        # 3. Fetch user-attached content if content_ids provided
        # 4. Run LangGraph with astream_events(v2)
        # 5. Map events to SSE: status/chunk/end
        # 6. Background: poll stop flag every 500ms (not every chunk)
        # 7. Background: send heartbeat every 15s
        # 8. Save messages to Core on completion

        config = {"configurable": {"thread_id": nonce}}

        # Memory management before graph invocation
        checkpoint = await app.aget_state(config)
        if checkpoint and checkpoint.values.get("messages"):
            managed = await manage_memory(checkpoint.values["messages"])
            if len(managed) != len(checkpoint.values["messages"]):
                await app.aupdate_state(config, {"messages": managed})

        yield sse_event("status", {"message": "분석 중..."})

        async for event in app.astream_events(input_data, config=config, version="v2"):
            if stop_event.is_set():
                yield sse_event("stopped", {})
                return
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield sse_event("chunk", {"content": chunk.content})
            elif event["event"] == "on_chain_start" and event["name"] in status_map:
                yield sse_event("status", {"message": status_map[event["name"]]})

        yield sse_event("end", {
            "source_documents": source_documents,
            "processed_content": full_response,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### SSE Client Implementation (Next.js)

```typescript
// lib/sse.ts - fetch-based SSE (supports POST, unlike native EventSource)
export async function streamChat(
  nonce: string,
  content: string,
  options: {
    contentIds?: number[];
    userId?: number | null;
    onStatus?: (message: string) => void;
    onChunk?: (content: string) => void;
    onEnd?: (data: { source_documents: SourceDocument[]; processed_content: string }) => void;
    onStopped?: () => void;
    onError?: (message: string) => void;
    signal?: AbortSignal;  // For stop generation via AbortController
  }
): Promise<void> {
  const response = await fetch(`/api/v1/chat/${nonce}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, content_ids: options.contentIds ?? [], user_id: options.userId }),
    credentials: "include",  // Forward session cookie
    signal: options.signal,
  });

  if (!response.ok) throw new Error(`Chat failed: ${response.status}`);

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7);
      } else if (line.startsWith("data: ") && currentEvent) {
        const data = JSON.parse(line.slice(6));
        switch (currentEvent) {
          case "status":  options.onStatus?.(data.message); break;
          case "chunk":   options.onChunk?.(data.content); break;
          case "end":     options.onEnd?.(data); break;
          case "stopped": options.onStopped?.(); break;
          case "error":   options.onError?.(data.message); break;
        }
        currentEvent = "";
      }
    }
  }
}
```

### Nginx Configuration for SSE

```nginx
location /api/v1/chat/ {
    proxy_pass http://agent;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # SSE-critical settings
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;       # 5 min max for long responses
    chunked_transfer_encoding on;
}

# REMOVE the old WebSocket block:
# location /ws/chat/ { proxy_set_header Upgrade $http_upgrade; ... }
```

---

## 4. Scraper Pipeline Decoupling

### Why Keep Scraper in Core?

The scraper **remains in Core** (not extracted to a separate microservice). Reasons:

1. **Django ORM dependency**: The scraper writes to `NaverCafeData`, `PostStatus`, `BatchJob`, `AllowedAuthor` models. Extracting requires either model duplication or a new API layer — significant overhead for no immediate gain.

2. **Celery already provides process isolation**: The scraper runs in its own Docker container (`Dockerfile.celery`) with Playwright. It's already independently scalable via container replicas.

3. **Pipeline abstraction enables future extraction**: The refactoring introduces clear interfaces (`BaseScraper`, `BaseProcessor`, etc.) that make extraction trivial when needed.

4. **When to actually extract**: When you have 3+ content sources with conflicting resource needs, or when Celery worker scaling conflicts with Core's web server needs.

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Pipeline Orchestrator (Celery task)        │
│   orchestrator.run_incremental(source, batch_size)       │
└──┬──────────┬──────────────┬──────────────┬─────────────┘
   │          │              │              │
   ▼          ▼              ▼              ▼
┌────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐
│ Scrape │ │ Process  │ │  Embed    │ │  Store    │
│ Stage  │ │ Stage    │ │  Stage    │ │  Stage    │
├────────┤ ├──────────┤ ├───────────┤ ├───────────┤
│ Naver  │ │Summarize │ │ OpenAI    │ │ Pinecone  │
│ Cafe   │ │Keywords  │ │ Batch API │ │ Upsert    │
├────────┤ │Questions │ │           │ │           │
│YouTube*│ │(Gemini)  │ └───────────┘ └───────────┘
├────────┤ └──────────┘
│ Blog* │
└────────┘
                           * = future sources
```

### Abstract Interfaces

```python
# pipeline/base.py

class ContentSource(str, Enum):
    NAVER_CAFE = "naver_cafe"
    YOUTUBE = "youtube"         # Future
    BLOG = "blog"               # Future

@dataclass
class ScrapedItem:
    """Universal format across all content sources."""
    source: ContentSource
    source_id: str              # post_id, video_id, etc.
    title: str
    content: str
    author: str
    published_date: datetime
    url: str
    metadata: dict = field(default_factory=dict)

@dataclass
class ProcessedItem:
    """After LLM processing."""
    source_id: str
    summary: str
    keywords: list[str]
    possible_questions: list[str]
    embedding_text: str         # "제목:'...',키워드:'...',요약:'...',질문:'...'"

class BaseScraper(ABC):
    @abstractmethod
    def scrape_incremental(self, batch_size: int = 100) -> list[ScrapedItem]: ...
    @abstractmethod
    def scrape_range(self, start_id: int, end_id: int) -> list[ScrapedItem]: ...

class BaseProcessor(ABC):
    @abstractmethod
    def process_batch(self, items: list[ScrapedItem]) -> list[ProcessedItem]: ...

class BaseEmbedder(ABC):
    @abstractmethod
    def embed_batch(self, items: list[ProcessedItem]) -> list[tuple[str, list[float]]]: ...

class BaseVectorStore(ABC):
    @abstractmethod
    def upsert(self, items: list[tuple[str, list[float], dict]]) -> int: ...
    @abstractmethod
    def delete(self, ids: list[str]) -> int: ...
```

### Orchestrator

```python
# pipeline/orchestrator.py

class PipelineOrchestrator:
    def __init__(self, scraper, processor, embedder, vector_store):
        self.scraper = scraper
        self.processor = processor
        self.embedder = embedder
        self.vector_store = vector_store

    def run_incremental(self, batch_size: int = 100) -> dict:
        items = self.scraper.scrape_incremental(batch_size)
        if not items: return {"scraped": 0}
        processed = self.processor.process_batch(items)
        vectors = self.embedder.embed_batch(processed)
        stored = self.vector_store.upsert(vectors_with_metadata)
        return {"scraped": len(items), "processed": len(processed), "embedded": stored}

def get_default_pipeline(source: ContentSource = ContentSource.NAVER_CAFE):
    """Factory for standard pipeline configurations."""
    scrapers = {
        ContentSource.NAVER_CAFE: NaverCafeScraper,
        # ContentSource.YOUTUBE: YouTubeScraper,  # Add when ready
    }
    return PipelineOrchestrator(
        scraper=scrapers[source](),
        processor=GeminiProcessor(),
        embedder=OpenAIBatchEmbedder(),
        vector_store=PineconeStore(),
    )
```

### How Ingestion Works (New vs Old)

| Aspect | Old (`ingest/`) | New (`pipeline/`) |
|--------|-----------------|-------------------|
| Entry point | `ingest_docs_task` calls `ingest_docs_chunk_sync()` | `ingest_docs_task` calls `orchestrator.run_incremental()` |
| Summarization | `content_evaluator.py` mixed with ingestion | `process/summarize.py` (isolated stage) |
| Embedding | Inline in `ingest.py` | `embed/openai.py` (isolated stage) |
| Pinecone ops | Inline in `ingest.py` | `embed/pinecone.py` (isolated stage) |
| Batch API | `batch_summarize.py` + `batch_embed.py` | Same files, moved to `process/` and `embed/` |
| Adding new source | Not possible without major refactoring | Implement `BaseScraper`, register in factory |
| Cleanup | `cleanup_pinecone_vectors()` in `ingest.py` | Moved to `PineconeStore.cleanup()` |

**The Celery task flow stays the same:**
- Daily 4 AM: `submit_batch_jobs_task` → orchestrator's batch submit
- Every 30 min: `poll_batch_status_task` → orchestrator's batch poll
- Manual: `ingest_docs_task` → orchestrator's `run_incremental()`

---

## 5. Memory System Upgrade

### Current Problem

The system stores ALL messages in the LangGraph checkpointer (PostgreSQL) with no pruning. Every node call uses `state["messages"][-5:]` — a raw slice of the last 5 messages. This means:

- No context from messages beyond the last 5 (messages 1-N are invisible)
- Checkpointer serializes/deserializes all messages on every graph invocation
- No way to recall older conversation topics
- For a 50-turn conversation: 100+ messages serialized per request

### Proposed Design: Sliding Window + Summary

```
┌─────────────────────────────────────────────────────┐
│                  Memory System                       │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │         Conversation Summary (SystemMessage)   │  │
│  │  "이전 대화 요약: 사용자가 프랜차이즈 추천을  │  │
│  │   물었고, 창플 브랜드에 대해 질문했습니다..."  │  │
│  └───────────────────────────────────────────────┘  │
│                        +                             │
│  ┌───────────────────────────────────────────────┐  │
│  │         Sliding Window (last 10 messages)      │  │
│  │  These are kept verbatim in checkpoint         │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  Trigger: When total messages > 20                   │
│  Action: Summarize oldest, keep window of 10         │
└─────────────────────────────────────────────────────┘
```

### Constants

```python
WINDOW_SIZE = 10            # Keep last 10 messages (5 conversation turns)
SUMMARIZE_THRESHOLD = 20    # Trigger summarization when total > 20
SUMMARY_PREFIX = "[대화 요약] "   # Identifies summary messages
```

### Implementation

```python
# graph/memory.py

async def manage_memory(messages: list[BaseMessage]) -> list[BaseMessage]:
    """
    Compact checkpoint messages when they exceed threshold.

    Before: [msg_1, msg_2, ..., msg_22]                    (22 messages)
    After:  [summary_of_1_to_12, msg_13, ..., msg_22]     (11 messages)
    """
    # Extract existing summary if present
    has_summary = isinstance(messages[0], SystemMessage) and messages[0].content.startswith(SUMMARY_PREFIX)
    conversation = messages[1:] if has_summary else messages

    if len(conversation) <= SUMMARIZE_THRESHOLD:
        return messages  # No compaction needed

    to_summarize = conversation[:-WINDOW_SIZE]
    to_keep = conversation[-WINDOW_SIZE:]

    # Include old summary as context for incremental summarization
    summarize_input = []
    if has_summary:
        summarize_input.append(messages[0])  # Old summary
    summarize_input.extend(to_summarize)

    new_summary = await summarize_messages(summarize_input)  # Gemini call
    return [SystemMessage(content=SUMMARY_PREFIX + new_summary)] + to_keep


def get_context_messages(messages: list[BaseMessage], context_size: int = 5) -> list[BaseMessage]:
    """
    Get messages for LLM node context. Replaces hardcoded [-5:] everywhere.
    Returns: [summary (if exists)] + [last N messages]
    """
    result = []
    if messages and isinstance(messages[0], SystemMessage) and messages[0].content.startswith(SUMMARY_PREFIX):
        result.append(messages[0])
        messages = messages[1:]
    result.extend(messages[-context_size:])
    return result
```

### Integration Points

**1. Before graph invocation** (in SSE endpoint):
```python
# Compact checkpoint if needed
checkpoint = await app.aget_state(config)
if checkpoint and checkpoint.values.get("messages"):
    managed = await manage_memory(checkpoint.values["messages"])
    if len(managed) != len(checkpoint.values["messages"]):
        await app.aupdate_state(config, {"messages": managed})
```

**2. In every node** (replace hardcoded slicing):
```python
# Before (in route_query, respond_simple, generate_queries, respond_with_docs):
trimmed = state["messages"][-5:]

# After:
from src.graph.memory import get_context_messages
context = get_context_messages(state["messages"])
```

### Why This Approach Works

- **Incremental summarization**: Each compaction includes the previous summary, so context accumulates across multiple compactions
- **Raw backup in Core**: `ChatMessage` in Django stores ALL messages permanently. The checkpoint is "working memory," Core is the archive
- **Minimal LLM cost**: Summarization only triggers once per ~10 turns (using Gemini Flash, which is cheap)
- **LangGraph compatible**: Uses standard `SystemMessage` — no changes to checkpointer or graph builder needed

---

## 6. Authentication Between Services

### Current Security Gaps

1. **Agent WebSocket has no auth**: `user_id` is sent as a plain field in the message payload. Any client can impersonate any user.
2. **Internal APIs use `AllowAny`**: Agent→Core calls have no authentication. Any network client can create sessions and save messages.

### Proposed Three-Layer Auth

```
┌─────────────────────────────────────────────────────────────┐
│                   Authentication Layers                       │
│                                                               │
│  Layer 1: Client → Core (User-facing)                        │
│  ─────────────────────────────────────                       │
│  Method: Django session cookie + CSRF token                   │
│  Status: Already implemented                                  │
│  Flow: Naver OAuth → session cookie → CSRF on mutations      │
│                                                               │
│  Layer 2: Client → Agent (Chat SSE)                          │
│  ──────────────────────────────────                          │
│  Method: Session cookie forwarded + validated via Core        │
│  Implementation:                                              │
│    1. Client sends session cookie with fetch (credentials)   │
│    2. Agent middleware extracts cookie                         │
│    3. Agent calls Core /api/v1/auth/status/ with cookie      │
│    4. If authenticated, extract user_id from response         │
│    5. Cache validation for request duration                   │
│                                                               │
│  Layer 3: Agent → Core (Internal APIs)                       │
│  ─────────────────────────────────────                       │
│  Method: Shared secret header                                 │
│  Implementation:                                              │
│    1. Both services share INTERNAL_API_KEY env var            │
│    2. Agent sends X-Internal-Auth: {key} header              │
│    3. Core internal views verify header                       │
│    4. Nginx blocks /api/v1/*/internal/* from external        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Agent Auth Middleware

```python
# agent/src/api/middleware.py

async def validate_session(request: Request, core_client: CoreClient) -> Optional[int]:
    """
    Validate Django session cookie by forwarding to Core.
    Returns user_id if authenticated, None otherwise.
    """
    session_cookie = request.cookies.get("sessionid")
    if not session_cookie:
        return None

    # Forward cookie to Core's auth status endpoint
    response = await core_client.client.get(
        "/api/v1/auth/status/",
        cookies={"sessionid": session_cookie},
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("is_authenticated"):
            return data["user"]["id"]
    return None
```

### Core Internal Auth

```python
# core/src/common/permissions.py

class InternalServicePermission(BasePermission):
    """Verify X-Internal-Auth header for service-to-service calls."""

    def has_permission(self, request, view):
        expected = settings.INTERNAL_API_KEY
        provided = request.headers.get("X-Internal-Auth")
        return provided and provided == expected
```

### Nginx Defense-in-Depth

```nginx
# Block external access to internal APIs
location ~ /api/v1/.*/internal/ {
    allow 172.16.0.0/12;   # Docker network
    allow 10.0.0.0/8;      # Internal network
    deny all;
}
```

---

## 7. Refactored Directory Structure

### Agent Service

```
services/agent/src/
├── api/
│   ├── __init__.py
│   ├── router.py              # Registers all routes
│   ├── health.py              # Health check endpoints
│   ├── chat.py                # NEW: REST + SSE endpoints
│   ├── dependencies.py        # NEW: FastAPI Depends() for resources
│   ├── middleware.py           # NEW: Auth validation middleware
│   └── websocket.py           # DELETE after migration complete
├── graph/
│   ├── __init__.py
│   ├── builder.py             # Graph construction
│   ├── checkpointer.py        # PostgreSQL checkpoint
│   ├── nodes.py               # UPDATE: use get_context_messages()
│   ├── prompts.py             # System prompts (Korean)
│   ├── state.py               # AgentState schema
│   └── memory.py              # NEW: sliding window + summarization
├── schemas/
│   ├── __init__.py
│   └── chat.py                # UPDATE: SSE event models
├── services/
│   ├── __init__.py
│   ├── core_client.py         # UPDATE: add X-Internal-Auth header
│   ├── redis.py               # Stop flags
│   └── vectorstore.py         # UPDATE: pass API keys via constructor
├── config.py
└── main.py                    # UPDATE: DI refactor, SSE routes
```

### Core Service - Scraper Module

```
services/core/src/scraper/
├── models.py                  # NaverCafeData, PostStatus, BatchJob, etc.
├── admin.py
├── api_views.py               # UPDATE: InternalServicePermission on internal views
├── serializers.py
├── urls.py
├── tasks.py                   # UPDATE: thin wrappers calling orchestrator
├── pipeline/                  # NEW: replaces ingest/
│   ├── __init__.py
│   ├── base.py                # Abstract interfaces
│   ├── orchestrator.py        # Pipeline coordinator
│   ├── scrape/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract scraper for future sources
│   │   └── naver_cafe.py      # Existing Playwright scraper logic
│   ├── process/
│   │   ├── __init__.py
│   │   ├── summarize.py       # From batch_summarize.py (Gemini Batch)
│   │   └── evaluate.py        # From content_evaluator.py
│   └── embed/
│       ├── __init__.py
│       ├── openai.py          # From batch_embed.py (OpenAI Batch)
│       └── pinecone.py        # Pinecone upsert/cleanup from ingest.py
├── ingest/                    # DELETE after pipeline verified
│   ├── ingest.py
│   ├── content_evaluator.py
│   ├── batch_summarize.py
│   └── batch_embed.py
└── management/commands/
    └── import_chunked_data.py
```

### Client Service

```
services/client/src/
├── lib/
│   ├── sse.ts                 # NEW: fetch-based SSE client
│   ├── websocket.ts           # DELETE after migration
│   ├── api.ts                 # Axios instance + CSRF
│   └── utils.ts
├── hooks/
│   ├── use-chat.ts            # UPDATE: SSE instead of WebSocket
│   ├── use-auth.ts
│   ├── use-chat-history.ts
│   └── use-content.ts
└── ... (rest unchanged)
```

---

## 8. Migration Roadmap

### Phase 0: Preparatory Cleanup (Day 1-2)

| Step | Task | Files |
|------|------|-------|
| 0.1 | Create `api/dependencies.py` with FastAPI `Depends()` | New `dependencies.py`, update `main.py` |
| 0.2 | Fix `os.environ` mutations → pass keys via constructors | `nodes.py`, `vectorstore.py` |
| 0.3 | Extract `[-5:]` into `CONTEXT_WINDOW_SIZE = 5` constant | `nodes.py` (5 locations) |
| 0.4 | Add `INTERNAL_API_KEY` env var + `X-Internal-Auth` header | `core_client.py`, Core internal views |

### Phase 1: Memory System (Day 3-5)

| Step | Task | Files |
|------|------|-------|
| 1.1 | Create `graph/memory.py` with `manage_memory()` + `get_context_messages()` | New `memory.py` |
| 1.2 | Update all nodes to use `get_context_messages()` | `nodes.py` |
| 1.3 | Hook memory into WebSocket handler (temporary, before SSE) | `websocket.py` |
| 1.4 | Test with 20+ turn conversations | Manual testing |

### Phase 2: SSE Migration (Day 6-10)

| Step | Task | Files |
|------|------|-------|
| 2.1 | Create `api/chat.py` with SSE endpoints | New `chat.py` |
| 2.2 | Create `api/middleware.py` for session validation | New `middleware.py` |
| 2.3 | Register SSE routes alongside existing WS | `main.py`, `router.py` |
| 2.4 | Create `lib/sse.ts` client | New `sse.ts` |
| 2.5 | Update `useChat` hook (feature flag for SSE vs WS) | `use-chat.ts` |
| 2.6 | Update nginx (disable buffering, remove WS block) | `default.conf` |
| 2.7 | Parallel testing (both WS and SSE active) | Manual + browser |
| 2.8 | Remove WebSocket code | `websocket.py`, `websocket.ts`, nginx |

### Phase 3: Scraper Decoupling (Day 11-13)

| Step | Task | Files |
|------|------|-------|
| 3.1 | Create `pipeline/base.py` with abstract interfaces | New file |
| 3.2 | Move scraping logic to `pipeline/scrape/naver_cafe.py` | New file |
| 3.3 | Move processing to `pipeline/process/` | New files |
| 3.4 | Move embedding to `pipeline/embed/` | New files |
| 3.5 | Create `pipeline/orchestrator.py` | New file |
| 3.6 | Update `tasks.py` to use orchestrator | `tasks.py` |
| 3.7 | Test pipeline, then delete old `ingest/` | Remove old files |

### Phase 4: Verification & Cleanup (Day 14-15)

| Step | Task |
|------|------|
| 4.1 | Full end-to-end chat via SSE |
| 4.2 | Long conversation memory compaction test |
| 4.3 | Scraper pipeline through orchestrator |
| 4.4 | Update `CLAUDE.md` to reflect new architecture |

---

## 9. Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **SSE connection drops silently** | Lost response mid-stream | Medium | Send heartbeat events every 15s; include event IDs for reconnection; nginx `proxy_read_timeout 300s` |
| **Memory summarization loses critical context** | Degraded answer quality | Low-Medium | High threshold (20 msgs); incremental summarization; raw messages preserved in Core's ChatMessage as backup |
| **Concurrent SSE streams on same session** | Race condition in LangGraph | Medium | Redis `agent:generating:{nonce}` guard flag with TTL |
| **POST-based SSE + auth** | Unauthorized access | Low | Agent validates session cookie via Core; Nginx blocks internal APIs externally |
| **Scraper refactoring breaks ingestion** | Data pipeline disruption | Low | Keep old `ingest/` until pipeline verified; same Celery task signatures; internal refactoring only |
| **Stop generation race condition** | Orphaned generation task | Low | Existing Redis flag pattern preserved; poll every 500ms instead of per-chunk |
| **nginx buffering prevents SSE** | Client receives no stream | Low | `proxy_buffering off; X-Accel-Buffering: no` — tested in Phase 2.7 |

---

## 10. Key Design Decisions & Rationale

### 1. Single POST→SSE (not two-step POST+GET)

**Decision**: `POST /chat/{nonce}/messages` returns SSE directly.

**Why**: Avoids Redis coordination for pending messages. Simpler client code. The trade-off (POST returning streaming body is unconventional) is acceptable because `fetch()` handles it natively.

**Alternative considered**: POST creates message → returns stream URL → client GETs stream. Rejected due to race condition window and added complexity.

### 2. Scraper stays in Core

**Decision**: Refactor into pipeline interfaces within Core, not a separate microservice.

**Why**: Django ORM dependency, Celery already provides isolation, pipeline abstraction makes future extraction easy. Premature microservice extraction adds deployment complexity without proportional benefit.

### 3. SystemMessage for conversation summary

**Decision**: Store summary as a `SystemMessage` with prefix in the checkpoint message list.

**Why**: Works with existing checkpointer without schema changes. `get_context_messages()` naturally includes it. No need for a separate database table or state field.

### 4. Heartbeat + Event IDs for SSE reliability

**Decision**: Send `event: heartbeat` every 15s and include `id:` field on chunk events.

**Why**: SSE connections can silently drop behind load balancers. Heartbeat keeps the connection alive. Event IDs enable future `Last-Event-ID` based reconnection.

### 5. Shared secret for internal auth

**Decision**: `INTERNAL_API_KEY` env var + `X-Internal-Auth` header.

**Why**: Simplest secure option for service-to-service auth in a Docker Compose deployment. No need for JWT or mTLS at this scale. Nginx IP restriction adds defense-in-depth.

### 6. 500ms stop-flag polling (not per-chunk)

**Decision**: Background `asyncio.Task` polls Redis every 500ms, sets a local `asyncio.Event`.

**Why**: Current implementation hits Redis on every `astream_events` iteration (hundreds of times per response). 500ms polling reduces Redis load by ~100x while maintaining <1s stop latency.
