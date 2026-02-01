'use client';

import { useEffect, useState, useRef } from 'react';
import { useContentDetail, useRecordView } from '@/hooks';
import { ImageModal } from './image-modal';

interface ContentDetailProps {
  contentId: number;
}

export function ContentDetail({ contentId }: ContentDetailProps) {
  const { data: content, isLoading, error } = useContentDetail(contentId);
  const { mutate: recordView } = useRecordView();

  const [modalImage, setModalImage] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const recordViewCalled = useRef(false);

  // Get absolute URL for iframe src (handle both relative and absolute URLs)
  const getAbsoluteUrl = (url: string | null) => {
    if (!url) return null;
    if (url.startsWith('http')) return url; // Already absolute

    // Relative URL - prepend backend URL in development
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || '';
    // Encode the URL to handle spaces and special characters
    const encodedUrl = url.split('/').map(part => encodeURIComponent(part)).join('/');
    // We only encoded parts, so slashes are preserved. 
    // But wait, url is full path "/media/html_content/...". 
    // If I split by /, empty parts will be encoded? 
    // "/a/b" -> ["", "a", "b"] -> encoded -> ["", "a", "b"] (empty string encoded is empty).
    // So join('/') -> "/a/b". 
    // If "a b" -> "a%20b". 
    // This seems correct for path.
    // But let's use a safer approach: encodeURI(url) is usually fine for full path if it doesn't contain query params with special chars that shouldn't be encoded.
    // encodeURI leaves / : & + = ? @ # alone. It encodes spaces.
    
    const safeUrl = encodeURI(url);
    const absoluteUrl = backendUrl + safeUrl;

    return absoluteUrl;
  };

  // Record view on mount
  useEffect(() => {
    if (!recordViewCalled.current && contentId) {
      recordView(contentId);
      recordViewCalled.current = true;
    }
  }, [contentId, recordView]);

  // Reset recordViewCalled when contentId changes
  useEffect(() => {
    recordViewCalled.current = false;
  }, [contentId]);

  // Handle iframe messages (from injected script)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data === 'iframeScrollEnd') {
        console.log('User scrolled to end of content', contentId);
      } else if (event.data?.type === 'openImageModal' && event.data?.imageUrl) {
        setModalImage(event.data.imageUrl);
        setIsModalOpen(true);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [contentId]);

  // Adjust iframe height to content
  useEffect(() => {
    if (!iframeRef.current || !content?.html_url) return;

    const adjustIframeHeight = () => {
      const iframe = iframeRef.current;
      if (!iframe) return;

      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
        if (iframeDoc) {
          const height = iframeDoc.documentElement.scrollHeight;
          iframe.style.height = `${height}px`;
        }
      } catch {
        // Cross-origin iframe - can't access content
      }
    };

    const iframe = iframeRef.current;
    iframe.addEventListener('load', adjustIframeHeight);

    return () => {
      iframe.removeEventListener('load', adjustIframeHeight);
    };
  }, [content?.html_url]);

  if (isLoading) {
    return (
      <div className="flex flex-col w-full h-full">
        <div className="flex items-center justify-center flex-1">
          <p className="text-grey-4">로딩 중...</p>
        </div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="flex flex-col w-full h-full">
        <div className="flex flex-col items-center justify-center flex-1 gap-2">
          <p className="text-grey-4">콘텐츠를 불러올 수 없습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full h-full">
      {/* Title header */}
      <div className="flex items-center w-full px-2 py-3 border-b border-grey-2 bg-white">
        <h2 className="text-base font-medium truncate">{content.title}</h2>
      </div>

      {/* Iframe container - scrollable */}
      <div className="flex-1 w-full overflow-y-auto overflow-x-hidden hide-scrollbar bg-white">
        {content.html_url ? (
          <iframe
            ref={iframeRef}
            src={getAbsoluteUrl(content.html_url) || undefined}
            className="w-full border-0"
            style={{ minHeight: '100%' }}
            title={content.title}
            sandbox="allow-scripts allow-same-origin allow-popups"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-grey-4">HTML 콘텐츠가 없습니다.</p>
          </div>
        )}
      </div>

      <ImageModal
        isOpen={isModalOpen}
        imageUrl={modalImage}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
