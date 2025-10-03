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

// Mock data storage
// eslint-disable-next-line prefer-const
let mockUsers: User[] = [
  {
    id: 1,
    username: 'demo_user',
    email: 'demo@example.com',
    first_name: 'Demo',
    last_name: 'User',
  },
]

// eslint-disable-next-line prefer-const
let mockDocuments: DocumentItem[] = [
  {
    id: 1,
    original_name: 'sample_document.pdf',
    file_url: '/mock/sample_document.pdf',
    size: 1024000,
    content_type: 'application/pdf',
    processed: true,
    processing_error: '',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 2,
    original_name: 'user_guide.txt',
    file_url: '/mock/user_guide.txt',
    size: 512000,
    content_type: 'text/plain',
    processed: true,
    processing_error: '',
    created_at: '2024-01-16T14:30:00Z',
    updated_at: '2024-01-16T14:30:00Z',
  },
]

// eslint-disable-next-line prefer-const
let mockConversations: ConversationItem[] = [
  {
    id: 1,
    title: 'Sample Conversation',
    documents: [mockDocuments[0]],
    messages: [
      {
        id: 1,
        role: 'user',
        content: 'What is this document about?',
        created_at: '2024-01-15T10:05:00Z',
      },
      {
        id: 2,
        role: 'assistant',
        content: 'This document appears to be a sample PDF file. It contains information about various topics. Based on the content, it seems to be a general reference document with multiple sections covering different subjects.',
        created_at: '2024-01-15T10:05:30Z',
      },
    ],
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:05:30Z',
  },
  {
    id: 2,
    title: 'User Guide Discussion',
    documents: [mockDocuments[1]],
    messages: [
      {
        id: 3,
        role: 'user',
        content: 'Can you help me understand this user guide?',
        created_at: '2024-01-16T14:35:00Z',
      },
      {
        id: 4,
        role: 'assistant',
        content: 'I\'d be happy to help you understand the user guide! This appears to be a text document containing instructions and guidelines. Please ask me specific questions about any part of the guide, and I\'ll provide detailed explanations based on the content.',
        created_at: '2024-01-16T14:35:30Z',
      },
    ],
    created_at: '2024-01-16T14:30:00Z',
    updated_at: '2024-01-16T14:35:30Z',
  },
]

// Mock authentication tokens
const MOCK_TOKEN = 'mock-jwt-token-12345'
let currentUser: User | null = null

// Helper function to simulate API delay
const delay = (ms: number = 500) => new Promise(resolve => setTimeout(resolve, ms))

