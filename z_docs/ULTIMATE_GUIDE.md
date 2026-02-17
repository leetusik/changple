# Changple AI v3.0 - The Ultimate Guide

> **Last Updated**: 2026-02-17
> **Purpose**: A single source of truth for understanding this entire codebase, written for someone who wants to learn how and why everything works.
> **How to Use This Guide**: Read Part 1 first to get the big picture, then dive into whichever service interests you.

---

## Table of Contents

### Part 1: The Big Picture
- [1.1 What Is This Project?](#11-what-is-this-project)
- [1.2 Architecture Overview](#12-architecture-overview)
- [1.3 How a Chat Message Travels Through the System](#13-how-a-chat-message-travels-through-the-system)
- [1.4 How Content Gets Into the System](#14-how-content-gets-into-the-system)
- [1.5 Key Concepts You Need to Know](#15-key-concepts-you-need-to-know)

### Part 2: The Client Service (Next.js Frontend)
- [2.1 What Is Next.js and Why Do We Use It?](#21-what-is-nextjs-and-why-do-we-use-it)
- [2.2 Project Structure](#22-project-structure)
- [2.3 How Pages Work (App Router)](#23-how-pages-work-app-router)
- [2.4 Components: The Building Blocks](#24-components-the-building-blocks)
- [2.5 State Management: Where Data Lives](#25-state-management-where-data-lives)
- [2.6 How Chat Streaming Works (SSE)](#26-how-chat-streaming-works-sse)
- [2.7 How Authentication Works on the Frontend](#27-how-authentication-works-on-the-frontend)
- [2.8 Styling with Tailwind CSS](#28-styling-with-tailwind-css)

### Part 3: The Core Service (Django Backend)
- [3.1 What Is Django and Why Do We Use It?](#31-what-is-django-and-why-do-we-use-it)
- [3.2 Project Structure](#32-project-structure)
- [3.3 The Django Apps](#33-the-django-apps)
- [3.4 Database Models (How Data Is Stored)](#34-database-models-how-data-is-stored)
- [3.5 API Endpoints (How Services Talk to Core)](#35-api-endpoints-how-services-talk-to-core)
- [3.6 Authentication: Naver OAuth Flow](#36-authentication-naver-oauth-flow)
- [3.7 The Scraper Pipeline](#37-the-scraper-pipeline)
- [3.8 Celery: Background Task Processing](#38-celery-background-task-processing)

### Part 4: The Agent Service (FastAPI + LangGraph)
- [4.1 What Is This Service and Why Does It Exist?](#41-what-is-this-service-and-why-does-it-exist)
- [4.2 Project Structure](#42-project-structure)
- [4.3 The LangGraph Workflow (The AI Brain)](#43-the-langgraph-workflow-the-ai-brain)
- [4.4 How Vector Search Works (RAG)](#44-how-vector-search-works-rag)
- [4.5 SSE Streaming: How Responses Stream to the Browser](#45-sse-streaming-how-responses-stream-to-the-browser)
- [4.6 Memory Management](#46-memory-management)
- [4.7 How Agent Talks to Core](#47-how-agent-talks-to-core)

### Part 5: Infrastructure (Docker, Nginx, Databases)
- [5.1 Docker: Why and How](#51-docker-why-and-how)
- [5.2 Docker Compose: Orchestrating All Services](#52-docker-compose-orchestrating-all-services)
- [5.3 Nginx: The Traffic Director](#53-nginx-the-traffic-director)
- [5.4 PostgreSQL: The Database](#54-postgresql-the-database)
- [5.5 Redis: The Fast Helper](#55-redis-the-fast-helper)
- [5.6 Development vs Production](#56-development-vs-production)

### Part 6: Reference
- [6.1 Complete File Map](#61-complete-file-map)
- [6.2 Environment Variables Reference](#62-environment-variables-reference)
- [6.3 All API Endpoints](#63-all-api-endpoints)
- [6.4 Common Development Commands](#64-common-development-commands)
- [6.5 Existing Documentation Audit](#65-existing-documentation-audit)
- [6.6 Glossary](#66-glossary)

---

# Part 1: The Big Picture

## 1.1 What Is This Project?

**Changple AI** is a chatbot system for a Korean startup community (Naver Cafe). It does three things:

1. **Scrapes** articles from a Naver Cafe (Korean online community)
2. **Processes** those articles into a searchable knowledge base (vector database)
3. **Answers questions** by finding relevant articles and generating AI responses

Think of it like building a "ChatGPT that only knows about your company's content."

### The History

This is **version 3** (changple4 is the repo name, v3.0 is the product version). The original was a Django monolith (`changple2`) that did everything in one big application. This version splits it into three separate services (microservices) for better maintainability and scalability.

**What changed from v2 to v3:**

| Aspect | v2 (changple2) | v3 (changple4) |
|--------|----------------|----------------|
| Frontend | Django templates + vanilla JS | Next.js React SPA |
| Real-time chat | Django Channels (WebSocket) | FastAPI + SSE streaming |
| Chat backend | Inside Django | Separate Agent service |
| AI orchestration | LangGraph inside Django | Dedicated FastAPI service |
| Deployment | Single Django app | Docker microservices |

## 1.2 Architecture Overview

```
                        ┌─────────────────────────┐
                        │      User's Browser       │
                        └────────────┬──────────────┘
                                     │
                        ┌────────────▼──────────────┐
                        │     Nginx (Port 80)        │
                        │     Traffic Director        │
                        └──┬─────────┬──────────┬───┘
                           │         │          │
              /api/v1/*    │    /api/v1/chat/*  │    /*
              (REST API)   │    (AI Chat)       │    (Web Pages)
                           │         │          │
                ┌──────────▼──┐ ┌───▼────────┐ ┌▼────────────┐
                │  Core       │ │  Agent     │ │  Client     │
                │  (Django)   │ │  (FastAPI) │ │  (Next.js)  │
                │  Port 8000  │ │  Port 8001 │ │  Port 3000  │
                └──┬───┬──────┘ └──┬───┬─────┘ └─────────────┘
                   │   │           │   │
            ┌──────▼┐ ┌▼─────┐ ┌──▼┐ ┌▼────────┐
            │Postgres│ │Redis │ │   │ │Pinecone │
            │  (DB)  │ │(Cache)│ │   │ │(Vectors)│
            └────────┘ └──────┘ │   │ └─────────┘
                                │   │
                      (calls Core's REST API)
```

### The Three Services

| Service | Technology | Role | Think of it as... |
|---------|-----------|------|-------------------|
| **Client** | Next.js (React) | The user interface | The restaurant's dining room |
| **Core** | Django (Python) | Data management, auth, scraping | The kitchen and storage |
| **Agent** | FastAPI (Python) | AI chat responses | The expert chef |

### Why Three Services Instead of One?

1. **Independence**: You can update the chat AI without touching user authentication
2. **Scalability**: If chat is busy, add more Agent instances without duplicating the database logic
3. **Technology fit**: Django is great for data/auth, FastAPI is great for async streaming, Next.js is great for modern UIs
4. **Isolation**: A bug in the scraper won't crash the chat

## 1.3 How a Chat Message Travels Through the System

Let's trace what happens when a user asks: "How much money do I need to start a livestock business?"

```
Step 1: USER TYPES MESSAGE
├── Browser: User types in ChatInput component
├── React: useChat hook calls streamChat() function
└── HTTP: POST /api/v1/chat/{nonce}/stream with message body

Step 2: REQUEST REACHES AGENT SERVICE
├── Nginx: Routes /api/v1/chat/*/stream → Agent (port 8001)
├── FastAPI: Receives request, checks Redis for duplicate
└── LangGraph: Starts the AI workflow

Step 3: AI DECIDES WHAT TO DO (route_query node)
├── Gemini LLM: "Does this need document search?"
├── Answer: "Yes, retrieval_required"
└── SSE Event → Browser: status "Analyzing your question..."

Step 4: GENERATE SEARCH QUERIES (generate_queries node)
├── Agent calls Core API: GET /api/v1/scraper/internal/brands/
├── Gemini LLM: Breaks question into search queries
│   → ["livestock startup funding", "cattle farming capital", ...]
└── SSE Event → Browser: status "Generating search queries..."

Step 5: SEARCH VECTOR DATABASE (retrieve_documents node, runs in parallel)
├── OpenAI: Converts each query to a vector (list of numbers)
├── Pinecone: Finds documents with similar vectors
├── Returns: Top 4 documents per query
└── SSE Event → Browser: status "Searching relevant documents..."

Step 6: FILTER RELEVANT DOCUMENTS (documents_handler node)
├── Agent calls Core API: GET /api/v1/scraper/internal/posts/{id}/
├── Gemini LLM: "Which of these 12 documents are actually relevant?"
├── Answer: Documents 1, 3, 5, 7 are relevant
└── SSE Event → Browser: status "Analyzing search results..."

Step 7: GENERATE ANSWER (respond_with_docs node)
├── Gemini LLM: Creates answer using relevant documents
├── Streams text token by token
├── Adds citations: [1], [2] → converted to clickable links
└── SSE Events → Browser: chunk "To start a livestock...", chunk "business, you need..."

Step 8: SAVE AND CLEAN UP
├── Agent calls Core API: POST /api/v1/chat/internal/messages/bulk/
├── Core: Saves messages to PostgreSQL
├── Agent: Saves state checkpoint to PostgreSQL
├── Agent: Deletes Redis "generating" flag
└── SSE Event → Browser: end (with source documents)

Step 9: BROWSER DISPLAYS RESULT
├── MessageBubble: Renders markdown with links
├── Source documents: Shown as collapsible citations
└── User sees: Complete answer with references
```

## 1.4 How Content Gets Into the System

There are two content pipelines:

### Pipeline A: Naver Cafe Articles (Automatic)

```
Celery Beat (scheduler, runs daily at 4 AM)
    │
    ▼
NaverCafeScraper (loads posts from database)
    │
    ▼
ContentEvaluator (LLM summarizes + extracts keywords)
    │
    ▼
OpenAI Embeddings (converts text to vectors)
    │
    ▼
Pinecone (stores vectors for search)
```

This pipeline takes articles written by approved authors on the Naver Cafe and makes them searchable by the AI chatbot.

### Pipeline B: Notion Content (Manual)

```
Admin uploads ZIP file (exported from Notion)
    │
    ▼
Django processes ZIP:
  - Extracts HTML and images
  - Rewrites image paths
  - Converts HEIC/WebP to JPEG
  - Injects JavaScript for iframe integration
    │
    ▼
Stored in Django media folder
    │
    ▼
Displayed in Client via iframe
```

This pipeline handles curated content (guides, tutorials) that admins create in Notion.

## 1.5 Key Concepts You Need to Know

### What Is RAG? (Retrieval-Augmented Generation)

RAG is the core technique that makes the chatbot useful. Without RAG, an LLM can only answer from its training data. With RAG:

1. **Retrieve**: Find relevant documents from your own data
2. **Augment**: Add those documents to the LLM's prompt
3. **Generate**: LLM creates an answer using both its knowledge AND your documents

```
Without RAG:
  User: "How much does a Changple franchise cost?"
  LLM: "I don't have information about Changple." ❌

With RAG:
  User: "How much does a Changple franchise cost?"
  System: [searches Pinecone] → finds 3 relevant Naver Cafe posts
  LLM + Posts: "Based on Changple's article, the initial franchise cost
               is approximately 50M won, with details as follows... [1]" ✅
```

### What Is a Vector Database?

Text is hard for computers to compare. Vectors (lists of numbers) are easy:

```
Text: "How to start a chicken restaurant"
  ↓ OpenAI embedding model
Vector: [0.23, -0.45, 0.78, ..., 0.12]  (1536 numbers)

Text: "Chicken franchise startup guide"
  ↓ Same model
Vector: [0.25, -0.43, 0.76, ..., 0.14]  (1536 numbers, very similar!)

Text: "Korean history of the Joseon dynasty"
  ↓ Same model
Vector: [-0.82, 0.15, -0.23, ..., 0.67]  (1536 numbers, very different!)
```

Pinecone stores these vectors and can quickly find the most similar ones to any query.

### What Is SSE? (Server-Sent Events)

SSE is how the chatbot streams responses word-by-word instead of waiting for the full answer:

```
Normal HTTP:
  Client: "What is X?" ────────────────────► Server
  Client: waiting... (5 seconds)
  Client: ◄─────────── "X is a thing that..." (full response at once)

SSE (Server-Sent Events):
  Client: "What is X?" ────────────────────► Server
  Client: ◄── "X"        (0.1s)
  Client: ◄── " is"      (0.2s)
  Client: ◄── " a"       (0.3s)
  Client: ◄── " thing"   (0.4s)
  Client: ◄── " that..." (0.5s)
  (User sees text appearing in real-time, like someone typing)
```

### What Is a Nonce?

A nonce (Number used ONCE) is a unique identifier for each chat session. In this project, it's a UUID like `a1b2c3d4-e5f6-7890-abcd-ef1234567890`. It:

- Identifies which conversation we're in
- Appears in the URL: `/chat/a1b2c3d4-e5f6.../`
- Is used as the thread_id for LangGraph checkpointing
- Prevents duplicate requests (Redis lock uses it)

### What Is a Webhook/Callback?

Used in the Naver OAuth login flow:

```
1. User clicks "Login with Naver"
2. Browser goes to Naver's website
3. User enters Naver credentials on Naver's site
4. Naver calls back YOUR server with an authorization code
   (this is the "callback" URL you registered with Naver)
5. Your server exchanges the code for user information
```

---

# Part 2: The Client Service (Next.js Frontend)

## 2.1 What Is Next.js and Why Do We Use It?

**Next.js** is a React framework that adds features on top of React:

| Feature | Plain React | Next.js |
|---------|------------|---------|
| Routing | Manual (react-router) | Automatic (file-based) |
| Server rendering | Manual setup | Built-in |
| API routes | Need separate server | Built-in |
| Image optimization | Manual | Built-in |
| Code splitting | Manual | Automatic |

We use Next.js 15 with the **App Router** (the newer routing system, vs the older "Pages Router").

**Key files:**
- `services/client/package.json` - Dependencies and scripts
- `services/client/next.config.ts` - Next.js configuration
- `services/client/tsconfig.json` - TypeScript configuration

## 2.2 Project Structure

```
services/client/src/
│
├── app/                          # PAGES (URL → file mapping)
│   ├── layout.tsx               # Root layout (wraps ALL pages)
│   ├── page.tsx                 # Home page (/)
│   ├── globals.css              # Global styles
│   ├── chat/[[...nonce]]/page.tsx   # Chat page (/chat or /chat/abc123)
│   ├── content/[id]/page.tsx        # Content detail (/content/42)
│   └── api/v1/chat/[nonce]/        # API route handlers (SSE proxy)
│       ├── stream/route.ts
│       └── stop/route.ts
│
├── components/                   # REUSABLE UI PIECES
│   ├── providers.tsx            # App-wide context providers
│   ├── chat/                    # Chat-related components
│   ├── content/                 # Content-related components
│   ├── layout/                  # Page structure components
│   ├── profile/                 # User profile components
│   └── ui/                      # Basic UI components (shadcn)
│
├── hooks/                        # CUSTOM REACT HOOKS
│   ├── use-auth.ts              # Authentication state
│   ├── use-chat.ts              # Chat logic
│   ├── use-chat-history.ts      # Chat session history
│   └── use-content.ts           # Content data fetching
│
├── lib/                          # UTILITY FUNCTIONS
│   ├── api.ts                   # Axios HTTP client setup
│   ├── sse.ts                   # SSE streaming client
│   └── utils.ts                 # Helper functions
│
├── stores/                       # STATE MANAGEMENT (Zustand)
│   ├── ui-store.ts              # Modal/sidebar state
│   ├── sidebar-store.ts         # Sidebar width state
│   └── content-selection-store.ts  # Selected content checkboxes
│
└── types/                        # TYPESCRIPT DEFINITIONS
    └── index.ts                 # All type interfaces
```

## 2.3 How Pages Work (App Router)

In Next.js App Router, **folders = URLs**:

| File Path | URL |
|-----------|-----|
| `app/page.tsx` | `/` |
| `app/chat/[[...nonce]]/page.tsx` | `/chat` or `/chat/abc123` |
| `app/content/[id]/page.tsx` | `/content/42` |

### Special Syntax

- `[id]` - **Dynamic segment**: Captures part of the URL. `/content/42` gives you `id = "42"`
- `[[...nonce]]` - **Optional catch-all**: Works with or without the segment. Both `/chat` and `/chat/abc123` work
- `layout.tsx` - **Layout**: Wraps all pages in the same folder (shared header, sidebar, etc.)

### The Root Layout (`app/layout.tsx`)

This file wraps EVERY page:

```
<html>
  <body>
    <Providers>          ← React Query + Zustand providers
      <MainLayout>       ← Header + Sidebar + Content area
        {children}       ← This is where each page renders
      </MainLayout>
    </Providers>
  </body>
</html>
```

### The Chat Page (`app/chat/[[...nonce]]/page.tsx`)

The most complex page. It:
1. Reads the `nonce` from the URL (or generates a new one)
2. Renders `ChatContainer` which manages the entire chat experience
3. Handles "pending questions" (when user clicks an example question on the home page)

## 2.4 Components: The Building Blocks

React components are like LEGO pieces. Each one does one thing and can be combined.

### Component Hierarchy (How They Nest)

```
MainLayout
├── Header
│   ├── Logo
│   ├── User Avatar (opens ProfileModal)
│   └── ProfileModal
│       └── ProfileTabs (Account, Plan, Links, Company, Privacy)
│
├── Sidebar
│   ├── ContentSidebar (when viewing content)
│   │   ├── ContentList
│   │   │   └── ContentCard (× many)
│   │   └── ContentDetail (when one is selected)
│   │       └── ImageModal (for zooming images)
│   └── ChatHistory (when viewing chat history)
│
└── Main Content Area
    ├── Home Page (ChatWelcome with example questions)
    ├── Chat Page
    │   └── ChatContainer
    │       ├── MessageList
    │       │   └── MessageBubble (× many)
    │       │       └── Markdown renderer
    │       ├── StreamingIndicator (when AI is typing)
    │       └── ChatInput
    └── Content Detail Page
```

### Key Components Explained

**`ChatContainer`** (`components/chat/chat-container.tsx`)
The "brain" of the chat feature. It:
- Manages the list of messages (user + AI)
- Calls the `useChat` hook for sending/receiving messages
- Handles loading existing messages when revisiting a session
- Processes "pending questions" from the home page

**`MessageBubble`** (`components/chat/message-bubble.tsx`)
Renders a single message. Key features:
- User messages: Right-aligned, blue background
- AI messages: Left-aligned, white background, with markdown rendering
- Source citations: Collapsible list of referenced documents
- Streaming: Shows text as it arrives, character by character

**`ChatInput`** (`components/chat/chat-input.tsx`)
The text input area. Features:
- Auto-resizing textarea (grows as you type)
- Send button (or Enter key)
- Stop button (appears during AI generation)
- Login prompt (if not authenticated)
- Content attachment indicator (shows how many content items are selected)

**`ContentCard`** (`components/content/content-card.tsx`)
Shows a preview of Notion content in the sidebar:
- Thumbnail image
- Title and description
- Checkbox for selecting/attaching to chat
- Click to expand in sidebar detail view

## 2.5 State Management: Where Data Lives

State management answers the question: "Where does data live and how do components share it?"

This project uses **three different approaches** for three different types of data:

### 1. React Query (TanStack Query) - Server Data

For data that comes from the API (user info, content lists, chat history):

```typescript
// In hooks/use-auth.ts
const { data: authStatus } = useQuery({
  queryKey: ['auth', 'status'],      // Unique cache key
  queryFn: () => authApi.getStatus(), // How to fetch
  staleTime: 5 * 60 * 1000,          // Cache for 5 minutes
});
```

**Why React Query?**
- Automatic caching (don't re-fetch data you already have)
- Loading/error states built in
- Auto-refetch when user returns to tab
- Invalidation (when you logout, clear auth cache)

**Where it's used:**
- `useAuth()` - User authentication status
- `usePreferredContent()` - Featured content
- `useRecentContent()` - Paginated content list
- `useChatHistory()` - Past chat sessions
- `useSessionMessages()` - Messages in a session

### 2. Zustand Stores - UI State

For UI-only state that doesn't come from the server:

```typescript
// In stores/ui-store.ts
const useUIStore = create((set) => ({
  profileModalOpen: false,
  sidebarView: 'content',
  openProfileModal: () => set({ profileModalOpen: true }),
  setSidebarView: (view) => set({ sidebarView: view }),
}));
```

**Why Zustand?**
- Simpler than Redux (no boilerplate)
- Works outside React components
- Can persist to localStorage

**Where it's used:**
- `useUIStore` - Modal visibility, sidebar view mode
- `useSidebarStore` - Sidebar collapsed/expanded state
- `useContentSelectionStore` - Which content items are checked (persisted to localStorage)

### 3. React State (useState/useRef) - Local State

For state that only one component needs:

```typescript
// In a component
const [messages, setMessages] = useState<Message[]>([]);
const [isStreaming, setIsStreaming] = useState(false);
```

**Where it's used:**
- Message list in ChatContainer
- Input text in ChatInput
- Streaming status in useChat hook

## 2.6 How Chat Streaming Works (SSE)

This is the most technically interesting part of the client. Let's trace the full flow.

### Step 1: User Sends Message

```typescript
// In hooks/use-chat.ts → sendMessage()
const sendMessage = async (content: string) => {
  // 1. Add user message to local state immediately (optimistic UI)
  setMessages(prev => [...prev, { role: 'user', content }]);

  // 2. Start streaming from agent
  setIsStreaming(true);
  await streamChat(nonce, content, contentIds, userId, {
    onStatus: (msg) => { /* show status like "Searching..." */ },
    onChunk: (text) => { /* append text to AI message */ },
    onEnd: (data) => { /* finalize with source documents */ },
    onError: (err) => { /* show error message */ },
    onStopped: () => { /* mark as stopped */ },
  }, abortController);
};
```

### Step 2: SSE Client Connects

```typescript
// In lib/sse.ts → streamChat()
const response = await fetch(`/api/v1/chat/${nonce}/stream/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken(),  // Django CSRF protection
  },
  body: JSON.stringify({ content, content_ids, user_id }),
  signal: abortController.signal,   // For cancellation
});

// Read streaming response
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const events = parseSSEEvents(text);  // Parse "event: chunk\ndata: {...}\n\n"

  for (const event of events) {
    switch (event.type) {
      case 'chunk': callbacks.onChunk(event.data.content); break;
      case 'end':   callbacks.onEnd(event.data); break;
      // ...
    }
  }
}
```

### Step 3: Next.js API Route Proxies to Agent

Why not call Agent directly? Because:
- Agent runs on a different port/host
- Browser CORS restrictions would block it
- Next.js can handle the proxying cleanly

```typescript
// In app/api/v1/chat/[nonce]/stream/route.ts
export async function POST(request, { params }) {
  const { nonce } = params;
  const body = await request.json();

  // Forward to Agent service
  const agentResponse = await fetch(
    `${AGENT_SERVICE_URL}/api/v1/chat/${nonce}/stream`,
    { method: 'POST', body: JSON.stringify(body), headers: ... }
  );

  // Stream the response back without buffering
  return new Response(agentResponse.body, {
    headers: { 'Content-Type': 'text/event-stream' },
  });
}
```

### SSE Event Format

Each event from the server looks like this in raw text:

```
event: status
data: {"message":"Searching relevant documents..."}

event: chunk
data: {"content":"To start"}

event: chunk
data: {"content":" a livestock"}

event: chunk
data: {"content":" business,"}

event: end
data: {"source_documents":[{"id":123,"title":"Livestock Startup Guide","source":"https://..."}],"processed_content":"To start a livestock business,..."}
```

## 2.7 How Authentication Works on the Frontend

The app uses **session-based authentication** (cookies), not JWT tokens.

### Login Flow

```
1. User clicks "Login with Naver" button
2. Browser navigates to: /api/v1/auth/naver/login/
   (This goes to Core service via Nginx)
3. Core redirects browser to Naver's OAuth page
4. User enters Naver credentials
5. Naver redirects back to: /api/v1/auth/naver/callback/?code=ABC123
6. Core exchanges code for user info, creates/updates user
7. Core sets session cookie in browser
8. Browser redirects to home page
9. React app detects new cookie, fetches /api/v1/auth/status/
10. UI updates to show logged-in state
```

### CSRF Protection

Every non-GET request (POST, PATCH, DELETE) must include a CSRF token:

```typescript
// In lib/api.ts
// Axios interceptor reads the 'csrftoken' cookie that Django sets
// and adds it as 'X-CSRFToken' header to every request
api.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});
```

This prevents malicious websites from making requests on behalf of logged-in users.

## 2.8 Styling with Tailwind CSS

Instead of writing CSS files, Tailwind uses utility classes directly in HTML/JSX:

```jsx
// Traditional CSS approach:
<div className="chat-message">  // then define .chat-message in a CSS file

// Tailwind approach:
<div className="flex items-center gap-2 p-4 bg-white rounded-lg shadow-sm">
```

### Design Tokens

Custom colors and sizes are defined in `globals.css`:

```css
:root {
  --blue-1: #9CA7B9;   /* Light blue for borders */
  --blue-2: #7C99CD;   /* Links and accents */
  --blue-3: #5C89B1;   /* Hover states */
  --blue-4: #2E6FA9;   /* Primary actions */
  --grey-0: #F2F3F5;   /* Light backgrounds */
  --black:  #323232;   /* Text color */
}
```

These are available as Tailwind classes: `bg-blue-2`, `text-grey-4`, `border-grey-2`, etc.

### shadcn/ui Components

shadcn/ui is NOT a component library you install. It's a collection of components you **copy into your project** and customize. They live in `components/ui/`:

- `button.tsx` - Buttons with variants (default, outline, ghost)
- `input.tsx` - Text inputs
- `textarea.tsx` - Multi-line inputs
- `avatar.tsx` - User profile pictures
- `scroll-area.tsx` - Custom scrollable containers

These are the building blocks that the feature components (chat, content, etc.) use.

---

# Part 3: The Core Service (Django Backend)

## 3.1 What Is Django and Why Do We Use It?

**Django** is a Python web framework that gives you a LOT out of the box:

| Feature | What It Does |
|---------|-------------|
| ORM | Talk to databases with Python objects instead of SQL |
| Admin panel | Auto-generated admin interface at `/admin/` |
| Auth system | User accounts, sessions, permissions |
| Migrations | Track database schema changes |
| REST Framework | Build APIs easily (via DRF addon) |
| Security | CSRF, XSS, SQL injection protection built-in |

We use Django for the "boring but important" parts: user management, data storage, scraping, content management.

## 3.2 Project Structure

```
services/core/
├── manage.py                    # Django CLI tool
├── pyproject.toml               # Python dependencies
├── Dockerfile                   # Web server container
├── Dockerfile.celery            # Celery worker container (includes Playwright)
├── Dockerfile.beat              # Celery scheduler container
├── entrypoint.sh                # Startup script (runs migrations, starts gunicorn)
│
└── src/
    ├── _changple/               # PROJECT CONFIGURATION
    │   ├── settings/
    │   │   ├── base.py          # Shared settings
    │   │   ├── development.py   # Dev-specific settings
    │   │   └── production.py    # Prod-specific settings
    │   ├── urls.py              # URL routing (maps paths → apps)
    │   ├── wsgi.py              # Web server interface
    │   └── celery.py            # Background task configuration
    │
    ├── users/                   # USER MANAGEMENT APP
    │   ├── models.py            # User database model
    │   ├── auth_views.py        # Naver OAuth login/callback
    │   ├── api_views.py         # Profile API endpoints
    │   ├── serializers.py       # JSON conversion
    │   ├── pipeline.py          # OAuth user creation logic
    │   └── middleware.py        # Request processing
    │
    ├── content/                 # NOTION CONTENT APP
    │   ├── models.py            # NotionContent, ViewHistory models
    │   ├── api_views.py         # Content list/detail endpoints
    │   ├── serializers.py       # JSON conversion
    │   └── utils.py             # HTML processing, image conversion
    │
    ├── chat/                    # CHAT HISTORY APP
    │   ├── models.py            # ChatSession, ChatMessage models
    │   ├── api_views.py         # Session/message endpoints
    │   └── serializers.py       # JSON conversion
    │
    ├── scraper/                 # WEB SCRAPING APP
    │   ├── models.py            # NaverCafeData, AllowedAuthor, BatchJob
    │   ├── tasks.py             # Celery background tasks
    │   ├── api_views.py         # Admin scraper controls
    │   ├── pipeline/            # Scraping and processing pipeline
    │   │   ├── orchestrator.py  # Coordinates pipeline steps
    │   │   ├── base.py          # Abstract base classes
    │   │   ├── scrape/          # Data loading
    │   │   ├── process/         # AI summarization & evaluation
    │   │   └── embed/           # Vector embedding & storage
    │   ├── ingest/              # Batch ingestion logic
    │   └── management/commands/ # CLI commands
    │
    └── common/                  # SHARED UTILITIES
        ├── models.py            # CommonModel (created_at, updated_at)
        └── pagination.py        # API pagination settings
```

## 3.3 The Django Apps

Django organizes code into "apps" - each app handles one domain:

### Users App - Authentication & Profiles

**What it does**: Manages user accounts and Naver OAuth login.

**Key files:**
- `models.py` - Defines the User model with Korean-specific fields (name, nickname, mobile)
- `auth_views.py` - Handles the Naver OAuth login/callback flow
- `api_views.py` - Profile API (get/update/delete your profile)
- `pipeline.py` - Custom logic for creating users from Naver OAuth data

### Content App - Notion Content Management

**What it does**: Stores and serves HTML content exported from Notion.

**Key files:**
- `models.py` - NotionContent (uploaded HTML) and ContentViewHistory (tracking)
- `api_views.py` - List, detail, and text extraction endpoints
- `utils.py` - ZIP extraction, image conversion (HEIC→JPEG), HTML processing

**How it works:**
1. Admin exports a Notion page as HTML (creates a ZIP file)
2. Admin uploads ZIP via Django admin panel
3. Django's `save()` method automatically:
   - Extracts the ZIP safely
   - Hashes long filenames to avoid OS limits
   - Converts HEIC/WebP images to JPEG
   - Rewrites image paths for web access
   - Injects JavaScript for iframe integration

### Chat App - Conversation History

**What it does**: Stores chat sessions and messages (the Agent service sends data here after each conversation).

**Key files:**
- `models.py` - ChatSession (conversation) and ChatMessage (individual message)
- `api_views.py` - List sessions, get messages, delete sessions

**Important**: This app does NOT handle real-time chat. That's the Agent service's job. This app just stores the history.

### Scraper App - Content Ingestion Pipeline

**What it does**: The most complex app. Manages the entire pipeline from Naver Cafe articles to searchable vectors in Pinecone.

Detailed explanation in [Section 3.7](#37-the-scraper-pipeline).

## 3.4 Database Models (How Data Is Stored)

### Entity Relationship Diagram

```
┌────────────────────┐          ┌────────────────────────┐
│       User         │          │    NotionContent        │
├────────────────────┤          ├────────────────────────┤
│ id (PK)            │     ┌───→│ id (PK)                │
│ username           │     │    │ title                   │
│ email              │     │    │ description             │
│ name               │     │    │ zip_file                │
│ nickname           │     │    │ html_path               │
│ profile_image      │     │    │ thumbnail_img_path      │
│ provider           │     │    │ is_preferred             │
│ social_id          │     │    │ created_at / updated_at  │
│ naver_access_token │     │    └────────────────────────┘
│ mobile             │     │
│ information (JSON) │     │    ┌────────────────────────┐
│ created_at         │     │    │  ContentViewHistory     │
│ updated_at         │     │    ├────────────────────────┤
└────────┬───────────┘     │    │ id (PK)                │
         │                 │    │ user_id (FK → User)     │
         │                 └────│ content_id (FK)         │
         │                      │ viewed_at               │
         │                      └────────────────────────┘
         │
         │    ┌────────────────────┐     ┌────────────────────┐
         │    │    ChatSession     │     │    ChatMessage      │
         │    ├────────────────────┤     ├────────────────────┤
         └───→│ id (PK)            │←────│ id (PK)            │
              │ user_id (FK)       │     │ session_id (FK)     │
              │ nonce (UUID)       │     │ role (user/assistant)│
              │ title              │     │ content (text)       │
              │ created_at         │     │ attached_content_ids │
              │ updated_at         │     │ helpful_documents    │
              └────────────────────┘     │ created_at           │
                                         └────────────────────┘

┌────────────────────┐     ┌────────────────────┐
│   NaverCafeData    │     │   AllowedAuthor     │
├────────────────────┤     ├────────────────────┤
│ id (PK)            │     │ id (PK)             │
│ post_id (unique)   │     │ name                │
│ title              │     │ author_group        │
│ content            │     │ is_active           │
│ author             │     └────────────────────┘
│ category           │
│ published_date     │     ┌────────────────────┐
│ summary            │     │     BatchJob        │
│ keywords (list)    │     ├────────────────────┤
│ possible_questions │     │ id (PK)             │
│ ingested (bool)    │     │ job_type            │
│ created_at         │     │ provider            │
│ updated_at         │     │ job_id              │
└────────────────────┘     │ status              │
                           │ post_ids            │
                           │ submitted_at        │
                           │ completed_at        │
                           └────────────────────┘
```

### Understanding Django Models

A Django model is a Python class that maps to a database table:

```python
# This Python class...
class NaverCafeData(CommonModel):
    post_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    content = models.TextField()
    author = models.CharField(max_length=100)
    ingested = models.BooleanField(default=False)

# ...creates this database table:
# CREATE TABLE scraper_navercafedata (
#   id SERIAL PRIMARY KEY,
#   post_id VARCHAR(50) UNIQUE NOT NULL,
#   title VARCHAR(500) NOT NULL,
#   content TEXT NOT NULL,
#   author VARCHAR(100) NOT NULL,
#   ingested BOOLEAN DEFAULT FALSE,
#   created_at TIMESTAMP,
#   updated_at TIMESTAMP
# );
```

You never write SQL. Django handles the translation.

## 3.5 API Endpoints (How Services Talk to Core)

### Public API (Called by the Client)

| Method | Path | What It Does |
|--------|------|-------------|
| GET | `/api/v1/auth/naver/login/` | Start Naver OAuth login |
| GET | `/api/v1/auth/naver/callback/` | Handle OAuth callback |
| GET | `/api/v1/auth/status/` | Check if user is logged in |
| POST | `/api/v1/auth/logout/` | Log out |
| GET | `/api/v1/users/me/` | Get current user's profile |
| PATCH | `/api/v1/users/me/` | Update profile |
| DELETE | `/api/v1/users/me/` | Delete account |
| GET | `/api/v1/content/` | List all content (paginated) |
| GET | `/api/v1/content/{id}/` | Get content detail |
| GET | `/api/v1/content/preferred/` | Get featured content |
| POST | `/api/v1/content/{id}/record-view/` | Track that user viewed content |
| POST | `/api/v1/content/text/` | Get text from selected content |
| GET | `/api/v1/chat/sessions/` | List user's chat sessions |
| POST | `/api/v1/chat/sessions/` | Create new session |
| GET | `/api/v1/chat/{nonce}/messages/` | Get messages for a session |
| DELETE | `/api/v1/chat/{nonce}/` | Delete a chat session |

### Internal API (Called by the Agent service only)

| Method | Path | What It Does |
|--------|------|-------------|
| GET | `/api/v1/scraper/internal/allowed-authors/` | Get list of approved authors |
| GET | `/api/v1/scraper/internal/brands/` | Get brand names for context |
| GET | `/api/v1/scraper/internal/posts/{post_id}/` | Get full post content |
| POST | `/api/v1/content/internal/attachment/` | Get text from content IDs |
| POST | `/api/v1/chat/internal/messages/bulk/` | Save conversation messages |

These "internal" endpoints are meant for service-to-service communication and should be restricted in production.

### Admin API (Called by admin users only)

| Method | Path | What It Does |
|--------|------|-------------|
| POST | `/api/v1/scraper/run/` | Trigger scraping manually |
| POST | `/api/v1/scraper/ingest/` | Trigger ingestion manually |
| GET | `/api/v1/scraper/batch-jobs/` | View batch job status |

## 3.6 Authentication: Naver OAuth Flow

Here's the complete login flow, step by step:

```
STEP 1: User clicks "Login with Naver" on the frontend
  └── Browser navigates to: GET /api/v1/auth/naver/login/

STEP 2: Django (NaverLoginView) builds the Naver authorization URL
  └── Redirect to: https://nid.naver.com/oauth2.0/authorize
        ?client_id=YOUR_NAVER_APP_ID
        &redirect_uri=YOUR_CALLBACK_URL
        &response_type=code
        &state=RANDOM_CSRF_TOKEN

STEP 3: User sees Naver's login page and enters credentials
  └── (This happens on Naver's website, not yours)

STEP 4: Naver redirects back to your callback URL
  └── GET /api/v1/auth/naver/callback/?code=AUTH_CODE&state=CSRF_TOKEN

STEP 5: Django (NaverCallbackView) exchanges the code for an access token
  └── POST https://nid.naver.com/oauth2.0/token
        ?grant_type=authorization_code
        &client_id=YOUR_ID
        &client_secret=YOUR_SECRET
        &code=AUTH_CODE
  └── Response: { "access_token": "AAA...", "refresh_token": "BBB..." }

STEP 6: Django uses the token to get user profile from Naver
  └── GET https://openapi.naver.com/v1/nid/me
        Authorization: Bearer AAA...
  └── Response: { "name": "홍길동", "email": "user@naver.com", "id": "12345" }

STEP 7: Django's social_core pipeline creates/updates the user
  └── pipeline.py → create_user():
        - Checks if user with this social_id exists
        - If new: Creates User with Naver data
        - If existing: Updates profile info
        - Stores access_token (for account disconnection later)

STEP 8: Django creates a session and sets cookies
  └── Response headers:
        Set-Cookie: sessionid=xyz123; HttpOnly; SameSite=Lax
        Set-Cookie: csrftoken=abc456; SameSite=Lax

STEP 9: Browser redirects to home page
  └── Frontend detects cookies, fetches /api/v1/auth/status/
  └── UI shows logged-in state with user avatar/name
```

## 3.7 The Scraper Pipeline

This is the most complex subsystem. Let's understand it piece by piece.

### What Is the Pipeline?

The pipeline transforms raw Naver Cafe posts into searchable knowledge:

```
Raw Post → Summary + Keywords → Vector Embedding → Pinecone Storage
```

### Pipeline Components

```
                    ┌─────────────────────────┐
                    │   PipelineOrchestrator   │
                    │   (Coordinates everything)│
                    └───┬─────────┬─────────┬──┘
                        │         │         │
              ┌─────────▼──┐ ┌───▼─────┐ ┌─▼─────────────┐
              │ NaverCafe   │ │ Content │ │ OpenAI/Pinecone│
              │ Scraper     │ │Evaluator│ │ Embedder       │
              │ (Load data) │ │(AI proc)│ │ (Store vectors)│
              └─────────────┘ └─────────┘ └───────────────┘
```

**Step 1: NaverCafeScraper** - Loads posts from the database

```python
# Not web scraping here - posts are already in the database
# Filters: active authors only, minimum content length, not yet ingested
posts = NaverCafeData.objects.filter(
    author__in=active_authors,
    ingested=False,
    content__length__gte=1000
)
```

**Step 2: ContentEvaluator** - AI processes each post

```python
# Sends post to Gemini LLM with a prompt like:
# "Summarize this article in 100 words.
#  Extract 10 keywords.
#  Generate 5 questions this article answers."
#
# Result:
# {
#   "summary": "This article explains how to start a chicken franchise...",
#   "keywords": ["chicken", "franchise", "startup", "투자", "가맹비"],
#   "possible_questions": [
#     "How much does a chicken franchise cost?",
#     "What are the requirements for opening a restaurant?",
#     ...
#   ]
# }
```

**Step 3: OpenAI Embeddings** - Convert text to vectors

```python
# Takes the summary + keywords + possible_questions
# Sends to OpenAI's text-embedding-3-large model
# Gets back a 1536-dimensional vector
text = f"{post.title}\n{post.summary}\n{' '.join(post.keywords)}"
vector = openai.embeddings.create(input=text, model="text-embedding-3-large")
# vector = [0.023, -0.456, 0.789, ...]  (1536 numbers)
```

**Step 4: PineconeStore** - Store in vector database

```python
# Upsert (insert or update) vector into Pinecone
pinecone_index.upsert(vectors=[{
    "id": str(post.post_id),
    "values": vector,
    "metadata": {
        "title": post.title,
        "author": post.author,
        "source": f"https://cafe.naver.com/.../{post.post_id}",
    }
}])

# Mark post as ingested in database
post.ingested = True
post.save()
```

### Batch API Processing (50% Cheaper)

For large batches, the project uses provider batch APIs instead of real-time processing:

```
Real-time: $1.00 per 1000 posts  (immediate results)
Batch API: $0.50 per 1000 posts  (results in up to 24 hours)
```

**How batch processing works:**

```
Day 1, 4:00 AM (Celery Beat triggers):
  1. submit_batch_jobs_task runs
  2. Collects 500 un-ingested posts
  3. Sends to Gemini Batch API for summarization
  4. Sends to OpenAI Batch API for embedding
  5. Creates BatchJob records with status="submitted"

Day 1, throughout the day (every 30 minutes):
  6. poll_batch_status_task runs
  7. Checks BatchJob records
  8. Calls provider API: "Is my batch done?"
  9. If done: downloads results, updates posts, stores vectors
  10. Updates BatchJob status="completed"
```

## 3.8 Celery: Background Task Processing

### What Is Celery?

Celery is a task queue. When you need to do something slow (scraping, AI processing) without making the user wait, you "send it to Celery":

```
Without Celery:
  User: "Scrape 500 posts" → Wait 30 minutes → "Done!"

With Celery:
  User: "Scrape 500 posts" → "Task started! (takes ~30 min)" → User continues working
  (Celery worker processes 500 posts in the background)
  (When done, results are saved to database)
```

### How Celery Works

```
┌────────────┐     ┌─────────┐     ┌───────────────┐
│ Django App │────►│  Redis   │────►│ Celery Worker │
│ "do this"  │     │ (Queue)  │     │ (processes it)│
└────────────┘     └─────────┘     └───────────────┘
                        ▲
                        │
                   ┌─────────────┐
                   │ Celery Beat │
                   │ (Scheduler) │
                   │ "Run X at   │
                   │  4 AM daily" │
                   └─────────────┘
```

Three Docker containers work together:
- **Core** (Django): Creates tasks ("scrape 500 posts")
- **Redis**: Stores tasks in a queue (FIFO)
- **Celery Worker**: Picks up and processes tasks
- **Celery Beat**: Creates scheduled tasks automatically

### Scheduled Tasks

| Task | Schedule | What It Does |
|------|----------|-------------|
| `submit_batch_jobs_task` | Daily at 4:00 AM | Submit posts to batch APIs |
| `poll_batch_status_task` | Every 30 minutes | Check if batch jobs are done |

### Why a Separate Dockerfile for Celery?

The Celery worker needs **Playwright** (a browser automation tool) to scrape web pages. Playwright requires a full Chromium browser (~400MB). If we put this in the main Django container:

```
Core Dockerfile (without Playwright): ~200MB  ← fast, lean
Core Dockerfile (with Playwright): ~600MB     ← slow, bloated

Solution:
  Core Dockerfile: ~200MB (no Playwright)
  Celery Dockerfile: ~600MB (with Playwright)
```

Only the Celery worker needs the browser, so only the Celery image includes it.

---

# Part 4: The Agent Service (FastAPI + LangGraph)

## 4.1 What Is This Service and Why Does It Exist?

The Agent service is the "AI brain" of the system. It:

1. Receives user messages
2. Decides if it needs to search for documents
3. Searches the vector database if needed
4. Generates AI responses using the found documents
5. Streams responses back to the user in real-time

### Why a Separate Service?

| Concern | Why Separate? |
|---------|--------------|
| Dependencies | LangGraph, LangChain, ML models are heavy (500MB+ of packages) |
| Performance | Async Python (FastAPI) is better for streaming than Django |
| Scaling | Can run 3 Agent instances while keeping 1 Core instance |
| Isolation | LLM API issues don't affect user login or content management |

## 4.2 Project Structure

```
services/agent/src/
│
├── main.py              # FastAPI app entry point + lifecycle management
├── config.py            # Environment variable loading
│
├── api/                 # HTTP ENDPOINTS
│   ├── router.py        # Route registration
│   ├── chat.py          # POST /chat/{nonce}/stream + POST /chat/{nonce}/stop
│   ├── health.py        # GET /health
│   └── dependencies.py  # Dependency injection setup
│
├── graph/               # LANGGRAPH AI WORKFLOW
│   ├── builder.py       # Graph construction (defines nodes and edges)
│   ├── state.py         # AgentState definition (workflow's "memory")
│   ├── nodes.py         # The 7 node functions (the actual AI logic)
│   ├── prompts.py       # System prompts for the LLM (in Korean)
│   ├── memory.py        # Conversation summarization
│   └── checkpointer.py  # PostgreSQL state persistence
│
├── schemas/             # DATA MODELS
│   └── chat.py          # Request/response schemas (Pydantic)
│
└── services/            # EXTERNAL SERVICE CLIENTS
    ├── core_client.py   # HTTP client for Core service API
    ├── vectorstore.py   # Pinecone vector search
    └── redis.py         # Redis for stop flags
```

## 4.3 The LangGraph Workflow (The AI Brain)

### What Is LangGraph?

LangGraph is a framework for building AI workflows as **state machines** (flowcharts). Instead of one function that does everything, you define:

1. **State**: The data that flows through the workflow
2. **Nodes**: Functions that read state, do something, and update state
3. **Edges**: Rules for which node runs next

Think of it like an assembly line in a factory. Each station (node) does one specific task and passes the product (state) to the next station.

### The Workflow Graph

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │
                    ┌────▼─────────┐
                    │ route_query   │  "Does this need document search?"
                    └──┬─────────┬─┘
                       │         │
          "just_respond"│         │"retrieval_required"
                       │         │
               ┌───────▼──┐ ┌───▼──────────────┐
               │ respond_  │ │ generate_queries  │  "Create 2-5 search queries"
               │ simple    │ └───────┬──────────┘
               └─────┬────┘         │
                     │         ┌────▼──────────────────┐
                     │         │ retrieve_in_parallel   │  "Fan out to parallel search"
                     │         └────┬──────────────────┘
                     │              │ (runs 2-5 times in parallel)
                     │         ┌────▼──────────────────┐
                     │         │ retrieve_documents     │  "Search Pinecone for each query"
                     │         └────┬──────────────────┘
                     │              │
                     │         ┌────▼──────────────────┐
                     │         │ documents_handler      │  "Filter to only relevant docs"
                     │         └────┬──────────────────┘
                     │              │
                     │         ┌────▼──────────────────┐
                     │         │ respond_with_docs      │  "Generate answer with citations"
                     │         └────┬──────────────────┘
                     │              │
                    ┌▼──────────────▼┐
                    │      END       │
                    └────────────────┘
```

### Node Details

**Node 1: `route_query`** - The Traffic Cop

Asks the LLM: "Is this a simple greeting or does it need document search?"

```
Input: "Hello!"
→ Router: "just_respond" (no documents needed)

Input: "How much does a Changple franchise cost?"
→ Router: "retrieval_required" (need to search documents)
```

**Node 2: `respond_simple`** - Quick Answers

For simple conversations that don't need documents:

```
Input: "Hello!"
→ LLM: "Hi! I'm Changple's AI assistant. How can I help you today?"
```

**Node 3: `generate_queries`** - Query Expansion

Turns one user question into multiple search queries for better coverage:

```
Input: "How to start a livestock business?"
→ LLM generates:
  1. "livestock business startup"
  2. "cattle farming requirements"
  3. "livestock startup funding"
  4. "animal husbandry business plan"
```

**Node 4: `retrieve_in_parallel`** - Parallel Dispatch

Sends each search query to Pinecone simultaneously (parallel execution):

```
Query 1 ──► Pinecone ──► 4 results ┐
Query 2 ──► Pinecone ──► 4 results ├──► 12-20 total results
Query 3 ──► Pinecone ──► 4 results ┘
```

**Node 5: `retrieve_documents`** - Vector Search

For each query, converts text to a vector and searches Pinecone:

```
"livestock startup funding"
  → OpenAI embedding: [0.23, -0.45, ...]
  → Pinecone search (top 4, filter by approved authors)
  → Returns 4 most similar documents
```

**Node 6: `documents_handler`** - Relevance Filtering

Not all retrieved documents are relevant. This node asks the LLM to filter:

```
12 documents retrieved
→ LLM: "Documents 1, 3, 5, 7 are relevant to the question"
→ 4 documents kept, 8 discarded
→ Fetches full content from Core API for each kept document
```

**Node 7: `respond_with_docs`** - RAG Response Generation

The main event. Uses the filtered documents to generate a cited answer:

```
System prompt: "You are Changple's AI. Use these documents to answer.
                Cite as [1], [2], etc."

Documents:
  [1] "Livestock Startup Guide" - Content about funding...
  [2] "Cattle Farm Requirements" - Content about regulations...

→ LLM generates: "To start a livestock business, you typically need
                   50-100M won in startup capital [1]. The main requirements
                   include a suitable location and proper licensing [2]..."
```

### The AgentState (Workflow Memory)

```python
class AgentState(MessagesState):
    messages: list[BaseMessage]     # Full conversation history
    router: Router                   # "retrieval_required" or "just_respond"
    documents: list[Document]        # Retrieved documents
    retrieve_queries: list[str]      # Generated search queries
    helpful_documents: list[int]     # Which docs are relevant
    answer: str                      # Final response text
    query: str                       # Current user question
    user_attached_content: str       # Content user attached from sidebar
    source_documents: list[dict]     # Citation metadata for frontend
```

Each node reads from this state and writes back to it. LangGraph manages the state transitions automatically.

## 4.4 How Vector Search Works (RAG)

### The Embedding Process

```
"How to start a chicken restaurant"
       │
       ▼ (OpenAI text-embedding-3-large model)
       │
[0.023, -0.456, 0.789, 0.012, -0.345, ..., 0.567]
                    1536 numbers
```

Each number represents a dimension of meaning. Similar texts produce similar numbers. The model has learned these representations from billions of text examples.

### Pinecone Search

```python
# Creating a retriever
vector_store = PineconeVectorStore(
    index_name="changple-index",
    embedding=OpenAIEmbeddings(model="text-embedding-3-large")
)

retriever = vector_store.as_retriever(
    search_kwargs={
        "k": 4,                                    # Return top 4 results
        "filter": {"author": {"$in": ["Changple", "TeamBiz"]}}  # Only approved authors
    }
)

# Searching
results = retriever.invoke("livestock startup funding")
# Returns: [Document(content="...", metadata={"title": "...", "source": "..."}), ...]
```

### Why This Works

The magic is that semantically similar text produces similar vectors:

```
"How to start a chicken restaurant"  → [0.23, -0.45, 0.78, ...]
"Chicken franchise startup guide"    → [0.25, -0.43, 0.76, ...]  ← VERY SIMILAR
"Korean history of Joseon dynasty"   → [-0.82, 0.15, -0.23, ...]  ← VERY DIFFERENT
```

Pinecone uses math (cosine similarity) to find the closest vectors to your query vector.

## 4.5 SSE Streaming: How Responses Stream to the Browser

### The Async Generator Pattern

```python
async def event_generator():
    """
    This function yields SSE events one at a time.
    FastAPI's StreamingResponse keeps calling it until it's done.
    """
    async for event in graph_app.astream_events(input_data, config):
        if event["event"] == "on_chain_start":
            # A new node started processing
            yield format_sse("status", {"message": "Analyzing..."})

        elif event["event"] == "on_chat_model_stream":
            # LLM produced a new text chunk
            chunk = event["data"]["chunk"].content
            yield format_sse("chunk", {"content": chunk})

        elif event["event"] == "on_chain_end":
            # Workflow finished
            yield format_sse("end", {"source_documents": [...], ...})

return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### SSE Format

```
event: status\n
data: {"message":"Searching documents..."}\n
\n
event: chunk\n
data: {"content":"To start"}\n
\n
event: chunk\n
data: {"content":" a business"}\n
\n
event: end\n
data: {"source_documents":[...],"processed_content":"To start a business..."}\n
\n
```

Each event is:
1. `event:` line (the type)
2. `data:` line (the JSON payload)
3. Empty line (separator)

The browser reads these as they arrive, enabling real-time text display.

## 4.6 Memory Management

### The Problem

Long conversations = more tokens sent to the LLM = slower + more expensive:

```
Conversation with 50 messages:
  - Tokens: ~20,000
  - Cost: ~$0.10 per response
  - Speed: 3-5 seconds first token

Conversation with 10 messages:
  - Tokens: ~4,000
  - Cost: ~$0.02 per response
  - Speed: 0.5-1 seconds first token
```

### The Solution: Summarize Old Messages

When a conversation exceeds 20 messages:

```
Before (20+ messages):
  [User: "Q1"] [AI: "A1"] [User: "Q2"] [AI: "A2"] ... [User: "Q20"]

After summarization:
  [System: "Summary of Q1-Q10: The user asked about franchise costs,
            regulations, and startup procedures. Key points discussed were..."]
  [User: "Q11"] [AI: "A11"] ... [User: "Q20"]
```

This keeps the context manageable while preserving important information from earlier in the conversation.

### Context Window

Only the most recent 5 messages (plus any summary) are sent to the LLM:

```python
def get_context_messages(messages):
    if messages[0] is a summary:
        return [summary] + messages[-5:]  # Summary + last 5
    else:
        return messages[-5:]               # Just last 5
```

## 4.7 How Agent Talks to Core

The Agent service has **NO direct database access**. All data goes through Core's REST API:

```
Agent needs post content:
  → HTTP GET http://core:8000/api/v1/scraper/internal/posts/123/
  ← JSON: {"title": "...", "content": "...", "url": "..."}

Agent needs to save messages:
  → HTTP POST http://core:8000/api/v1/chat/internal/messages/bulk/
  ← JSON: {"status": "ok"}
```

### Why No Direct Database Access?

1. **Loose coupling**: Agent doesn't need to know the database schema
2. **Security**: Agent can't accidentally corrupt data
3. **Flexibility**: Core can change its database without affecting Agent
4. **Reusability**: The same API works for any service that needs data

### Caching

To avoid calling Core's API on every request, the CoreClient caches results:

```python
# First call: hits Core API, caches result
brands = await core_client.get_brands()  # HTTP request → 200ms

# Second call (within 5 minutes): returns cached data
brands = await core_client.get_brands()  # From cache → 0ms
```

---

# Part 5: Infrastructure (Docker, Nginx, Databases)

## 5.1 Docker: Why and How

### What Is Docker?

Docker creates **isolated environments** (containers) for each service. Think of it as shipping containers for software:

```
Without Docker:
  "It works on my machine!"
  - Different Python version on server
  - Missing library
  - Wrong database version
  - Conflicting dependencies

With Docker:
  Each service runs in its own container with EXACTLY the right:
  - Operating system
  - Language version
  - Libraries
  - Configuration
```

### How a Dockerfile Works

A Dockerfile is a recipe for building a container image:

```dockerfile
# Start with a base image (Python 3.12 on minimal Linux)
FROM python:3.12-slim

# Install system libraries
RUN apt-get update && apt-get install -y libpq-dev

# Copy dependency file first (for caching)
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy application code
COPY . .

# Define what happens when container starts
ENTRYPOINT ["./entrypoint.sh"]
```

**Layer caching optimization**: Docker caches each step. If you change your code but not your dependencies, Docker reuses the dependency layer and only rebuilds from `COPY . .` onward. This saves minutes of build time.

### Dockerfiles in This Project

| Dockerfile | Service | Size | Includes |
|-----------|---------|------|----------|
| `services/core/Dockerfile` | Django web server | ~200MB | Python, Django, DRF |
| `services/core/Dockerfile.celery` | Celery worker | ~600MB | Python, Django, Playwright, Chromium |
| `services/core/Dockerfile.beat` | Celery scheduler | ~150MB | Python, Django (minimal) |
| `services/agent/Dockerfile` | FastAPI agent | ~250MB | Python, FastAPI, LangGraph |
| `services/client/Dockerfile` | Next.js frontend | ~200MB | Node.js, Next.js (multi-stage) |
| `nginx/Dockerfile` | Reverse proxy | ~30MB | Nginx Alpine |

## 5.2 Docker Compose: Orchestrating All Services

### What Is Docker Compose?

Instead of manually starting 7 containers with the right settings, Docker Compose lets you define everything in one file and run `docker compose up`.

### The Three Compose Files

```
docker-compose.yml          # Base configuration (shared settings)
docker-compose.dev.yml      # Development additions (hot reload, exposed ports)
docker-compose.prod.yml     # Production additions (nginx, restart policies)
```

**Running in development:**
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Running in production:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Service Startup Order

Services have dependencies - PostgreSQL must start before Django:

```
                    postgres ──────────────►  redis
                       │                        │
                       │                        │
                  (healthy?)                (healthy?)
                       │                        │
                       ▼                        ▼
                     core  ◄────────────────────┘
                       │
                  (started?)
                       │
                       ▼
                     agent
                       │
               ┌───────┴───────┐
               ▼               ▼
            celery         celery-beat
```

Docker Compose manages this with `depends_on` and health checks:

```yaml
core:
  depends_on:
    postgres:
      condition: service_healthy    # Wait until pg_isready succeeds
    redis:
      condition: service_healthy    # Wait until redis-cli ping succeeds
```

### Volume Mounts (Development)

In development, your local code is "mounted" into containers:

```yaml
core:
  volumes:
    - ./services/core:/app    # Your local code → inside container
```

This means when you edit a Python file on your machine, the change is immediately visible inside the container. With `--reload` mode, the server automatically restarts.

## 5.3 Nginx: The Traffic Director

### What Is a Reverse Proxy?

A reverse proxy sits between users and your services:

```
Without Nginx:
  User must know:
  - Core is on port 8000
  - Agent is on port 8001
  - Client is on port 3000

With Nginx:
  User only knows: port 80
  Nginx figures out where to send each request
```

### Routing Rules

```
Request URL                        → Destination
──────────────────────────────────────────────────
/api/v1/auth/*                     → Core (Django, port 8000)
/api/v1/users/*                    → Core
/api/v1/content/*                  → Core
/api/v1/scraper/*                  → Core
/api/v1/chat/history/*             → Core (chat history)
/api/v1/chat/internal/*            → Core (service-to-service)
/api/v1/chat/{uuid}/(stream|stop)  → Agent (FastAPI, port 8001) ← SSE!
/api/v1/chat/{uuid}/messages/      → Core (message history)
/api/v1/chat/*                     → Agent (catch-all chat)
/static/*                          → Nginx serves directly (fast!)
/media/*                           → Nginx serves directly (fast!)
/*                                 → Client (Next.js, port 3000)
```

### SSE Configuration

For streaming responses, Nginx must NOT buffer:

```nginx
location ~ ^/api/v1/chat/[0-9a-f-]+/(stream|stop)$ {
    proxy_pass http://agent;
    proxy_buffering off;         # Don't buffer responses
    proxy_cache off;             # Don't cache
    proxy_read_timeout 300;      # Wait up to 5 minutes
    add_header X-Accel-Buffering no;
}
```

Without this, Nginx would collect all the SSE chunks and send them in one batch, defeating the purpose of streaming.

## 5.4 PostgreSQL: The Database

### What It Stores

Two databases are created by `infra/postgres/init.sql`:

**Database 1: `changple`** (Main application data)
- Users and their profiles
- Chat sessions and messages
- Notion content records
- Scraped Naver Cafe posts
- Batch job tracking
- Allowed authors list

**Database 2: `changple_langgraph`** (AI state persistence)
- LangGraph checkpoints (conversation state after each node)
- Used to resume conversations where they left off

### Why Two Databases?

Separation of concerns:
- The main database is managed by Django (migrations, ORM)
- The LangGraph database is managed by LangGraph (its own schema)
- They can be backed up, restored, or scaled independently

### Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- Generate UUIDs
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Fuzzy text search
```

## 5.5 Redis: The Fast Helper

Redis is an in-memory data store (data lives in RAM, not on disk). It's used for three things:

### 1. Celery Task Queue

```
Django: "Process these 500 posts"
  → Redis stores task message in a queue
  → Celery worker picks it up and processes it
```

### 2. Django Session Cache

```
User logs in → Session data stored in Redis
User makes request → Session lookup from Redis (fast, ~1ms)
  vs. PostgreSQL (~10ms)
```

### 3. Agent Stop Flags

```
User clicks "Stop" → Agent sets Redis flag: "stop:abc123" = "1"
LLM streaming loop → Checks Redis flag each iteration
If flag set → Stop generating, clean up
```

Redis is perfect for these use cases because it's extremely fast (in-memory) and supports automatic expiration (TTL).

## 5.6 Development vs Production

| Aspect | Development | Production |
|--------|-------------|-----------|
| Access | `localhost:8000`, `:8001`, `:3000` | `yourdomain.com:80` (nginx) |
| Code changes | Hot reload (volume mounts) | Rebuild image |
| Debug | Enabled (detailed errors) | Disabled (generic errors) |
| Ports | All services exposed | Only nginx exposed |
| Restart | Manual | Automatic (`unless-stopped`) |
| Static files | Django serves them | Nginx serves them |
| CORS | Allow all origins | Restricted to your domain |
| Cookies | Non-secure | Secure, HttpOnly |
| Logging | DEBUG level | WARNING level |

---

# Part 6: Reference

## 6.1 Complete File Map

Every file in the project and its purpose:

### Root Level
| File | Purpose |
|------|---------|
| `CLAUDE.md` | AI assistant instructions (you're reading the consolidated version) |
| `README.md` | Project overview (needs update) |
| `Makefile` | Build automation shortcuts |
| `docker-compose.yml` | Base Docker configuration |
| `docker-compose.dev.yml` | Development Docker overrides |
| `docker-compose.prod.yml` | Production Docker overrides |
| `.env` | Root environment variables (PostgreSQL credentials) |
| `.env.example` | Template for `.env` |

### Client Service (`services/client/`)
| File | Purpose |
|------|---------|
| `package.json` | Dependencies and scripts |
| `next.config.ts` | Next.js settings (rewrites, images, standalone) |
| `tsconfig.json` | TypeScript compiler settings |
| `components.json` | shadcn/ui configuration |
| `postcss.config.mjs` | Tailwind CSS setup |
| `src/app/layout.tsx` | Root HTML structure + providers |
| `src/app/page.tsx` | Home page with welcome screen |
| `src/app/globals.css` | Global styles + Tailwind design tokens |
| `src/app/chat/[[...nonce]]/page.tsx` | Chat page (dynamic nonce) |
| `src/app/content/[id]/page.tsx` | Content detail page |
| `src/app/api/v1/chat/[nonce]/stream/route.ts` | SSE proxy to Agent |
| `src/app/api/v1/chat/[nonce]/stop/route.ts` | Stop generation proxy |
| `src/components/providers.tsx` | React Query provider setup |
| `src/components/chat/chat-container.tsx` | Chat page main logic |
| `src/components/chat/chat-input.tsx` | Message input textarea |
| `src/components/chat/chat-welcome.tsx` | Welcome screen with examples |
| `src/components/chat/chat-history.tsx` | Past sessions sidebar |
| `src/components/chat/message-list.tsx` | Message container with auto-scroll |
| `src/components/chat/message-bubble.tsx` | Individual message with markdown |
| `src/components/chat/streaming-indicator.tsx` | Loading dots animation |
| `src/components/layout/main-layout.tsx` | Header + sidebar + content |
| `src/components/layout/header.tsx` | Top navigation bar |
| `src/components/layout/sidebar.tsx` | Collapsible side panel |
| `src/components/layout/mobile-warning.tsx` | PC-only warning |
| `src/components/content/content-sidebar.tsx` | Content list/detail router |
| `src/components/content/content-list.tsx` | Content card grid |
| `src/components/content/content-card.tsx` | Single content preview |
| `src/components/content/content-detail.tsx` | Content iframe viewer |
| `src/components/content/image-modal.tsx` | Fullscreen image overlay |
| `src/components/profile/profile-modal.tsx` | User profile dialog |
| `src/components/profile/profile-tabs.tsx` | Tab navigation |
| `src/components/profile/tab-*.tsx` | Individual tab content |
| `src/components/ui/*.tsx` | shadcn/ui base components |
| `src/hooks/use-auth.ts` | Auth status + logout |
| `src/hooks/use-chat.ts` | Send message + streaming |
| `src/hooks/use-chat-history.ts` | Session list + delete |
| `src/hooks/use-content.ts` | Content CRUD + pagination |
| `src/lib/api.ts` | Axios client + CSRF handling |
| `src/lib/sse.ts` | SSE streaming client |
| `src/lib/utils.ts` | Tailwind class merge utility |
| `src/stores/ui-store.ts` | Modal/sidebar UI state |
| `src/stores/sidebar-store.ts` | Sidebar width state |
| `src/stores/content-selection-store.ts` | Content selection (persisted) |
| `src/types/index.ts` | TypeScript type definitions |

### Core Service (`services/core/`)
| File | Purpose |
|------|---------|
| `manage.py` | Django CLI entry point |
| `pyproject.toml` | Python dependencies |
| `Dockerfile` | Web server image |
| `Dockerfile.celery` | Worker image (with Playwright) |
| `Dockerfile.beat` | Scheduler image |
| `entrypoint.sh` | Web server startup (migrate + gunicorn) |
| `entrypoint-celery.sh` | Worker startup |
| `entrypoint-beat.sh` | Scheduler startup |
| `src/_changple/settings/base.py` | Shared Django settings |
| `src/_changple/settings/development.py` | Dev settings |
| `src/_changple/settings/production.py` | Prod settings |
| `src/_changple/urls.py` | URL routing |
| `src/_changple/wsgi.py` | WSGI entry point |
| `src/_changple/celery.py` | Celery configuration |
| `src/users/models.py` | User model |
| `src/users/auth_views.py` | Naver OAuth flow |
| `src/users/api_views.py` | Profile endpoints |
| `src/users/serializers.py` | User JSON serialization |
| `src/users/pipeline.py` | OAuth user creation |
| `src/users/middleware.py` | Auth middleware |
| `src/content/models.py` | NotionContent + ViewHistory |
| `src/content/api_views.py` | Content CRUD endpoints |
| `src/content/serializers.py` | Content JSON serialization |
| `src/content/utils.py` | ZIP extraction, image conversion |
| `src/chat/models.py` | ChatSession + ChatMessage |
| `src/chat/api_views.py` | Session/message endpoints |
| `src/chat/serializers.py` | Chat JSON serialization |
| `src/scraper/models.py` | NaverCafeData, AllowedAuthor, BatchJob |
| `src/scraper/tasks.py` | Celery task definitions |
| `src/scraper/api_views.py` | Admin scraper controls |
| `src/scraper/pipeline/orchestrator.py` | Pipeline coordination |
| `src/scraper/pipeline/base.py` | Abstract pipeline classes |
| `src/scraper/pipeline/scrape/naver_cafe.py` | Data loading |
| `src/scraper/pipeline/process/summarize.py` | AI summarization |
| `src/scraper/pipeline/process/evaluate.py` | Content evaluation |
| `src/scraper/pipeline/embed/openai.py` | OpenAI embedding |
| `src/scraper/pipeline/embed/pinecone.py` | Pinecone storage |
| `src/scraper/ingest/ingest.py` | Ingestion orchestration |
| `src/scraper/ingest/batch_embed.py` | Batch embedding |
| `src/scraper/ingest/batch_summarize.py` | Batch summarization |
| `src/scraper/ingest/content_evaluator.py` | Content evaluation |
| `src/common/models.py` | CommonModel base class |
| `src/common/pagination.py` | API pagination config |

### Agent Service (`services/agent/`)
| File | Purpose |
|------|---------|
| `pyproject.toml` | Python dependencies |
| `Dockerfile` | FastAPI server image |
| `entrypoint.sh` | Server startup |
| `src/main.py` | FastAPI app + lifecycle |
| `src/config.py` | Environment settings |
| `src/api/router.py` | Route registration |
| `src/api/chat.py` | Chat streaming + stop endpoints |
| `src/api/health.py` | Health check |
| `src/api/dependencies.py` | Dependency injection |
| `src/graph/builder.py` | LangGraph workflow construction |
| `src/graph/state.py` | AgentState definition |
| `src/graph/nodes.py` | 7 node functions |
| `src/graph/prompts.py` | Korean system prompts |
| `src/graph/memory.py` | Conversation summarization |
| `src/graph/checkpointer.py` | PostgreSQL persistence |
| `src/schemas/chat.py` | Pydantic schemas |
| `src/services/core_client.py` | Core HTTP client |
| `src/services/vectorstore.py` | Pinecone integration |
| `src/services/redis.py` | Redis stop flags |

### Infrastructure
| File | Purpose |
|------|---------|
| `nginx/nginx.conf` | Nginx global settings |
| `nginx/conf.d/upstream.conf` | Service upstream definitions |
| `nginx/conf.d/default.conf` | Routing rules |
| `nginx/Dockerfile` | Nginx image |
| `infra/postgres/init.sql` | Database initialization |

## 6.2 Environment Variables Reference

### Root `.env`
| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `POSTGRES_USER` | Yes | `changple` | Database username |
| `POSTGRES_PASSWORD` | Yes | `secure_password` | Database password |

### Core Service `.env`
| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Yes | `random-50-char-string` | Django security key |
| `DJANGO_DEBUG` | No | `true` | Enable debug mode |
| `ALLOWED_HOSTS` | Yes | `*` or `yourdomain.com` | Allowed request hosts |
| `POSTGRES_HOST` | Yes | `postgres` | Database host |
| `POSTGRES_PORT` | No | `5432` | Database port |
| `POSTGRES_DB` | Yes | `changple` | Database name |
| `REDIS_HOST` | Yes | `redis` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `SOCIAL_AUTH_NAVER_KEY` | Yes | `naver_client_id` | Naver OAuth client ID |
| `SOCIAL_AUTH_NAVER_SECRET` | Yes | `naver_secret` | Naver OAuth secret |
| `SOCIAL_AUTH_NAVER_CALLBACK_URL` | Yes | `http://localhost/api/v1/auth/naver/callback/` | OAuth callback |
| `OPENAI_API_KEY` | Yes | `sk-...` | OpenAI for embeddings |
| `GOOGLE_API_KEY` | Yes | `AIza...` | Gemini for summarization |
| `PINECONE_API_KEY` | Yes | `pcsk_...` | Pinecone vector DB |
| `PINECONE_INDEX_NAME` | Yes | `changple-index` | Pinecone index |

### Agent Service `.env`
| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `CORE_SERVICE_URL` | Yes | `http://core:8000` | Core service URL |
| `LANGGRAPH_DATABASE_URL` | Yes | `postgresql://...` | Checkpoint database |
| `REDIS_URL` | Yes | `redis://redis:6379/1` | Redis for stop flags |
| `OPENAI_API_KEY` | Yes | `sk-...` | OpenAI embeddings |
| `GOOGLE_API_KEY` | Yes | `AIza...` | Gemini LLM |
| `PINECONE_API_KEY` | Yes | `pcsk_...` | Pinecone search |
| `DEFAULT_MODEL` | No | `gemini-2.5-flash` | Default LLM model |
| `EMBEDDING_MODEL` | No | `text-embedding-3-large` | Embedding model |
| `LANGCHAIN_TRACING_V2` | No | `true` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | `lsv2_...` | LangSmith API key |

### Client Service `.env`
| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Core API base URL |
| `CORE_SERVICE_URL` | Yes | `http://core:8000` | Server-side Core URL |
| `AGENT_SERVICE_URL` | Yes | `http://agent:8001` | Server-side Agent URL |

## 6.3 All API Endpoints

### Authentication
| Method | Path | Auth | Service |
|--------|------|------|---------|
| GET | `/api/v1/auth/naver/login/` | No | Core |
| GET | `/api/v1/auth/naver/callback/` | No | Core |
| GET | `/api/v1/auth/status/` | No | Core |
| POST | `/api/v1/auth/logout/` | Yes | Core |

### Users
| Method | Path | Auth | Service |
|--------|------|------|---------|
| GET | `/api/v1/users/me/` | Yes | Core |
| PATCH | `/api/v1/users/me/` | Yes | Core |
| DELETE | `/api/v1/users/me/` | Yes | Core |

### Content
| Method | Path | Auth | Service |
|--------|------|------|---------|
| GET | `/api/v1/content/` | No | Core |
| GET | `/api/v1/content/{id}/` | No | Core |
| GET | `/api/v1/content/preferred/` | No | Core |
| POST | `/api/v1/content/{id}/record-view/` | Yes | Core |
| POST | `/api/v1/content/text/` | Yes | Core |

### Chat
| Method | Path | Auth | Service |
|--------|------|------|---------|
| GET | `/api/v1/chat/sessions/` | Yes | Core |
| POST | `/api/v1/chat/sessions/` | Yes | Core |
| GET | `/api/v1/chat/{nonce}/messages/` | Yes | Core |
| DELETE | `/api/v1/chat/{nonce}/` | Yes | Core |
| POST | `/api/v1/chat/{nonce}/stream` | No* | Agent |
| POST | `/api/v1/chat/{nonce}/stop` | No* | Agent |

*Authentication on Agent endpoints is a known gap (see architecture-refactoring-plan.md).

### Internal (Service-to-Service)
| Method | Path | Auth | Service |
|--------|------|------|---------|
| GET | `/api/v1/scraper/internal/allowed-authors/` | No* | Core |
| GET | `/api/v1/scraper/internal/brands/` | No* | Core |
| GET | `/api/v1/scraper/internal/posts/{id}/` | No* | Core |
| POST | `/api/v1/content/internal/attachment/` | No* | Core |
| POST | `/api/v1/chat/internal/messages/bulk/` | No* | Core |

*Should be restricted to Docker internal network in production.

### Admin
| Method | Path | Auth | Service |
|--------|------|------|---------|
| POST | `/api/v1/scraper/run/` | Admin | Core |
| POST | `/api/v1/scraper/ingest/` | Admin | Core |
| GET | `/api/v1/scraper/batch-jobs/` | Admin | Core |

## 6.4 Common Development Commands

### Docker

```bash
# Start all services (development)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Start specific service
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d core agent

# View logs
docker compose logs -f agent
docker compose logs -f core celery

# Rebuild after dependency changes
docker compose build --no-cache core

# Stop everything
docker compose down

# Stop and remove all data (careful!)
docker compose down -v
```

### Client (Next.js)

```bash
cd services/client
pnpm install          # Install dependencies
pnpm dev              # Start dev server (port 3000)
pnpm build            # Production build
pnpm lint             # Run ESLint
pnpm type-check       # TypeScript type checking
```

### Core (Django)

```bash
cd services/core
uv sync                              # Install dependencies
uv run python manage.py runserver    # Start dev server (port 8000)
uv run python manage.py migrate      # Apply database migrations
uv run python manage.py createsuperuser  # Create admin user
uv run python manage.py shell        # Python shell with Django
```

### Agent (FastAPI)

```bash
cd services/agent
uv sync                                           # Install dependencies
uv run uvicorn src.main:app --reload --port 8001  # Start dev server
```

### Celery

```bash
cd services/core
uv run celery -A src._changple worker -l INFO     # Start worker
uv run celery -A src._changple beat -l INFO        # Start scheduler
```

### Database

```bash
# Access PostgreSQL shell
docker compose exec postgres psql -U changple -d changple

# Reset database completely
docker compose down -v
docker compose up -d postgres
# Then run migrations again
```

## 6.5 Existing Documentation Audit

| File | Status | Notes |
|------|--------|-------|
| `CLAUDE.md` | **Current** | AI coding assistant instructions. Accurate. |
| `README.md` | **Needs Update** | Mentions scraper as separate service (incorrect). |
| `services/client/README.md` | **Stale** | Auto-generated Next.js boilerplate. Not useful. |
| `z_docs/architecture-refactoring-plan.md` | **Proposal** | Marked "not yet implemented" but SSE migration appears done (see git log). |
| `z_docs/guides/content_app_explanation.md` | **Current** | Good explanation of Notion content processing. |
| `z_docs/guides/iframe_content_issue_resolution.md` | **Current** | Documents a resolved bug (URL encoding + CORS). |
| `z_docs/guides/troubleshooting-redirect-loops.md` | **Current** | Documents a resolved bug (trailing slashes). |
| `z_docs/plans/SSL-plan.md` | **Incomplete** | Very brief (16 lines). Needs implementation details. |
| `z_docs/plans/client-service.md` | **Current** | Comprehensive Next.js implementation plan. |
| `z_docs/plans/django-core-migration.md` | **Current** | Comprehensive Django migration plan. |

## 6.6 Glossary

| Term | Definition |
|------|-----------|
| **API** | Application Programming Interface. A way for programs to talk to each other over HTTP. |
| **App Router** | Next.js 13+ routing system where folders in `app/` directory define URL routes. |
| **Async/Await** | Python pattern for non-blocking operations. Lets the server handle other requests while waiting for a database query or API call. |
| **Celery** | Python task queue. Runs slow tasks in the background without blocking user requests. |
| **CORS** | Cross-Origin Resource Sharing. Security policy that controls which websites can make API calls to your server. |
| **CSRF** | Cross-Site Request Forgery. Attack where a malicious site tricks your browser into making requests. Django protects against this with tokens. |
| **DRF** | Django REST Framework. Addon that makes building REST APIs easier in Django. |
| **Docker** | Tool that packages applications into isolated containers with all their dependencies. |
| **Docker Compose** | Tool that orchestrates multiple Docker containers together. |
| **Embedding** | Converting text to a vector (list of numbers) that captures semantic meaning. |
| **FastAPI** | Modern Python web framework optimized for async operations and automatic docs. |
| **Gunicorn** | Production-grade Python web server. Handles multiple requests simultaneously. |
| **Hook (React)** | Function starting with `use` that lets components use state and other React features. |
| **JWT** | JSON Web Token. An auth method (NOT used in this project - we use sessions instead). |
| **LangChain** | Python framework for building LLM applications. Provides abstractions for common AI patterns. |
| **LangGraph** | Extension of LangChain for building stateful, multi-step AI workflows as graphs. |
| **LLM** | Large Language Model. AI model like GPT-4 or Gemini that generates text. |
| **Middleware** | Code that processes every request/response. Like a security guard at the door. |
| **Migration** | Database schema change tracked by Django. Like version control for your database structure. |
| **MSA** | Microservice Architecture. Splitting one big app into smaller, independent services. |
| **Nginx** | High-performance web server used as a reverse proxy (traffic director). |
| **Nonce** | Number used once. A UUID that uniquely identifies each chat session. |
| **OAuth** | Authentication protocol. Lets users log in with existing accounts (Naver, Google, etc.). |
| **ORM** | Object-Relational Mapping. Write Python objects instead of SQL queries. |
| **Pinecone** | Managed vector database service. Stores and searches embeddings. |
| **Pydantic** | Python library for data validation. Ensures data matches expected types/formats. |
| **RAG** | Retrieval-Augmented Generation. Finding relevant documents and using them to generate better AI answers. |
| **React Query** | Library for fetching, caching, and updating server data in React apps. |
| **Redis** | In-memory data store. Ultra-fast for caching, queues, and temporary data. |
| **REST** | Representational State Transfer. Standard pattern for web APIs (GET, POST, PUT, DELETE). |
| **SSE** | Server-Sent Events. HTTP-based one-way streaming from server to client. |
| **Serializer** | DRF component that converts Django models to/from JSON. |
| **Session** | Server-side storage tied to a browser cookie. Stores login state. |
| **shadcn/ui** | Collection of copy-paste React components built on Radix UI + Tailwind. |
| **SPA** | Single Page Application. The browser loads one HTML page and JavaScript handles navigation. |
| **Tailwind CSS** | Utility-first CSS framework. Style with classes like `bg-blue-500 p-4 rounded`. |
| **TypeScript** | JavaScript with type annotations. Catches errors before runtime. |
| **UUID** | Universally Unique Identifier. 128-bit random ID like `a1b2c3d4-e5f6-7890-abcd-ef1234567890`. |
| **Vector** | A list of numbers representing text meaning. Used for similarity search. |
| **Volume (Docker)** | Persistent storage that survives container restarts. |
| **WSGI** | Web Server Gateway Interface. Standard for Python web apps to talk to web servers. |
| **Zustand** | Lightweight React state management library. Simpler alternative to Redux. |
| **uv** | Fast Python package manager (replacement for pip). |

---

> **You've reached the end of the guide!** If something is unclear or you want to dive deeper into any topic, the source code is the best reference. Every file path mentioned in this guide is a real file you can open and read. Start with the files in the section that interests you most.
