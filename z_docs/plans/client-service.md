# Plan: Client Service Development (Next.js Frontend)

## Objective
Build the changple4 Client service as a Next.js SPA that preserves the exact visual design and UX from changple2 while modernizing to React.

---

## Critical Design Decision: Chat UI Approach

### Original Plan Issue
The original plan proposed using `@assistant-ui/react` with a custom runtime adapter. **This is overly complex** for our use case.

**Why assistant-ui doesn't fit well:**
1. assistant-ui is designed for SSE-based Data Stream Protocol, not custom WebSocket
2. Creating a custom `AssistantRuntime` adapter requires translating between protocols
3. The overhead isn't worth it given our well-defined WebSocket protocol
4. assistant-ui's abstractions add complexity without proportional benefit

### Revised Approach: shadcn/ui + Custom WebSocket

**Use shadcn/ui AI components + custom WebSocket client:**
- Use shadcn/ui chat components (already designed for AI chat)
- Implement direct WebSocket connection with our exact protocol
- Zustand for UI state (sidebar, streaming status)
- TanStack Query for server state (content, history)
- Full control, simpler debugging, less abstraction

**Benefits:**
- Exact visual match to changple2 (full CSS control)
- No protocol translation layer
- Easier to debug and maintain
- shadcn/ui components are copy-paste customizable

---

## Tech Stack (Revised)

| Layer | Technology | Purpose |
|-------|------------|---------|
| Framework | Next.js 15 (App Router) | SSR, routing, API routes |
| Language | TypeScript | Type safety |
| UI Components | shadcn/ui | Accessible, customizable components |
| Styling | TailwindCSS | Utility-first CSS with design tokens |
| Server State | TanStack Query | Content, history, auth caching |
| UI State | Zustand | Sidebar state, streaming status |
| WebSocket | Native API + custom hooks | Real-time chat |
| Markdown | react-markdown + rehype | Safe rendering |
| Package Manager | pnpm | Fast, disk-efficient |

---

## Verified Core Service APIs

All required APIs **already exist** in Core service:

### Authentication (`/api/v1/auth/`)
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/naver/login/` | GET | Public | Redirect to Naver OAuth |
| `/naver/callback/` | GET | Public | Handle OAuth callback, set session |
| `/status/` | GET | Public | Check auth status, return user if logged in |
| `/logout/` | POST | Auth | Clear session |

### Users (`/api/v1/users/`)
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/me/` | GET | Auth | Get current user profile |
| `/profile/` | PATCH | Auth | Update profile |

### Content (`/api/v1/content/`)
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/columns/` | GET | Public | List all content (paginated) |
| `/preferred/` | GET | Public | Featured content |
| `/<id>/` | GET | Public | Content detail |
| `/attachment/` | POST | Auth | Get text for content IDs |

### Chat History (`/api/v1/chat/`)
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/history/` | GET | Auth | List chat sessions |
| `/<nonce>/messages/` | GET | Auth | Get session messages |
| `/<nonce>/` | DELETE | Auth | Delete session |

### Key Integration Notes
1. **Session-based auth** - No JWT, uses Django session cookies
2. **CSRF tokens required** - For POST/PATCH/DELETE requests
3. **Pagination** - 20 items per page default

---

## WebSocket Protocol (Agent Service)

**Endpoint:** `ws://{host}/ws/chat/{nonce}`

### Client → Agent
```typescript
// Send message
{ type: "message", content: string, content_ids: number[], user_id: number | null }

// Stop generation
{ type: "stop_generation" }
```

### Agent → Client
```typescript
// Session created (first message after connect)
{ type: "session_created", nonce: string }

// Processing status updates
{ type: "status_update", message: string }

// Streaming chunks
{ type: "stream_chunk", content: string }

// Stream complete
{ type: "stream_end", source_documents: SourceDoc[], processed_content: string }

// Generation stopped by user
{ type: "generation_stopped" }

// Error
{ type: "error", message: string, code?: string }
```

---

## Directory Structure (Revised)

