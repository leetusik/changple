'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ThumbsUp, ThumbsDown, ExternalLink } from 'lucide-react';
import type { Message, SourceDocument } from '@/types';

interface MessageBubbleProps {
  message: Message;
  userSelectedSources?: SourceDocument[];
}

export function MessageBubble({ message, userSelectedSources = [] }: MessageBubbleProps) {
  const [showSources, setShowSources] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const isUser = message.role === 'user';
  const hasSources = message.sources && message.sources.length > 0;

  if (isUser) {
    return (
      <div className="flex w-full justify-end mb-[36px]">
        <p
          className="inline-block max-w-[60%] bg-key-1 text-grey-4 px-[14px] py-2
            rounded-[16px_16px_0_16px] whitespace-pre-line text-base leading-[1.5] text-left break-words"
        >
          {message.content}
        </p>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="text-left mb-[70px]">
      {/* Message content */}
      <div className="inline-block max-w-[60%] px-6 py-2 rounded-[0_16px_16px_16px]">
        {message.isStreaming ? (
          message.content ? (
            <div className="markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          ) : null
        ) : (
          <div className="markdown-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children, ...props }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-2 hover:underline" {...props}>
                    {children}
                  </a>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {/* Response actions - only show when not streaming and has sources */}
      {!message.isStreaming && hasSources && (
        <>
          <div className="response-actions-container">
            {/* 출처 보기 button */}
            <button
              onClick={() => setShowSources(!showSources)}
              className={`response-button ${showSources ? 'active' : ''}`}
            >
              <ChevronDown className="w-[17px] h-[10px] text-grey-3" />
              <span>출처 보기</span>
            </button>

            {/* Feedback buttons */}
            <div className="feedback-buttons">
              <button
                onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
                className={`like-button ${feedback === 'up' ? 'active' : ''}`}
                aria-label="좋아요"
              >
                <ThumbsUp
                  className={`w-[18px] h-[18px] ${
                    feedback === 'up' ? 'fill-blue-1 text-blue-1' : 'text-grey-4'
                  }`}
                />
              </button>
              <button
                onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
                className={`dislike-button ${feedback === 'down' ? 'active' : ''}`}
                aria-label="싫어요"
              >
                <ThumbsDown
                  className={`w-[18px] h-[18px] ${
                    feedback === 'down' ? 'fill-blue-1 text-blue-1' : 'text-grey-4'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Source container - collapsible */}
          {showSources && (
            <div className="source-container">
              {/* User-selected sources */}
              {userSelectedSources.length > 0 && (
                <>
                  <p className="source-section-title">사용자가 선택한 참조 문서</p>
                  {userSelectedSources.map((source, idx) => (
                    <SourceItem key={`user-${idx}`} source={source} index={idx + 1} />
                  ))}
                  <div className="source-divider" />
                </>
              )}

              {/* AI-found sources */}
              <p className="source-section-title">창플AI가 찾은 관련 문서</p>
              {message.sources!.map((source, idx) => (
                <SourceItem
                  key={`ai-${idx}`}
                  source={source}
                  index={userSelectedSources.length + idx + 1}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SourceItem({ source, index }: { source: SourceDocument; index: number }) {
  return (
    <p className="source-item">
      <a
        href={source.source}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-grey-4 hover:underline"
      >
        <span>[{index}]</span>
        <span className="truncate max-w-[300px]">{source.title}</span>
        <ExternalLink className="w-3 h-3 flex-shrink-0 text-grey-4" />
      </a>
    </p>
  );
}
