'use client';

import { useRef, useEffect } from 'react';
import { MessageBubble } from './message-bubble';
import { StreamingIndicator } from './streaming-indicator';
import type { Message } from '@/types';

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  statusMessage?: string | null;
}

export function MessageList({ messages, isStreaming, statusMessage }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive or during streaming
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming, statusMessage]);

  if (messages.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col py-4 max-w-3xl mx-auto">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {/* Show status indicator in the message flow, where the next message would appear */}
      <StreamingIndicator statusMessage={statusMessage ?? null} isStreaming={!!isStreaming} />
      <div ref={bottomRef} />
    </div>
  );
}
