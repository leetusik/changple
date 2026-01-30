'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ChatWebSocket } from '@/lib/websocket';
import { useContentSelectionStore } from '@/stores/content-selection-store';
import { useAuth } from './use-auth';
import type { Message, SourceDocument } from '@/types';

interface UseChatOptions {
  initialNonce?: string;
  onSessionCreated?: (nonce: string) => void;
}

export function useChat(options: UseChatOptions = {}) {
  const { initialNonce, onSessionCreated } = options;
  const router = useRouter();
  const wsRef = useRef<ChatWebSocket | null>(null);
  const isMountedRef = useRef(true);

  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [nonce, setNonce] = useState<string | null>(initialNonce || null);
  const [error, setError] = useState<string | null>(null);

  const { user } = useAuth();
  const selectedContentIds = useContentSelectionStore((s) => s.selectedIds);

  // Initialize WebSocket connection
  const connect = useCallback(() => {
    // Only check wsRef (not isConnecting) to handle React StrictMode double-mount
    // wsRef is properly cleared in cleanup, isConnecting state persists
    if (wsRef.current || !isMountedRef.current) return;

    setIsConnecting(true);
    setError(null);

    const ws = new ChatWebSocket(initialNonce);
    wsRef.current = ws;

    // Handle session creation
    ws.on('session_created', ({ nonce: newNonce }) => {
      if (!isMountedRef.current) return;
      setNonce(newNonce);
      setIsConnected(true);
      setIsConnecting(false);
      onSessionCreated?.(newNonce);
      // Update URL without full navigation
      router.replace(`/chat/${newNonce}`, { scroll: false });
    });

    // Handle status updates (e.g., "검색 중...", "답변 생성 중...")
    ws.on('status_update', ({ message }) => {
      setStatusMessage(message);
    });

    // Handle streaming chunks
    ws.on('stream_chunk', ({ content }) => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === 'assistant' && last.isStreaming) {
          return [
            ...prev.slice(0, -1),
            { ...last, content: last.content + content },
          ];
        }
        return prev;
      });
    });

    // Handle stream end
    ws.on('stream_end', ({ processed_content, source_documents }) => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === 'assistant') {
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              content: processed_content,
              sources: source_documents,
              isStreaming: false,
            },
          ];
        }
        return prev;
      });
      setIsStreaming(false);
      setStatusMessage(null);
    });

    // Handle generation stopped
    ws.on('generation_stopped', () => {
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
    });

    // Handle errors
    ws.on('error', ({ message }) => {
      setError(message);
      setStatusMessage(`오류: ${message}`);
      setIsStreaming(false);
    });

    // Start connection
    ws.connect().catch((err) => {
      if (!isMountedRef.current) return;
      console.warn('[useChat] Connection failed:', err.message);
      setError('WebSocket 연결에 실패했습니다.');
      setIsConnecting(false);
    });
  }, [initialNonce, onSessionCreated, router]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  // Track mounted state and clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      wsRef.current?.disconnect();
      wsRef.current = null;
    };
  }, []);

  // Send a message
  const sendMessage = useCallback(
    (content: string) => {
      if (!wsRef.current || isStreaming || !content.trim()) return;

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

      // Send to WebSocket
      wsRef.current.send({
        type: 'message',
        content: content.trim(),
        content_ids: selectedContentIds,
        user_id: user?.id || null,
      });
    },
    [isStreaming, selectedContentIds, user?.id]
  );

  // Stop generation
  const stopGeneration = useCallback(() => {
    wsRef.current?.send({ type: 'stop_generation' });
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
    isConnected,
    isConnecting,
    isStreaming,
    statusMessage,
    nonce,
    error,

    // Actions
    connect,
    disconnect,
    sendMessage,
    stopGeneration,
    clearMessages,
    loadMessages,

    // Computed
    canSend: isConnected && !isStreaming,
    hasMessages: messages.length > 0,
  };
}
