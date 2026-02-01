'use client';

import { ContentList } from "./content-list";
import { ContentDetail } from "./content-detail";
import {
  usePreferredContent,
  useRecentContent,
  flattenRecentContent,
} from "@/hooks";
import { useUIStore } from "@/stores/ui-store";
import { useEffect } from "react";

export function ContentSidebar() {
  const preferredQuery = usePreferredContent();
  const recentQuery = useRecentContent();
  const { sidebarView, selectedContentDetailId } = useUIStore();

  // If viewing content details, show the detail view
  if (sidebarView === "details" && selectedContentDetailId !== null) {
    return <ContentDetail contentId={selectedContentDetailId} />;
  }

  // Default: show content list
  return (
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
          {recentQuery.isFetchingNextPage ? "로딩 중..." : "더 보기"}
        </button>
      )}
    </div>
  );
}
