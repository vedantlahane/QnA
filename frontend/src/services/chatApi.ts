const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

export interface RawConversationSummary {
  id: string;
  title: string;
  summary: string;
  updatedAt: string;
  updatedAtISO?: string;
  messageCount?: number;
}

export interface RawMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface RawConversationDetail extends RawConversationSummary {
  messages: RawMessage[];
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchConversations(): Promise<RawConversationSummary[]> {
  const response = await fetch(`${API_BASE_URL}/conversations/`);
  const data = await handleResponse<{ conversations: RawConversationSummary[] }>(response);
  return data.conversations ?? [];
}

export async function fetchConversation(conversationId: string): Promise<RawConversationDetail> {
  const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/`);
  return handleResponse<RawConversationDetail>(response);
}

export interface SendChatPayload {
  message: string;
  conversationId?: string;
  title?: string;
}

export async function sendChatMessage(payload: SendChatPayload): Promise<RawConversationDetail> {
  const body: Record<string, unknown> = {
    message: payload.message,
  };

  if (payload.conversationId) {
    body.conversation_id = payload.conversationId;
  }

  if (payload.title) {
    body.title = payload.title;
  }

  const response = await fetch(`${API_BASE_URL}/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  return handleResponse<RawConversationDetail>(response);
}
