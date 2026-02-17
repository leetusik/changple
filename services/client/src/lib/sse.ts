/**
 * Fetch-based SSE client for chat streaming.
 *
 * Uses POST requests with ReadableStream parsing instead of EventSource
 * (which only supports GET). Supports credentials, AbortController, and
 * typed event handlers.
 *
 * NOTE: URLs use trailing slashes to match Next.js trailingSlash: true
 * config and avoid 308 redirects that break POST streaming.
 */

export interface SSEStatusEvent {
  message: string;
}

export interface SSEChunkEvent {
  content: string;
}

export interface SSEEndEvent {
  source_documents: Array<{
    id: number;
    title: string;
    source: string;
  }>;
  processed_content: string;
}

export interface SSEStoppedEvent {
  message: string;
}

export interface SSEErrorEvent {
  message: string;
  code?: string;
}

export interface StreamChatOptions {
  onStatus?: (data: SSEStatusEvent) => void;
  onChunk?: (data: SSEChunkEvent) => void;
  onEnd?: (data: SSEEndEvent) => void;
  onStopped?: (data: SSEStoppedEvent) => void;
  onError?: (data: SSEErrorEvent) => void;
}

/**
 * Get CSRF token from cookie (Django sets 'csrftoken' cookie)
 */
function getCSRFToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

/**
 * Parse SSE text into individual events.
 * Handles buffering of partial events across chunks.
 */
function parseSSEEvents(
  text: string,
  buffer: string
): { events: Array<{ event: string; data: string; id?: string }>; remaining: string } {
  const combined = buffer + text;
  const events: Array<{ event: string; data: string; id?: string }> = [];

  // Split by double newline (SSE event boundary)
  const parts = combined.split("\n\n");

  // Last part might be incomplete
  const remaining = parts.pop() || "";

  for (const part of parts) {
    if (!part.trim()) continue;

    let event = "";
    let data = "";
    let id: string | undefined;

    for (const line of part.split("\n")) {
      if (line.startsWith("event: ")) {
        event = line.slice(7);
      } else if (line.startsWith("data: ")) {
        data = line.slice(6);
      } else if (line.startsWith("id: ")) {
        id = line.slice(4);
      }
    }

    if (event && data) {
      events.push({ event, data, id });
    }
  }

  return { events, remaining };
}

/**
 * Stream a chat message via SSE POST request.
 *
 * @param nonce - Session nonce (UUID)
 * @param content - Message content
 * @param contentIds - Optional attached content IDs
 * @param userId - Optional user ID
 * @param options - Event handlers
 * @param signal - AbortController signal for cancellation
 */
export async function streamChat(
  nonce: string,
  content: string,
  contentIds: number[] = [],
  userId: number | null = null,
  options: StreamChatOptions = {},
  signal?: AbortSignal
): Promise<void> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
  // Trailing slash to avoid 308 redirect from trailingSlash: true
  const url = `${baseUrl}/chat/${nonce}/stream/`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const csrfToken = getCSRFToken();
  if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    credentials: "include",
    signal,
    body: JSON.stringify({
      content,
      content_ids: contentIds,
      user_id: userId,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage: string;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorJson.message || errorText;
    } catch {
      errorMessage = errorText;
    }
    options.onError?.({ message: errorMessage, code: String(response.status) });
    return;
  }

  if (!response.body) {
    options.onError?.({ message: "No response body" });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value, { stream: true });
      const { events, remaining } = parseSSEEvents(text, buffer);
      buffer = remaining;

      for (const { event, data } of events) {
        try {
          switch (event) {
            case "status":
              options.onStatus?.(JSON.parse(data));
              break;
            case "chunk":
              options.onChunk?.(JSON.parse(data));
              break;
            case "end":
              options.onEnd?.(JSON.parse(data));
              break;
            case "stopped":
              options.onStopped?.(JSON.parse(data));
              break;
            case "error":
              options.onError?.(JSON.parse(data));
              break;
            case "heartbeat":
              // Ignore heartbeats
              break;
          }
        } catch (parseError) {
          console.error("[SSE] Failed to parse event data:", event, data, parseError);
        }
      }
    }
  } catch (err) {
    if (signal?.aborted) {
      // AbortController triggered - not an error
      return;
    }
    throw err;
  }
}

/**
 * Send a stop generation request.
 */
export async function stopChatGeneration(nonce: string): Promise<void> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
  // Trailing slash to avoid 308 redirect
  const url = `${baseUrl}/chat/${nonce}/stop/`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const csrfToken = getCSRFToken();
  if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
  }

  await fetch(url, {
    method: "POST",
    headers,
    credentials: "include",
  });
}
