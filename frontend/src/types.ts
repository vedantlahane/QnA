export type User = {
  id: number
  username: string
  email: string | null
  first_name: string
  last_name: string
}

export type DocumentItem = {
  id: number
  original_name: string
  file_url: string | null
  size: number
  content_type: string
  processed: boolean
  processing_error: string
  created_at: string
  updated_at: string
}

export type MessageItem = {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export type ConversationItem = {
  id: number
  title: string
  documents: DocumentItem[]
  messages?: MessageItem[]
  created_at: string
  updated_at: string
}

export type ChatPayload = {
  conversation_id?: number
  title?: string
  document_ids?: number[]
  message: string
}
