'use client';

import { use } from 'react';
import { MainLayout } from '@/components/layout';
import { ChatContainer, ChatHistory } from '@/components/chat';
import { ContentSidebar } from '@/components/content';
import { useUIStore } from '@/stores/ui-store';

interface ChatPageProps {
  params: Promise<{ nonce?: string[] }>;
}

export default function ChatPage({ params }: ChatPageProps) {
  const resolvedParams = use(params);
  const nonce = resolvedParams.nonce?.[0];
  const { sidebarView, showHistory, showContentList } = useUIStore();

  const handleHistoryClick = () => {
    showHistory();
  };

  const handleBackClick = () => {
    showContentList();
  };

  // Sidebar content based on current view
  const getSidebarContent = () => {
    if (sidebarView === 'history') {
      return <ChatHistory />;
    }
    return <ContentSidebar />;
  };

  // Show back button for history and details views
  const showBackButton = sidebarView === 'history' || sidebarView === 'details';

  return (
    <MainLayout
      sidebarContent={getSidebarContent()}
      onHistoryClick={handleHistoryClick}
      showBackButton={showBackButton}
      onBackClick={handleBackClick}
    >
      <ChatContainer initialNonce={nonce} />
    </MainLayout>
  );
}
