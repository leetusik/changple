'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send, Square, Paperclip } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
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
  placeholder = '메시지를 입력하세요...',
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { isAuthenticated } = useAuth();
  const selectedIds = useContentSelectionStore((s) => s.selectedIds);

  const selectedCount = selectedIds.length;
  const canSend = isConnected && !isStreaming && !disabled && input.trim().length > 0;

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
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends, Shift+Enter adds newline
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4">
      {/* Source counter */}
      {selectedCount > 0 && (
        <div className="flex items-center gap-2 mb-2 text-sm text-blue-3">
          <Paperclip className="w-4 h-4" />
          <span>소스 {selectedCount}개 첨부됨</span>
        </div>
      )}

      {/* Input area */}
      <div className="relative flex items-end gap-2 p-2 bg-grey-0 rounded-md border border-grey-2 focus-within:border-blue-2 transition-colors">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            !isAuthenticated
              ? '로그인 후 질문할 수 있습니다'
              : !isConnected
                ? '연결 중...'
                : placeholder
          }
          disabled={disabled || !isAuthenticated || !isConnected}
          className="flex-1 min-h-[44px] max-h-[200px] resize-none border-none bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-base"
          rows={1}
        />

        {/* Send or Stop button */}
        {isStreaming ? (
          <Button
            onClick={onStop}
            variant="ghost"
            size="icon"
            className="flex-shrink-0 h-10 w-10 rounded-full bg-grey-3 hover:bg-grey-4"
            aria-label="생성 중단"
          >
            <Square className="w-4 h-4 text-white fill-white" />
          </Button>
        ) : (
          <Button
            onClick={handleSend}
            disabled={!canSend || !isAuthenticated}
            variant="ghost"
            size="icon"
            className={`flex-shrink-0 h-10 w-10 rounded-full transition-colors ${
              canSend
                ? 'bg-blue-2 hover:bg-blue-3 text-white'
                : 'bg-grey-2 text-grey-4 cursor-not-allowed'
            }`}
            aria-label="메시지 전송"
          >
            <Send className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* Keyboard hint */}
      <p className="mt-1 text-xs text-grey-3 text-center">
        Enter로 전송, Shift+Enter로 줄바꿈
      </p>
    </div>
  );
}
