import type { ClientMessage, AgentMessage, AgentMessageType } from "@/types";

type MessageHandler = (data: AgentMessage) => void;

/**
 * WebSocket client for chat communication with Agent service
 */
export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Map<AgentMessageType, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isIntentionalClose = false;
  private connectPromiseReject: ((reason?: unknown) => void) | null = null;

  constructor(private nonce?: string) {}

  /**
   * Connect to the WebSocket server
   * Returns a promise that resolves with the session nonce
   */
  connect(): Promise<string> {
    // If already intentionally closed, don't attempt to connect
    if (this.isIntentionalClose) {
      return Promise.reject(new Error("WebSocket was intentionally closed"));
    }

    return new Promise((resolve, reject) => {
      // Store reject so we can call it from disconnect()
      this.connectPromiseReject = reject;

      const wsBaseUrl =
        process.env.NEXT_PUBLIC_WS_URL ||
        (typeof window !== "undefined"
          ? `ws://${window.location.host}`
          : "ws://localhost");

      // Generate a new UUID if no nonce provided
      const sessionNonce = this.nonce || crypto.randomUUID();
      const url = `${wsBaseUrl}/ws/chat/${sessionNonce}`;

      console.log("[WebSocket] Connecting to:", url);
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log("[WebSocket] Connected");
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as AgentMessage;
          console.log("[WebSocket] Received:", data.type);

          // First message should be session_created with nonce
          if (data.type === "session_created") {
            this.nonce = data.nonce;
            this.connectPromiseReject = null; // Clear since we're resolving
            resolve(data.nonce);
          }

          // Emit to registered handlers
          const handlers = this.handlers.get(data.type) || [];
          handlers.forEach((handler) => handler(data));
        } catch (error) {
          console.error("[WebSocket] Failed to parse message:", error);
        }
      };

      this.ws.onerror = (error) => {
        // Don't log error if this was an intentional close (e.g., React StrictMode cleanup)
        if (!this.isIntentionalClose) {
          console.error("[WebSocket] Error:", error);
        }
        reject(error);
      };

      this.ws.onclose = (event) => {
        console.log("[WebSocket] Closed:", event.code, event.reason);
        // Reject pending connect promise if connection closed before session_created
        if (this.connectPromiseReject) {
          this.connectPromiseReject(
            new Error("Connection closed before session created")
          );
          this.connectPromiseReject = null;
        }
        if (!this.isIntentionalClose) {
          this.attemptReconnect();
        }
      };
    });
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log("[WebSocket] Max reconnection attempts reached");
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;
    console.log(
      `[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`
    );

    setTimeout(() => {
      this.connect().catch((error) => {
        console.error("[WebSocket] Reconnection failed:", error);
      });
    }, delay);
  }

  /**
   * Register a handler for a specific message type
   */
  on<T extends AgentMessageType>(
    type: T,
    handler: (data: Extract<AgentMessage, { type: T }>) => void
  ): void {
    const handlers = this.handlers.get(type) || [];
    handlers.push(handler as MessageHandler);
    this.handlers.set(type, handlers);
  }

  /**
   * Remove a handler for a specific message type
   */
  off<T extends AgentMessageType>(
    type: T,
    handler: (data: Extract<AgentMessage, { type: T }>) => void
  ): void {
    const handlers = this.handlers.get(type) || [];
    const index = handlers.indexOf(handler as MessageHandler);
    if (index > -1) {
      handlers.splice(index, 1);
      this.handlers.set(type, handlers);
    }
  }

  /**
   * Send a message to the server
   */
  send(message: ClientMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      console.log("[WebSocket] Sent:", message.type);
    } else {
      console.warn("[WebSocket] Cannot send - not connected");
    }
  }

  /**
   * Send a chat message
   */
  sendMessage(
    content: string,
    contentIds: number[] = [],
    userId?: number | null
  ): void {
    this.send({
      type: "message",
      content,
      content_ids: contentIds,
      user_id: userId,
    });
  }

  /**
   * Request to stop the current generation
   */
  stopGeneration(): void {
    this.send({ type: "stop_generation" });
  }

  /**
   * Disconnect from the server
   */
  disconnect(): void {
    this.isIntentionalClose = true;
    this.maxReconnectAttempts = 0; // Prevent reconnection

    this.ws?.close();
    this.ws = null;
  }

  /**
   * Check if connected
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get current session nonce
   */
  get sessionNonce(): string | undefined {
    return this.nonce;
  }
}
