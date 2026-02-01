"use client";

import { useRouter } from "next/navigation";
import { MainLayout } from "@/components/layout";
import { ChatWelcome, ChatHistory, ChatInput } from "@/components/chat";
import { ContentSidebar } from "@/components/content";
import { useAuth } from "@/hooks";
import { useUIStore } from "@/stores/ui-store";

export default function Home() {
  const router = useRouter();
  const { user } = useAuth();
  const { sidebarView, showHistory, showContentList } = useUIStore();

  const handleSendMessage = (question: string) => {
    // Navigate to chat page - question will be sent after WebSocket connects
    // Store question in sessionStorage for the chat page to pick up
    sessionStorage.setItem("pendingQuestion", question);
    router.push("/chat");
  };

  const handleHistoryClick = () => {
    showHistory();
  };

  const handleBackClick = () => {
    showContentList();
  };

  // Sidebar content based on current view
  const getSidebarContent = () => {
    if (sidebarView === "history") {
      return <ChatHistory />;
    }

    // Default: content list/detail view (ContentSidebar handles both)
    return <ContentSidebar />;
  };

  // Show back button for history and details views
  const showBackButton = sidebarView === "history" || sidebarView === "details";

  return (
    <MainLayout
      sidebarContent={getSidebarContent()}
      onHistoryClick={handleHistoryClick}
      showBackButton={showBackButton}
      onBackClick={handleBackClick}
    >
      <div className="flex flex-col h-full w-full">
        <ChatWelcome
          userName={user?.nickname}
          onExampleClick={handleSendMessage}
        />
        <ChatInput onSend={handleSendMessage} isConnected={true} />
      </div>
    </MainLayout>
  );
}
