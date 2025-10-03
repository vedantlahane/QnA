import { useCallback, useState } from 'react'
import { api } from '../api'
import type { ConversationItem } from '../types'

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadConversations = useCallback(async (token: string) => {
    setLoading(true)
    setError(null)
    try {
      const items = await api.listConversations(token)
      setConversations(items)
      return items
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshConversations = useCallback(async (token: string) => {
    try {
      await loadConversations(token)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }, [loadConversations])

  const addConversation = useCallback((conversation: ConversationItem) => {
    setConversations((prev) => {
      const exists = prev.find((item) => item.id === conversation.id)
      if (exists) {
        return prev.map((item) => (item.id === conversation.id ? { ...item, ...conversation } : item))
      }
      return [conversation, ...prev]
    })
  }, [])

  return {
    conversations,
    loading,
    error,
    loadConversations,
    refreshConversations,
    addConversation,
  }
}