'use client';

import { useEffect, useRef } from 'react';
import { ChatWelcome } from './chat-welcome';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { useChat } from '@/hooks/use-chat';
import { useSessionMessages } from '@/hooks/use-chat-history';
import type { Message } from '@/types';

interface ChatContainerProps {
  initialNonce?: string;
}

export function ChatContainer({ initialNonce }: ChatContainerProps) {
  const {
    messages,
    isConnected,
    isConnecting,
    isStreaming,
    statusMessage,
    error,
    sendMessage,
    stopGeneration,
    loadMessages,
    hasMessages,
  } = useChat({ initialNonce });

  // Load existing messages if we have a session nonce
  const { data: existingMessages } = useSessionMessages(initialNonce || null);

  // Handle pending question from home page navigation.
  // Uses setTimeout(0) to defer sendMessage to the next macrotask, which
  // survives React StrictMode's synchronous unmount/remount cycle in dev mode.
  // Without this, StrictMode's cleanup would abort the stream mid-flight.
  const pendingHandled = useRef(false);
  useEffect(() => {
    if (pendingHandled.current) return;
    const pendingQuestion = sessionStorage.getItem('pendingQuestion');
    if (pendingQuestion) {
      pendingHandled.current = true;
      sessionStorage.removeItem('pendingQuestion');
      setTimeout(() => sendMessage(pendingQuestion), 0);
    }
  }, [sendMessage]);

  // Load existing messages when fetched
  useEffect(() => {
    if (existingMessages && existingMessages.length > 0) {
      const formatted: Message[] = existingMessages.map((msg) => ({
        id: String(msg.id),
        role: msg.role,
        content: msg.content,
        createdAt: new Date(msg.created_at),
      }));
      loadMessages(formatted);
    }
  }, [existingMessages, loadMessages]);

  const handleExampleClick = (question: string) => {
    if (isConnected) {
      sendMessage(question);
    }
  };

  return (
    <div className="flex flex-col h-full w-full overflow-hidden">
      {/* Connection error */}
      {error && (
        <div className="px-4 py-2 bg-red-50 text-red-600 text-sm text-center flex-shrink-0">
          {error}
        </div>
      )}

      {/* Messages or Welcome screen */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {hasMessages ? (
          <MessageList messages={messages} isStreaming={isStreaming} statusMessage={statusMessage} />
        ) : (
          <ChatWelcome onExampleClick={handleExampleClick} />
        )}
      </div>

      {/* Input */}
      <div className="flex-shrink-0 pb-4">
        <ChatInput
          onSend={sendMessage}
          onStop={stopGeneration}
          isStreaming={isStreaming}
          isConnected={isConnected}
          disabled={isConnecting}
        />
      </div>
    </div>
  );
}
