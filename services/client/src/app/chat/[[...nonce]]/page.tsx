'use client';

import { use } from 'react';
import { MainLayout } from '@/components/layout';
import { ChatContainer } from '@/components/chat';
import { ContentList } from '@/components/content';
import { usePreferredContent, useRecentContent, flattenRecentContent } from '@/hooks';

interface ChatPageProps {
  params: Promise<{ nonce?: string[] }>;
}

export default function ChatPage({ params }: ChatPageProps) {
  const resolvedParams = use(params);
  const nonce = resolvedParams.nonce?.[0];

  // Fetch content for sidebar
  const preferredQuery = usePreferredContent();
  const recentQuery = useRecentContent();

  const handleHistoryClick = () => {
    // TODO: Open history panel
    console.log('History clicked');
  };

  // Sidebar content
  const sidebarContent = (
    <div className="flex flex-col w-full h-full px-1.5 overflow-y-auto overflow-x-hidden hide-scrollbar">
      {/* Preferred content section */}
      {preferredQuery.data && preferredQuery.data.length > 0 && (
        <ContentList
          title="인기 칼럼"
          contents={preferredQuery.data}
          isLoading={preferredQuery.isLoading}
        />
      )}

      {/* Recent content section */}
      <ContentList
        title="최근 소식"
        contents={flattenRecentContent(recentQuery.data)}
        isLoading={recentQuery.isLoading}
      />

      {/* Load more button */}
      {recentQuery.hasNextPage && (
        <button
          onClick={() => recentQuery.fetchNextPage()}
          disabled={recentQuery.isFetchingNextPage}
          className="w-full py-3 text-sm text-grey-4 hover:text-grey-5 hover:bg-grey-1 rounded-md transition-colors disabled:opacity-50"
        >
          {recentQuery.isFetchingNextPage ? '로딩 중...' : '더 보기'}
        </button>
      )}
    </div>
  );

  return (
    <MainLayout
      sidebarContent={sidebarContent}
      onHistoryClick={handleHistoryClick}
    >
      <ChatContainer initialNonce={nonce} />
    </MainLayout>
  );
}
