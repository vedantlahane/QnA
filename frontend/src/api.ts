import type { ChatPayload, ConversationItem, DocumentItem, User } from './types'

type RegisterPayload = {
  username: string
  email: string
  password: string
  first_name: string
  last_name: string
}

type LoginPayload = {
  username: string
  password: string
}

type AuthResponse = {
  token: string
  user: User
}

const normalizeBaseUrl = (value: string | undefined): string => {
  if (!value) {
    return 'http://localhost:8000/api'
  }
  return value.endsWith('/') ? value.slice(0, -1) : value
}

const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL)

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
  const headers = new Headers(options.headers)

  if (token) {
    headers.set('Authorization', `Token ${token}`)
  }

  const isFormData = options.body instanceof FormData
  if (!isFormData && options.method && options.method !== 'GET') {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let message = response.statusText || 'Request failed'
    try {
      const data = await response.json()
      if (typeof data === 'string') {
        message = data
      } else if (data.detail) {
        message = data.detail
      } else if (data.message) {
        message = data.message
      } else {
        message = JSON.stringify(data)
      }
    } catch (error) {
      if (error instanceof Error) {
        message = error.message || message
      }
    }
    throw new Error(message)
  }

  if (response.status === 204) {
    return null as T
  }

  try {
    return (await response.json()) as T
  } catch {
    return null as T
  }
}

export const api = {
  register: (payload: RegisterPayload) =>
    request<AuthResponse>('/auth/register/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  login: (payload: LoginPayload) =>
    request<AuthResponse>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  logout: (token: string) =>
    request<void>(
      '/auth/logout/',
      {
        method: 'POST',
      },
      token,
    ),
  profile: (token: string) => request<User>('/auth/me/', { method: 'GET' }, token),
  listDocuments: (token: string) => request<DocumentItem[]>('/files/', { method: 'GET' }, token),
  uploadDocument: (token: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<DocumentItem>(
      '/files/',
      {
        method: 'POST',
        body: formData,
      },
      token,
    )
  },
  deleteDocument: (token: string, id: number) =>
    request<void>(
      `/files/${id}/`,
      {
        method: 'DELETE',
      },
      token,
    ),
  listConversations: (token: string) =>
    request<ConversationItem[]>('/conversations/', { method: 'GET' }, token),
  retrieveConversation: (token: string, id: number) =>
    request<ConversationItem>(`/conversations/${id}/`, { method: 'GET' }, token),
  sendChat: (token: string, payload: ChatPayload) =>
    request<ConversationItem>(
      '/chat/',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      token,
    ),
}

export type { RegisterPayload, LoginPayload, AuthResponse, ChatPayload }
