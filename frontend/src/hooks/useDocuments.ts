import { useCallback, useState } from 'react'
import { api } from '../api'
import type { DocumentItem } from '../types'

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadDocuments = useCallback(async (token: string) => {
    try {
      const items = await api.listDocuments(token)
      setDocuments(items)
      return items
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
      throw err
    }
  }, [])

  const uploadDocument = useCallback(async (token: string, file: File) => {
    setUploading(true)
    setError(null)
    try {
      await api.uploadDocument(token, file)
      await loadDocuments(token)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
      throw err
    } finally {
      setUploading(false)
    }
  }, [loadDocuments])

  const deleteDocument = useCallback(async (token: string, id: number) => {
    try {
      await api.deleteDocument(token, id)
      await loadDocuments(token)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
      throw err
    }
  }, [loadDocuments])

  const refreshDocuments = useCallback(async (token: string) => {
    try {
      await loadDocuments(token)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }, [loadDocuments])

  return {
    documents,
    uploading,
    error,
    loadDocuments,
    uploadDocument,
    deleteDocument,
    refreshDocuments,
  }
}