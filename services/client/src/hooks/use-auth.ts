'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type { AuthStatus, User } from '@/types';

/**
 * Fetch current auth status from Core service
 */
async function fetchAuthStatus(): Promise<AuthStatus> {
  const { data } = await api.get<AuthStatus>('/api/v1/auth/status/');
  return data;
}

/**
 * Logout from Core service
 */
async function logout(): Promise<void> {
  await api.post('/api/v1/auth/logout/');
}

/**
 * Hook to get current authentication status
 */
export function useAuth() {
  const query = useQuery({
    queryKey: ['auth', 'status'],
    queryFn: fetchAuthStatus,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });

  return {
    user: query.data?.user ?? null,
    isAuthenticated: query.data?.is_authenticated ?? false,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    loginUrl: getLoginUrl(),
  };
}

/**
 * Hook to handle logout
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      // Clear auth cache
      queryClient.setQueryData(['auth', 'status'], {
        is_authenticated: false,
        user: null,
      });
      // Invalidate all queries that depend on auth
      queryClient.invalidateQueries({ queryKey: ['chat'] });
    },
  });
}

/**
 * Get Naver OAuth login URL
 */
export function getLoginUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
  return `${baseUrl}/api/v1/auth/naver/login/`;
}

/**
 * Hook for protected routes - redirects to login if not authenticated
 */
export function useRequireAuth() {
  const { user, isAuthenticated, isLoading } = useAuth();

  return {
    user,
    isAuthenticated,
    isLoading,
    // Can be used to conditionally render protected content
    isReady: !isLoading && isAuthenticated,
  };
}