```
services/client/
├── public/
│   ├── fonts/
│   │   └── SpoqaHanSansNeo/     # Korean font (free for web)
│   └── icons/                    # SVG icons from changple2
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout + providers
│   │   ├── page.tsx             # Home (welcome screen)
│   │   ├── chat/
│   │   │   └── [[...nonce]]/    # Optional catch-all for /chat and /chat/{nonce}
│   │   │       └── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── layout/
│   │   │   ├── header.tsx
│   │   │   ├── sidebar.tsx
│   │   │   └── main-layout.tsx
│   │   ├── chat/
│   │   │   ├── chat-welcome.tsx
│   │   │   ├── chat-container.tsx    # Main chat orchestrator
│   │   │   ├── message-list.tsx      # Scrollable message area
│   │   │   ├── message-bubble.tsx    # User/assistant bubble
│   │   │   ├── chat-input.tsx        # Input + source counter
│   │   │   ├── source-panel.tsx      # Source documents display
│   │   │   └── streaming-indicator.tsx
│   │   ├── content/
│   │   │   ├── content-list.tsx
│   │   │   └── content-card.tsx
│   │   └── ui/                       # shadcn/ui components
│   ├── lib/
│   │   ├── api.ts                    # Axios instance with CSRF
│   │   ├── websocket.ts              # WebSocket client class
│   │   └── utils.ts                  # cn() helper
│   ├── hooks/
│   │   ├── use-auth.ts               # Auth query hook
│   │   ├── use-content.ts            # Content query hooks
│   │   ├── use-chat-history.ts       # Chat history query
│   │   └── use-chat.ts               # WebSocket chat hook (main)
│   ├── stores/
│   │   ├── sidebar-store.ts          # Sidebar collapse state
│   │   └── content-selection-store.ts # Selected content IDs
│   └── types/
│       └── index.ts                  # All TypeScript types
├── Dockerfile
├── next.config.ts
├── tailwind.config.ts
├── components.json                   # shadcn/ui config
└── package.json
```

---

## Key Implementation Details

### 1. CSRF Token Handling (Critical)

Django requires CSRF tokens for state-mutating requests.

```typescript
// src/lib/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  withCredentials: true, // Send session cookies
});

// Get CSRF token from cookie (Django sets 'csrftoken' cookie)
function getCSRFToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

// Add CSRF token to all non-GET requests
api.interceptors.request.use((config) => {
  if (config.method !== 'get') {
    const token = getCSRFToken();
    if (token) {
      config.headers['X-CSRFToken'] = token;
    }
  }
  return config;
});

export default api;
```

### 2. WebSocket Client with Reconnection

```typescript
// src/lib/websocket.ts
type MessageHandler = (data: any) => void;

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(private nonce?: string) {}

  connect(): Promise<string> {
    return new Promise((resolve, reject) => {
      const url = this.nonce
        ? `${process.env.NEXT_PUBLIC_WS_URL}/ws/chat/${this.nonce}`
        : `${process.env.NEXT_PUBLIC_WS_URL}/ws/chat/${crypto.randomUUID()}`;

      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // First message is session_created with nonce
        if (data.type === 'session_created') {
          this.nonce = data.nonce;
          resolve(data.nonce);
        }

        // Emit to handlers
        const handlers = this.handlers.get(data.type) || [];
        handlers.forEach(h => h(data));
      };

      this.ws.onerror = (error) => reject(error);

      this.ws.onclose = () => {
        this.attemptReconnect();
      };
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
    }
  }

  on(type: string, handler: MessageHandler) {
    const handlers = this.handlers.get(type) || [];
    handlers.push(handler);
    this.handlers.set(type, handlers);
  }

  send(message: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  disconnect() {
    this.maxReconnectAttempts = 0; // Prevent reconnection
    this.ws?.close();
  }
}
```

### 3. useChat Hook (Core Chat Logic)

```typescript
// src/hooks/use-chat.ts
import { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ChatWebSocket } from '@/lib/websocket';
import { useContentSelectionStore } from '@/stores/content-selection-store';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: SourceDocument[];
  isStreaming?: boolean;
}

export function useChat(initialNonce?: string) {
  const router = useRouter();
  const wsRef = useRef<ChatWebSocket | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [nonce, setNonce] = useState<string | null>(initialNonce || null);

  const selectedContentIds = useContentSelectionStore(s => s.selectedIds);

  // Initialize WebSocket connection
  useEffect(() => {
    const ws = new ChatWebSocket(initialNonce);
    wsRef.current = ws;

    ws.on('session_created', ({ nonce }) => {
      setNonce(nonce);
      setIsConnected(true);
      // Update URL without full navigation
      router.replace(`/chat/${nonce}`, { scroll: false });
    });

    ws.on('status_update', ({ message }) => {
      setStatusMessage(message);
    });

    ws.on('stream_chunk', ({ content }) => {
      setMessages(prev => {
        const last = prev[prev.length - 1];
        if (last?.role === 'assistant' && last.isStreaming) {
          return [...prev.slice(0, -1), { ...last, content: last.content + content }];
        }
        return prev;
      });
    });

    ws.on('stream_end', ({ processed_content, source_documents }) => {
      setMessages(prev => {
        const last = prev[prev.length - 1];
        if (last?.role === 'assistant') {
          return [...prev.slice(0, -1), {
            ...last,
            content: processed_content,
            sources: source_documents,
            isStreaming: false
          }];
        }
        return prev;
      });
      setIsStreaming(false);
      setStatusMessage(null);
    });

    ws.on('generation_stopped', () => {
      setIsStreaming(false);
      setStatusMessage(null);
    });

    ws.on('error', ({ message }) => {
      setStatusMessage(`오류: ${message}`);
      setIsStreaming(false);
    });

    ws.connect();

    return () => ws.disconnect();
  }, [initialNonce, router]);

  const sendMessage = useCallback((content: string, userId?: number) => {
    if (!wsRef.current || isStreaming) return;

    // Add user message
    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: 'user',
      content
    }]);

    // Add placeholder for assistant response
    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      isStreaming: true
    }]);

    setIsStreaming(true);

    wsRef.current.send({
      type: 'message',
      content,
      content_ids: selectedContentIds,
      user_id: userId || null
    });
  }, [isStreaming, selectedContentIds]);

  const stopGeneration = useCallback(() => {
    wsRef.current?.send({ type: 'stop_generation' });
  }, []);

  return {
    messages,
    isConnected,
    isStreaming,
    statusMessage,
    nonce,
    sendMessage,
    stopGeneration
  };
}
```

