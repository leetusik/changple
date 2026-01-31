import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api/v1',
  withCredentials: true, // Send session cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Get CSRF token from cookie (Django sets 'csrftoken' cookie)
 */
function getCSRFToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

// Add CSRF token to all non-GET requests
api.interceptors.request.use((config) => {
  if (config.method && config.method.toLowerCase() !== 'get') {
    const token = getCSRFToken();
    if (token) {
      config.headers['X-CSRFToken'] = token;
    }
  }
  return config;
});

// Handle 401 responses (session expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Optionally trigger auth refresh or redirect
      console.warn('Session expired or not authenticated');
    }
    return Promise.reject(error);
  }
);

export default api;

// API endpoints
export const authApi = {
  status: () => api.get('/auth/status/'),
  logout: () => api.post('/auth/logout/'),
};

export const usersApi = {
  me: () => api.get('/users/me/'),
  updateProfile: (data: { name?: string; nickname?: string; mobile?: string }) =>
    api.patch('/users/profile/', data),
};

export const contentApi = {
  columns: (page = 1) => api.get(`/content/columns/?page=${page}`),
  preferred: () => api.get('/content/preferred/'),
  detail: (id: number) => api.get(`/content/${id}/`),
  attachment: (contentIds: number[]) =>
    api.post('/content/attachment/', { content_ids: contentIds }),
};

export const chatApi = {
  history: (page = 1) => api.get(`/chat/history/?page=${page}`),
  messages: (nonce: string) => api.get(`/chat/${nonce}/messages/`),
  deleteSession: (nonce: string) => api.delete(`/chat/${nonce}/`),
};
