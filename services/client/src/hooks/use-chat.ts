'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { streamChat, stopChatGeneration } from '@/lib/sse';
import { useContentSelectionStore } from '@/stores/content-selection-store';
import { useAuth } from './use-auth';
import type { Message, SourceDocument } from '@/types';

interface UseChatOptions {
  initialNonce?: string;
  onSessionCreated?: (nonce: string) => void;
}

export function useChat(options: UseChatOptions = {}) {
  const { initialNonce, onSessionCreated } = options;
  const isMountedRef = useRef(true);
  const abortRef = useRef<AbortController | null>(null);
  // Use a ref for the nonce to avoid stale closures creating duplicate nonces.
  // The state `nonce` drives UI re-renders; the ref is the single source of truth
  // for the actual session nonce used in network requests.
  const nonceRef = useRef<string | null>(initialNonce || null);
  // Ref mirror of isStreaming to avoid stale closure in sendMessage guard.
  // This lets sendMessage have stable deps (no isStreaming), preventing
  // unnecessary effect re-runs in consumers.
  const isStreamingRef = useRef(false);

  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [nonce, setNonce] = useState<string | null>(initialNonce || null);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth();
  const selectedContentIds = useContentSelectionStore((s) => s.selectedIds);

  // Keep streaming ref in sync
  useEffect(() => {
    isStreamingRef.current = isStreaming;
  }, [isStreaming]);

  // Ensure nonce exists (create one if needed).
  // Uses a ref to guarantee only ONE nonce is ever created, regardless of
  // React closure timing. URL is updated via a separate effect to avoid
  // interfering with streaming.
  const ensureNonce = useCallback(() => {
    if (nonceRef.current) return nonceRef.current;
    const newNonce = crypto.randomUUID();
    nonceRef.current = newNonce;
    setNonce(newNonce);
    onSessionCreated?.(newNonce);
    return newNonce;
  }, [onSessionCreated]);

  // Update URL when a new nonce is created (deferred from ensureNonce to avoid
  // interfering with Next.js rendering during streaming)
  useEffect(() => {
    if (nonce && !initialNonce) {
      window.history.replaceState(null, '', `/chat/${nonce}/`);
    }
  }, [nonce, initialNonce]);

  // Track mounted state
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  // Send a message via SSE
  const sendMessage = useCallback(
    async (content: string) => {
      if (isStreamingRef.current || !content.trim()) return;

      const sessionNonce = ensureNonce();

      // Add user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: content.trim(),
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Add placeholder for assistant response
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        isStreaming: true,
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      setIsStreaming(true);
      setError(null);

      // Create abort controller for this request
      const abortController = new AbortController();
      abortRef.current = abortController;

      // Track whether a terminal SSE event (end/stopped/error) was received.
      // The finally block only resets state if none of these fired.
      let streamCompleted = false;

      try {
        await streamChat(
          sessionNonce,
          content.trim(),
          selectedContentIds,
          user?.id || null,
          {
            onStatus: (data) => {
              if (!isMountedRef.current) return;
              setStatusMessage(data.message);
            },
            onChunk: (data) => {
              if (!isMountedRef.current) return;
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.role === 'assistant' && last.isStreaming) {
                  return [
                    ...prev.slice(0, -1),
                    { ...last, content: last.content + data.content },
                  ];
                }
                return prev;
              });
            },
            onEnd: (data) => {
              streamCompleted = true;
              if (!isMountedRef.current) return;
              const sources = data.source_documents as SourceDocument[];
              // Convert [N] citation references to markdown hyperlinks
              let finalContent = data.processed_content;
              if (sources && sources.length > 0) {
                finalContent = finalContent.replace(/\[(\d+)\]/g, (match, numStr) => {
                  const num = parseInt(numStr, 10);
                  if (num >= 1 && num <= sources.length) {
                    return `[\\[${num}\\]](${sources[num - 1].source})`;
                  }
                  return match;
                });
              }
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.role === 'assistant') {
                  return [
                    ...prev.slice(0, -1),
                    {
                      ...last,
                      content: finalContent,
                      sources,
                      isStreaming: false,
                    },
                  ];
                }
                return prev;
              });
              setIsStreaming(false);
              setStatusMessage(null);
            },
            onStopped: () => {
              streamCompleted = true;
              if (!isMountedRef.current) return;
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.role === 'assistant' && last.isStreaming) {
                  return [
                    ...prev.slice(0, -1),
                    { ...last, isStreaming: false, content: last.content + ' (중단됨)' },
                  ];
                }
                return prev;
              });
              setIsStreaming(false);
              setStatusMessage(null);
            },
            onError: (data) => {
              streamCompleted = true;
              if (!isMountedRef.current) return;
              setError(data.message);
              setStatusMessage(null);
              setIsStreaming(false);
              // Remove empty assistant placeholder on error
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.role === 'assistant' && !last.content) {
                  return prev.slice(0, -1);
                }
                return prev;
              });
            },
          },
          abortController.signal
        );
      } catch (err) {
        if (!isMountedRef.current) return;
        if (abortController.signal.aborted) return;

        const errorMessage = err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.';
        setError(errorMessage);
        setIsStreaming(false);
        setStatusMessage(null);
      } finally {
        abortRef.current = null;
        // Safety net: only reset if no terminal SSE event was received.
        // This prevents the finally block from interfering with onEnd/onStopped/onError state.
        if (!streamCompleted && isMountedRef.current) {
          setIsStreaming(false);
          setStatusMessage(null);
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === 'assistant' && last.isStreaming) {
              return [
                ...prev.slice(0, -1),
                { ...last, isStreaming: false },
              ];
            }
            return prev;
          });
        }
      }
    },
    [ensureNonce, selectedContentIds, user?.id]
  );

  // Stop generation - uses ref for correct nonce
  const stopGeneration = useCallback(async () => {
    const currentNonce = nonceRef.current;
    if (!currentNonce) return;

    // Abort the fetch first to stop reading the stream
    abortRef.current?.abort();

    // Mark streaming as stopped immediately for responsive UI
    setIsStreaming(false);
    setStatusMessage(null);
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === 'assistant' && last.isStreaming) {
        return [
          ...prev.slice(0, -1),
          { ...last, isStreaming: false, content: last.content + ' (중단됨)' },
        ];
      }
      return prev;
    });

    // Tell the server to stop (best effort)
    try {
      await stopChatGeneration(currentNonce);
    } catch {
      // Best effort
    }
  }, []);

  // Clear messages (for new chat)
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Load existing messages (for session restoration)
  const loadMessages = useCallback((existingMessages: Message[]) => {
    setMessages(existingMessages);
  }, []);

  return {
    // State
    messages,
    isConnected: true, // SSE is connectionless (per-request)
    isConnecting: false,
    isStreaming,
    statusMessage,
    nonce,
    error,

    // Actions
    sendMessage,
    stopGeneration,
    clearMessages,
    loadMessages,

    // Computed
    canSend: !isStreaming,
    hasMessages: messages.length > 0,
  };
}
