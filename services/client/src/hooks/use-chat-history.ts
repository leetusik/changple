'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type { ChatSession, ChatMessage, PaginatedResponse } from '@/types';

/**
 * Fetch chat session history
 */
async function fetchChatHistory(): Promise<PaginatedResponse<ChatSession>> {
  const { data } = await api.get<PaginatedResponse<ChatSession>>('/chat/history/');
  return data;
}

/**
 * Fetch messages for a specific session
 * Returns empty array if session doesn't exist yet (new session)
 */
async function fetchSessionMessages(nonce: string): Promise<ChatMessage[]> {
  try {
    // API returns { id, nonce, messages, created_at, updated_at }
    const { data } = await api.get<{ messages: ChatMessage[] }>(`/chat/${nonce}/messages/`);
    return data.messages || [];
  } catch (error: any) {
    // Return empty array for 404 (session doesn't exist yet - this is normal for new sessions)
    if (error.response?.status === 404) {
      return [];
    }
    throw error;
  }
}

/**
 * Delete a chat session
 */
async function deleteSession(nonce: string): Promise<void> {
  await api.delete(`/chat/${nonce}/`);
}

/**
 * Hook to get chat history list
 */
export function useChatHistory() {
  return useQuery({
    queryKey: ['chat', 'history'],
    queryFn: fetchChatHistory,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to get messages for a specific session
 */
export function useSessionMessages(nonce: string | null) {
  return useQuery({
    queryKey: ['chat', 'messages', nonce],
    queryFn: () => fetchSessionMessages(nonce!),
    enabled: nonce !== null,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to delete a chat session
 */
export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteSession,
    onSuccess: () => {
      // Invalidate chat history to refetch
      queryClient.invalidateQueries({ queryKey: ['chat', 'history'] });
    },
  });
}
