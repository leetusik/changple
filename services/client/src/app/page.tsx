'use client';

import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/layout';
import { ChatWelcome } from '@/components/chat/chat-welcome';
import { ContentList } from '@/components/content';
import { usePreferredContent, useRecentContent, flattenRecentContent, useAuth } from '@/hooks';

export default function Home() {
  const router = useRouter();
  const { user } = useAuth();

  // Fetch content for sidebar
  const preferredQuery = usePreferredContent();
  const recentQuery = useRecentContent();

  const handleExampleClick = (question: string) => {
    // Navigate to chat page - question will be sent after WebSocket connects
    // Store question in sessionStorage for the chat page to pick up
    sessionStorage.setItem('pendingQuestion', question);
    router.push('/chat');
  };

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
      <ChatWelcome
        userName={user?.nickname}
        onExampleClick={handleExampleClick}
      />
    </MainLayout>
  );
}