// Mock API functions
export const api = {
  register: async (payload: RegisterPayload): Promise<AuthResponse> => {
    await delay()
    const newUser: User = {
      id: Date.now(),
      username: payload.username,
      email: payload.email,
      first_name: payload.first_name,
      last_name: payload.last_name,
    }
    mockUsers.push(newUser)
    currentUser = newUser
    return {
      token: MOCK_TOKEN,
      user: newUser,
    }
  },

  login: async (payload: LoginPayload): Promise<AuthResponse> => {
    await delay()
    const user = mockUsers.find(u => u.username === payload.username)
    if (!user) {
      throw new Error('Invalid credentials')
    }
    currentUser = user
    return {
      token: MOCK_TOKEN,
      user,
    }
  },

  logout: async (token: string): Promise<void> => {
    await delay()
    if (token !== MOCK_TOKEN) {
      throw new Error('Invalid token')
    }
    currentUser = null
  },

  profile: async (token: string): Promise<User> => {
    await delay()
    if (token !== MOCK_TOKEN || !currentUser) {
      throw new Error('Invalid token')
    }
    return currentUser
  },

  listDocuments: async (token: string): Promise<DocumentItem[]> => {
    await delay()
    if (token !== MOCK_TOKEN) {
      throw new Error('Invalid token')
    }
    return [...mockDocuments]
  },

  uploadDocument: async (token: string, file: File): Promise<DocumentItem> => {
    await delay(1000) // Simulate longer upload time
    if (token !== MOCK_TOKEN) {
      throw new Error('Invalid token')
    }
    const newDoc: DocumentItem = {
      id: Date.now(),
      original_name: file.name,
      file_url: `/mock/${file.name}`,
      size: file.size,
      content_type: file.type || 'application/octet-stream',
      processed: true,
      processing_error: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    mockDocuments.push(newDoc)
    return newDoc
  },

  deleteDocument: async (token: string, id: number): Promise<void> => {
    await delay()
    if (token !== MOCK_TOKEN) {
      throw new Error('Invalid token')
    }
    const index = mockDocuments.findIndex(doc => doc.id === id)
    if (index === -1) {
      throw new Error('Document not found')
    }
    mockDocuments.splice(index, 1)
  },

  listConversations: async (token: string): Promise<ConversationItem[]> => {
    await delay()
    if (token !== MOCK_TOKEN) {
      throw new Error('Invalid token')
    }
    return [...mockConversations]
  },

  retrieveConversation: async (token: string, id: number): Promise<ConversationItem> => {
    await delay()
    if (token !== MOCK_TOKEN) {
      throw new Error('Invalid token')
    }
    const conversation = mockConversations.find(conv => conv.id === id)
    if (!conversation) {
      throw new Error('Conversation not found')
    }
    return { ...conversation }
  },

  sendChat: async (token: string, payload: ChatPayload): Promise<ConversationItem> => {
    await delay(1500) // Simulate AI response time
    if (token !== MOCK_TOKEN) {
      throw new Error('Invalid token')
    }

    let conversation: ConversationItem

    if (payload.conversation_id) {
      // Continue existing conversation
      conversation = mockConversations.find(conv => conv.id === payload.conversation_id)!
      if (!conversation) {
        throw new Error('Conversation not found')
      }
      conversation = { ...conversation }
    } else {
      // Create new conversation
      const newId = Date.now()
      conversation = {
        id: newId,
        title: payload.title || `Conversation ${newId}`,
        documents: payload.document_ids
          ? mockDocuments.filter(doc => payload.document_ids!.includes(doc.id))
          : [],
        messages: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      mockConversations.push(conversation)
    }

    // Add user message
    const userMessage = {
      id: Date.now(),
      role: 'user' as const,
      content: payload.message,
      created_at: new Date().toISOString(),
    }
    conversation.messages = [...(conversation.messages || []), userMessage]

    // Generate mock AI response
    const aiResponse = generateMockResponse(payload.message, conversation.documents)
    const assistantMessage = {
      id: Date.now() + 1,
      role: 'assistant' as const,
      content: aiResponse,
      created_at: new Date().toISOString(),
    }
    conversation.messages.push(assistantMessage)

    conversation.updated_at = new Date().toISOString()

    // Update the conversation in mock storage
    const index = mockConversations.findIndex(conv => conv.id === conversation.id)
    if (index !== -1) {
      mockConversations[index] = conversation
    }

    return conversation
  },
}

// Mock response generator
function generateMockResponse(userMessage: string, documents: DocumentItem[]): string {
  const responses = [
    "I understand your question. Based on the documents available, I can provide some insights about this topic.",
    "That's an interesting question! Looking at the content, here's what I can tell you:",
    "Great question! From the information in the documents, I can explain this as follows:",
    "I see what you're asking about. Let me break this down for you based on the available content:",
    "Thanks for your question. Here's what the documents indicate about this subject:",
  ]

  const baseResponse = responses[Math.floor(Math.random() * responses.length)]

  if (documents.length > 0) {
    const docNames = documents.map(doc => doc.original_name).join(', ')
    return `${baseResponse}\n\nRegarding your question "${userMessage}", the documents (${docNames}) contain relevant information. In a real implementation, I would analyze the document content to provide specific answers. For now, this is a mock response to demonstrate the chat functionality.`
  }

  return `${baseResponse}\n\nYour question "${userMessage}" is noted. In a real implementation, I would process this through an AI model to provide a meaningful response. This is currently a mock response for demonstration purposes.`
}

export type { RegisterPayload, LoginPayload, AuthResponse, ChatPayload }
