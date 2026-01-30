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
  thumbnail: string | null;
  uploaded_at: string;
  view_count: number;
  // Extended fields for display
  summary?: string;
  url?: string;
  sourceType?: 'naver_cafe' | 'notion';
}

export interface ContentDetail extends Content {
  text: string;
  notion_url: string | null;
}

// Alias for display components (uses summary as fallback for description)
export type ContentItem = Content & {
  thumbnailUrl?: string; // Alias for thumbnail
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
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  attached_content_ids: number[];
  helpful_document_post_ids: number[];
}

// WebSocket message types (Client → Agent)
export interface ClientMessage {
  type: 'message' | 'stop_generation';
  content?: string;
  content_ids?: number[];
  user_id?: number | null;
}

// WebSocket message types (Agent → Client)
export type AgentMessageType =
  | 'session_created'
  | 'status_update'
  | 'stream_chunk'
  | 'stream_end'
  | 'generation_stopped'
  | 'error';

export interface SessionCreatedMessage {
  type: 'session_created';
  nonce: string;
}

export interface StatusUpdateMessage {
  type: 'status_update';
  message: string;
}

export interface StreamChunkMessage {
  type: 'stream_chunk';
  content: string;
}

export interface SourceDocument {
  id: number;
  title: string;
  source: string;
}

export interface StreamEndMessage {
  type: 'stream_end';
  source_documents: SourceDocument[];
  processed_content: string;
}

export interface GenerationStoppedMessage {
  type: 'generation_stopped';
}

export interface ErrorMessage {
  type: 'error';
  message: string;
  code?: string;
}

export type AgentMessage =
  | SessionCreatedMessage
  | StatusUpdateMessage
  | StreamChunkMessage
  | StreamEndMessage
  | GenerationStoppedMessage
  | ErrorMessage;

// UI state types
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: SourceDocument[];
  isStreaming?: boolean;
  createdAt?: Date;
}

export interface SelectedContent {
  id: number;
  title: string;
}
