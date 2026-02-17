'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Lock, Square } from 'lucide-react';
import { useContentSelectionStore } from '@/stores/content-selection-store';
import { useAuth } from '@/hooks/use-auth';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  isConnected?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming = false,
  isConnected = true,
  disabled = false,
  placeholder = '무엇이든 물어보세요...',
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [showSourceModal, setShowSourceModal] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { isAuthenticated, loginUrl } = useAuth();
  const { selectedIds, selectedInfo } = useContentSelectionStore();

  const selectedCount = selectedIds.length;
  const canSend = isAuthenticated && isConnected && !isStreaming && !disabled && input.trim().length > 0;

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!canSend) return;
    onSend(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Skip if IME is composing (Korean, Japanese, Chinese input)
    // nativeEvent.isComposing catches the composing state reliably across browsers
    if (e.nativeEvent.isComposing) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleLogin = () => {
    if (loginUrl) {
      window.location.href = loginUrl;
    }
  };

  // Locked state (unauthenticated)
  if (!isAuthenticated) {
    return (
      <div className="w-[95%] mx-auto my-[10px_auto_20px]">
        <div
          className="relative bg-grey-2 rounded-md border border-grey-3 p-[35px] pr-[120px] box-border"
        >
          <span className="text-lg font-normal text-grey-4">
            로그인 후 질문할 수 있습니다
          </span>
          <button
            onClick={handleLogin}
            className="absolute right-5 top-1/2 -translate-y-1/2 w-[50px] h-[50px]
              bg-grey-2 rounded-pill border border-grey-3 cursor-pointer
              transition-all duration-200 flex items-center justify-center
              hover:cursor-not-allowed"
            aria-label="로그인 필요"
          >
            <Lock className="w-5 h-5 text-grey-3" strokeWidth={1.5} />
          </button>
        </div>
      </div>
    );
  }

  // Unlocked state (authenticated)
  return (
    <div className="w-[95%] mx-auto my-[10px_auto_20px]">
      <div
        className="relative bg-white rounded-md p-5 pr-[120px] box-border"
        style={{ border: '1.5px solid var(--color-black)' }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={!isConnected ? '연결 중...' : placeholder}
          disabled={disabled || !isConnected}
          className="w-full min-h-[40px] max-h-[200px] bg-transparent border-none
            resize-none outline-none overflow-y-auto font-normal text-lg text-black
            break-words whitespace-pre-wrap placeholder:text-grey-3"
          rows={1}
        />

        {/* Source count indicator */}
        {selectedCount > 0 && (
          <div
            className="absolute right-[90px] top-1/2 -translate-y-1/2"
            onMouseEnter={() => setShowSourceModal(true)}
            onMouseLeave={() => setShowSourceModal(false)}
          >
            <span className="text-sm text-grey-4 cursor-pointer select-none hover:text-blue-2">
              소스 {selectedCount}개
            </span>

            {/* Source modal */}
            {showSourceModal && (
              <div
                className="absolute right-0 bottom-[calc(100%+10px)] z-[1000]
                  bg-white border border-grey-3 rounded-sm shadow-lg
                  min-w-[250px] max-w-[400px]"
              >
                <div className="p-3">
                  <p className="text-xs font-medium text-grey-4 mb-2 pb-1.5 border-b border-grey-2">
                    선택된 문서
                  </p>
                  <div className="flex flex-col gap-1.5">
                    {selectedInfo.map((info, idx) => (
                      <p key={idx} className="text-[13px] text-blue-2 py-1 border-b border-grey-1 last:border-b-0">
                        {info.title}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Send or Stop button */}
        {isStreaming ? (
          <button
            onClick={onStop}
            className="absolute right-5 top-1/2 -translate-y-1/2 w-[50px] h-[50px]
              bg-grey-1 rounded-pill border-none cursor-pointer
              transition-all duration-200 flex items-center justify-center
              hover:bg-btn-hover"
            aria-label="생성 중단"
          >
            <PauseIcon className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!canSend}
            className={`absolute right-5 top-1/2 -translate-y-1/2 w-[50px] h-[50px]
              rounded-pill border-none cursor-pointer
              transition-all duration-200 flex items-center justify-center
              ${canSend ? 'bg-blue-2' : 'bg-grey-1'}
              ${!canSend && 'cursor-not-allowed'}`}
            aria-label="메시지 전송"
          >
            <SendIcon className={canSend ? 'text-white' : 'text-grey-3'} />
          </button>
        )}
      </div>
    </div>
  );
}

// Custom send icon matching the original design
function SendIcon({ className }: { className?: string }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      className={className}
    >
      <path
        d="M12 19V5M12 5L5 12M12 5L19 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Pause icon for stop button
function PauseIcon({ className }: { className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
    >
      <rect x="6" y="4" width="4" height="16" rx="1" />
      <rect x="14" y="4" width="4" height="16" rx="1" />
    </svg>
  );
}
