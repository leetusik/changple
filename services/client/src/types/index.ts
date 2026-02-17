// User types
export interface User {
  id: number;
  email: string;
  name: string;
  nickname: string;
  profile_image: string | null;
  user_type: string;
  provider: string;
  mobile: string | null;
  information: string | null;
  date_joined: string;
}

export interface AuthStatus {
  is_authenticated: boolean;
  user: User | null;
}

// Content types (from Core API)
export interface Content {
  id: number;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  is_preferred: boolean;
  uploaded_at: string;
  // Extended fields for display
  summary?: string;
  url?: string;
}

export interface ContentDetail extends Content {
  html_url: string | null;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Chat types
export interface ChatSession {
  id: number;
  nonce: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  attached_content_ids: number[];
  helpful_document_post_ids: number[];
}

// Source document from agent response
export interface SourceDocument {
  id: number;
  title: string;
  source: string;
}

// UI state types
export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceDocument[];
  isStreaming?: boolean;
  createdAt?: Date;
}

export interface SelectedContent {
  id: number;
  title: string;
}
