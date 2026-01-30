'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import type { Message, SourceDocument } from '@/types';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';
  const hasSources = message.sources && message.sources.length > 0;

  return (
    <div
      className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[80%] ${
          isUser
            ? 'bg-blue-2 text-white rounded-[20px] rounded-br-[4px] px-4 py-3'
            : 'bg-grey-1 text-black rounded-[20px] rounded-bl-[4px] px-4 py-3'
        }`}
      >
        {/* Message content */}
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
            {message.isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-grey-4 animate-pulse" />
            )}
          </div>
        )}

        {/* Source documents toggle */}
        {hasSources && !message.isStreaming && (
          <div className="mt-3 pt-3 border-t border-grey-2">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-sm text-grey-4 hover:text-grey-5"
            >
              <span>출처 {message.sources!.length}개</span>
              {showSources ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>

            {showSources && (
              <ul className="mt-2 space-y-1">
                {message.sources!.map((source, idx) => (
                  <SourceItem key={idx} source={source} />
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SourceItem({ source }: { source: SourceDocument }) {
  return (
    <li className="text-sm">
      <a
        href={source.source}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1 text-blue-3 hover:text-blue-4 hover:underline"
      >
        <span className="truncate max-w-[250px]">{source.title}</span>
        <ExternalLink className="w-3 h-3 flex-shrink-0" />
      </a>
    </li>
  );
}
