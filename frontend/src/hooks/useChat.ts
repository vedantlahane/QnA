import { useCallback, useState } from 'react'
import { api, type ChatPayload } from '../api'
import type { ConversationItem, MessageItem } from '../types'

export function useChat() {
  const [activeConversation, setActiveConversation] = useState<ConversationItem | null>(null)
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadConversation = useCallback(async (token: string, conversationId: number) => {
    try {
      const detail = await api.retrieveConversation(token, conversationId)
      setActiveConversation(detail)
      setMessages(detail.messages ?? [])
      return detail
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
      throw err
    }
  }, [])

  const startNewConversation = useCallback(() => {
    setActiveConversation(null)
    setMessages([])
    setError(null)
  }, [])

  const sendMessage = useCallback(async (token: string, payload: ChatPayload) => {
    setSending(true)
    setError(null)
    try {
      const response = await api.sendChat(token, payload)
      setActiveConversation(response)
      setMessages(response.messages ?? [])
      return response
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
      throw err
    } finally {
      setSending(false)
    }
  }, [])

  return {
    activeConversation,
    messages,
    sending,
    error,
    loadConversation,
    startNewConversation,
    sendMessage,
    setActiveConversation,
    setMessages,
  }
}