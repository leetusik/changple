"use client";

import { useEffect, useState, useRef, use } from "react";
import { useRouter } from "next/navigation";
import { MainLayout } from "@/components/layout";
import { ContentSidebar, ImageModal } from "@/components/content";
import { useContentDetail, useRecordView } from "@/hooks";
import { useUIStore } from "@/stores/ui-store";
import { ChatHistory } from "@/components/chat";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ContentDetailPage({ params }: PageProps) {
  const { id: idStr } = use(params);
  const id = parseInt(idStr, 10);
  const router = useRouter();

  const { data: content, isLoading, error } = useContentDetail(id);
  const { mutate: recordView } = useRecordView();
  const { sidebarView, showHistory, showContentList } = useUIStore();

  const [modalImage, setModalImage] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const recordViewCalled = useRef(false);

  // Handle back navigation
  const handleBackClick = () => {
    // Check if there is history to go back to, otherwise go to home
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push("/");
    }
  };

  const handleSidebarBackClick = () => {
    showContentList();
  };

  const handleHistoryClick = () => {
    showHistory();
  };

  // Record view on mount
  useEffect(() => {
    if (!recordViewCalled.current && id) {
      recordView(id);
      recordViewCalled.current = true;
    }
  }, [id, recordView]);

  // Handle iframe messages
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data === "iframeScrollEnd") {
        console.log("User scrolled to end of content", id);
      } else if (
        event.data?.type === "openImageModal" &&
        event.data?.imageUrl
      ) {
        setModalImage(event.data.imageUrl);
        setIsModalOpen(true);
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [id]);

  // Sidebar content
  const getSidebarContent = () => {
    if (sidebarView === "history") {
      return <ChatHistory />;
    }
    return <ContentSidebar />;
  };

  if (isLoading) {
    return (
      <MainLayout
        sidebarContent={getSidebarContent()}
        onHistoryClick={handleHistoryClick}
        showBackButton={sidebarView === "history"}
        onBackClick={handleSidebarBackClick}
      >
        <div className="flex items-center justify-center w-full h-full">
          <p>로딩 중...</p>
        </div>
      </MainLayout>
    );
  }

  if (error || !content) {
    return (
      <MainLayout
        sidebarContent={getSidebarContent()}
        onHistoryClick={handleHistoryClick}
        showBackButton={sidebarView === "history"}
        onBackClick={handleSidebarBackClick}
      >
        <div className="flex flex-col items-center justify-center w-full h-full gap-4">
          <p>콘텐츠를 불러올 수 없습니다.</p>
          <button
            onClick={() => router.push("/")}
            className="px-4 py-2 text-white bg-blue-1 rounded-md hover:bg-blue-2"
          >
            홈으로 돌아가기
          </button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout
      sidebarContent={getSidebarContent()}
      onHistoryClick={handleHistoryClick}
      showBackButton={sidebarView === "history"}
      onBackClick={handleSidebarBackClick}
    >
      <div className="flex flex-col w-full h-full relative">
        {/* Header with back button for mobile/desktop convenience */}
        <div className="flex items-center w-full p-4 border-b border-grey-2 bg-white z-10">
          <button
            onClick={handleBackClick}
            className="mr-4 text-grey-5 hover:text-black transition-colors"
          >
            ← 뒤로가기
          </button>
          <h1 className="text-lg font-medium truncate flex-1">
            {content.title}
          </h1>
        </div>

        {/* Iframe container */}
        <div className="flex-1 w-full h-full overflow-hidden bg-white relative">
          {content.html_url ? (
            <iframe
              ref={iframeRef}
              src={content.html_url}
              className="w-full h-full border-0"
              title={content.title}
              sandbox="allow-scripts allow-same-origin allow-popups"
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <p>HTML 콘텐츠가 없습니다.</p>
            </div>
          )}
        </div>
      </div>

      <ImageModal
        isOpen={isModalOpen}
        imageUrl={modalImage}
        onClose={() => setIsModalOpen(false)}
      />
    </MainLayout>
  );
}
