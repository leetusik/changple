"use client";

import { useQuery, useInfiniteQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Content, ContentDetail, PaginatedResponse } from "@/types";

/**
 * Fetch preferred/featured content
 */
async function fetchPreferredContent(): Promise<Content[]> {
  const { data } = await api.get<Content[]>("/api/v1/content/preferred/");
  return data;
}

/**
 * Fetch paginated content list (recent)
 */
async function fetchRecentContent(
  page: number
): Promise<PaginatedResponse<Content>> {
  const { data } = await api.get<PaginatedResponse<Content>>(
    "/api/v1/content/columns/",
    {
      params: { page },
    }
  );
  return data;
}

/**
 * Fetch content detail
 */
async function fetchContentDetail(id: number): Promise<ContentDetail> {
  const { data } = await api.get<ContentDetail>(`/api/v1/content/${id}/`);
  return data;
}

/**
 * Fetch text content for attachment (selected content IDs)
 */
async function fetchAttachment(
  contentIds: number[]
): Promise<{ texts: string[] }> {
  const { data } = await api.post<{ texts: string[] }>(
    "/api/v1/content/attachment/",
    {
      content_ids: contentIds,
    }
  );
  return data;
}

/**
 * Record content view
 */
async function recordContentView(id: number): Promise<void> {
  await api.post("/api/v1/content/view/", { content_id: id });
}

/**
 * Hook to get preferred/featured content
 */
export function usePreferredContent() {
  return useQuery({
    queryKey: ["content", "preferred"],
    queryFn: fetchPreferredContent,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get recent content with pagination
 */
export function useRecentContent() {
  return useInfiniteQuery({
    queryKey: ["content", "recent"],
    queryFn: ({ pageParam = 1 }) => fetchRecentContent(pageParam),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (lastPage.next) {
        // Extract page number from URL
        const url = new URL(lastPage.next);
        const page = url.searchParams.get("page");
        return page ? parseInt(page, 10) : undefined;
      }
      return undefined;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Hook to get content detail
 */
export function useContentDetail(id: number | null) {
  return useQuery({
    queryKey: ["content", "detail", id],
    queryFn: () => fetchContentDetail(id!),
    enabled: id !== null,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to get attachment text for selected content
 */
export function useAttachment(contentIds: number[]) {
  return useQuery({
    queryKey: ["content", "attachment", contentIds],
    queryFn: () => fetchAttachment(contentIds),
    enabled: contentIds.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook to record content view
 */
export function useRecordView() {
  return useMutation({
    mutationFn: recordContentView,
  });
}

/**
 * Flatten paginated results for easy rendering
 */
export function flattenRecentContent(
  data: ReturnType<typeof useRecentContent>["data"]
): Content[] {
  if (!data) return [];
  return data.pages.flatMap((page) => page.results);
}
