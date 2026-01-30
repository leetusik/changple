'use client';

import { useEffect } from 'react';
import { ChatWelcome } from './chat-welcome';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { StreamingIndicator } from './streaming-indicator';
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
    connect,
    sendMessage,
    stopGeneration,
    loadMessages,
    hasMessages,
  } = useChat({ initialNonce });

  // Load existing messages if we have a session nonce
  const { data: existingMessages } = useSessionMessages(initialNonce || null);

  // Connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

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
    <div className="flex flex-col h-full w-full">
      {/* Connection error */}
      {error && (
        <div className="px-4 py-2 bg-red-50 text-red-600 text-sm text-center">
          {error}
        </div>
      )}

      {/* Messages or Welcome screen */}
      {hasMessages ? (
        <MessageList messages={messages} isStreaming={isStreaming} />
      ) : (
        <ChatWelcome onExampleClick={handleExampleClick} />
      )}

      {/* Streaming indicator */}
      <StreamingIndicator
        statusMessage={statusMessage}
        isStreaming={isStreaming}
      />

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        onStop={stopGeneration}
        isStreaming={isStreaming}
        isConnected={isConnected}
        disabled={isConnecting}
      />
    </div>
  );
}