### 4. Tailwind Design Tokens

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        // Changple design tokens (exact from root.css)
        key: {
          1: '#EAECF7',
          2: '#F1F3FF',
        },
        blue: {
          1: '#9CA7B9',
          2: '#7C99CD',
          3: '#5C89B1',
          4: '#2E6FA9',
        },
        grey: {
          0: '#F9F9F9',
          1: '#F6F6F6',
          2: '#DEDEDE',
          3: '#A6A6A6',
          4: '#8D8D8D',
          5: '#666666',
          6: '#4D4D4D',
        },
        black: '#323232',
        'btn-hover': '#EDEDED',
      },
      borderRadius: {
        md: '12px',
        sm: '8px',
        pill: '100px',
      },
      fontFamily: {
        sans: ['Spoqa Han Sans Neo', 'system-ui', 'sans-serif'],
      },
      transitionDuration: {
        '600': '600ms',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
```

---

## Implementation Phases (Revised)

### Phase 1: Project Setup (1 day)

**Commands:**
```bash
cd /Users/sugang/projects/personal/changple4/services/client

# Initialize Next.js
pnpm create next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*" --turbopack

# Core dependencies
pnpm add zustand @tanstack/react-query axios

# UI dependencies
pnpm add class-variance-authority clsx tailwind-merge lucide-react

# Markdown (safer than marked)
pnpm add react-markdown rehype-sanitize remark-gfm

# shadcn/ui init
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add button input textarea scroll-area avatar

# Types
pnpm add -D @types/node
```

**Files to create:**
1. `tailwind.config.ts` - Changple design tokens
2. `src/app/globals.css` - Font imports, base styles
3. `src/lib/api.ts` - Axios with CSRF handling
4. `src/lib/utils.ts` - cn() helper
5. `src/types/index.ts` - TypeScript interfaces
6. Copy `SpoqaHanSansNeo/` fonts to `public/fonts/`

**Verify:** `pnpm dev` runs, `bg-key-1` renders as `#EAECF7`

---

### Phase 2: Layout & Navigation (2 days)

**Files:**
1. `src/components/layout/main-layout.tsx` - Three-panel container
2. `src/components/layout/header.tsx` - Logo + auth status
3. `src/components/layout/sidebar.tsx` - Collapsible content browser
4. `src/stores/sidebar-store.ts` - Collapse state (Zustand)
5. `src/app/layout.tsx` - Providers (QueryClient, etc.)

**Key implementation:**
- Sidebar widths: 100px (collapsed) → 600px (normal) → 1000px (expanded)
- Transition: `transition-all duration-600 ease-in-out`
- Mobile detection: Show warning overlay on `max-width: 768px`

**Verify:** Layout matches changple2, sidebar animations work

---

### Phase 3: Authentication (1 day)

**Files:**
1. `src/hooks/use-auth.ts` - Auth status query
2. Update `header.tsx` - Login button / user profile
3. `src/lib/api.ts` - CSRF token handling

**Auth flow:**
1. Check `/api/v1/auth/status/` on mount
2. If not authenticated, show "로그인" button
3. Button redirects to `/api/v1/auth/naver/login/`
4. After OAuth, Django redirects back with session cookie
5. Re-check status, update UI

**Verify:** Can login via Naver, session persists across refresh

---

### Phase 4: Content Browser (2 days)

**Files:**
1. `src/hooks/use-content.ts` - Preferred/recent content queries
2. `src/components/content/content-list.tsx` - Section with cards
3. `src/components/content/content-card.tsx` - Card + checkbox
4. `src/stores/content-selection-store.ts` - Selected IDs (Zustand + sessionStorage)

**Verify:** Content loads, checkboxes persist in sessionStorage, source counter updates

---

### Phase 5: Chat UI (Static) (2 days)

**Files:**
1. `src/components/chat/chat-welcome.tsx` - Welcome screen
2. `src/components/chat/message-bubble.tsx` - User/assistant bubbles
3. `src/components/chat/message-list.tsx` - Scrollable container
4. `src/app/chat/[[...nonce]]/page.tsx` - Chat page
5. `src/hooks/use-chat-history.ts` - Load existing messages

**Verify:** Welcome screen displays, can view chat history via API

---

### Phase 6: WebSocket Chat (3 days) — CRITICAL

**Files:**
1. `src/lib/websocket.ts` - WebSocket client class
2. `src/hooks/use-chat.ts` - Main chat hook
3. `src/components/chat/chat-container.tsx` - Orchestrates chat
4. `src/components/chat/chat-input.tsx` - Input + send/stop buttons
5. `src/components/chat/streaming-indicator.tsx` - Status + loading dots

**Verify:** Full chat flow works end-to-end

---

### Phase 7: Source Documents (1 day)

**Files:**
1. `src/components/chat/source-panel.tsx` - Expandable source list
2. Update `message-bubble.tsx` - Add source toggle

**Verify:** Sources display correctly, links work

---

### Phase 8: Polish (2 days)

**Tasks:**
1. Error boundaries
2. Loading states
3. Empty states
4. Keyboard shortcuts
5. Accessibility
6. Transitions
7. Mobile warning

---

### Phase 9: Docker & Production (1 day)

**Verify:** `make prod` runs all services, client accessible via nginx

---

## Verification Checklist

### Layout & Auth
- [ ] Three-panel layout matches changple2
- [ ] Sidebar collapses smoothly (100px ↔ 600px ↔ 1000px)
- [ ] Header shows login button when unauthenticated
- [ ] Naver OAuth flow works (login → callback → session)
- [ ] User profile displays after login
- [ ] Logout clears session

### Content Browser
- [ ] Preferred content loads from API
- [ ] Recent content loads from API
- [ ] Checkbox selection works
- [ ] Selection persists across page refresh (sessionStorage)
- [ ] Source counter updates: "소스 N개"

### Chat
- [ ] Welcome screen displays with example questions
- [ ] WebSocket connects on chat page visit
- [ ] URL updates to `/chat/{nonce}` after session creation
- [ ] Sending message adds user bubble
- [ ] Streaming chunks appear incrementally
- [ ] `stream_end` finalizes message with full content
- [ ] Source documents display in expandable panel
- [ ] Stop generation button works
- [ ] Chat history loads for existing sessions
- [ ] Enter sends, Shift+Enter adds newline
- [ ] Input locked when not authenticated

### Production
- [ ] Docker build succeeds
- [ ] Nginx routes `/` to client
- [ ] API calls work through nginx proxy
- [ ] WebSocket connects through nginx

---

## Files to Reference

**From changple2 (for visual matching):**
- `/Users/sugang/projects/personal/changple2/static/css/root.css` - Design tokens
- `/Users/sugang/projects/personal/changple2/static/css/chat.css` - Chat styles
- `/Users/sugang/projects/personal/changple2/static/css/base.css` - Layout
- `/Users/sugang/projects/personal/changple2/templates/chatbot/index_chat.html` - Chat HTML

**From changple4 (for integration):**
- `/Users/sugang/projects/personal/changple4/services/agent/src/schemas/chat.py` - WS types
- `/Users/sugang/projects/personal/changple4/services/agent/src/api/websocket.py` - WS protocol
- `/Users/sugang/projects/personal/changple4/services/core/src/chat/urls.py` - Chat APIs
- `/Users/sugang/projects/personal/changple4/services/core/src/content/urls.py` - Content APIs

---

## Summary of Key Improvements

| Issue | Original Plan | Improved Plan |
|-------|--------------|---------------|
| Chat UI | Complex assistant-ui adapter | Simple shadcn/ui + custom WebSocket |
| Auth | Assumed JWT | Correct: Session-based + CSRF tokens |
| API endpoints | Wrong paths | Verified actual endpoints |
| State mgmt | Overkill | TanStack Query (server) + Zustand (UI) |
| WebSocket | Basic | Reconnection with exponential backoff |
| Types | Scattered | Centralized in `/types/index.ts` |

**Total estimated time:** ~12-15 days (vs 15-19 days original)
