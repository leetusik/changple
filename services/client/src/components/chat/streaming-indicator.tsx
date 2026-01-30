'use client';

interface StreamingIndicatorProps {
  statusMessage: string | null;
  isStreaming: boolean;
}

export function StreamingIndicator({
  statusMessage,
  isStreaming,
}: StreamingIndicatorProps) {
  if (!isStreaming && !statusMessage) return null;

  return (
    <div className="flex items-center gap-2 px-4 py-2 text-sm text-grey-4">
      {/* Loading dots animation */}
      <div className="flex gap-1">
        <span
          className="w-2 h-2 bg-blue-2 rounded-full animate-bounce"
          style={{ animationDelay: '0ms' }}
        />
        <span
          className="w-2 h-2 bg-blue-2 rounded-full animate-bounce"
          style={{ animationDelay: '150ms' }}
        />
        <span
          className="w-2 h-2 bg-blue-2 rounded-full animate-bounce"
          style={{ animationDelay: '300ms' }}
        />
      </div>
      <span>{statusMessage || '답변 생성 중...'}</span>
    </div>
  );
}
