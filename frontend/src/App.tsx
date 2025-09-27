import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { gsap } from 'gsap'

import { api, type LoginPayload, type RegisterPayload } from './api'
import { AuthPanel } from './components/AuthPanel'
import { ChatWindow } from './components/ChatWindow'
import { ConversationSidebar } from './components/ConversationSidebar'
import { DocumentManager } from './components/DocumentManager'
import type { ConversationItem, DocumentItem, MessageItem, User } from './types'

const TOKEN_STORAGE_KEY = 'qna_auth_token'

function App() {
  const rootRef = useRef<HTMLDivElement | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY))
  const [user, setUser] = useState<User | null>(null)
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [activeConversation, setActiveConversation] = useState<ConversationItem | null>(null)
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([])
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authError, setAuthError] = useState<string | null>(null)
  const [authLoading, setAuthLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(false)
  const [sidebarLoading, setSidebarLoading] = useState(false)
  const [documentUploading, setDocumentUploading] = useState(false)
  const [chatSending, setChatSending] = useState(false)
  const [globalError, setGlobalError] = useState<string | null>(null)
  const activeConversationRef = useRef<ConversationItem | null>(null)

  useEffect(() => {
    activeConversationRef.current = activeConversation
  }, [activeConversation])

  useLayoutEffect(() => {
    if (!rootRef.current) return
    const ctx = gsap.context(() => {
      const tl = gsap.timeline()
      tl.from('.brand-title', { y: -30, opacity: 0, duration: 0.8, ease: 'power3.out' })
        .from('.brand-subtitle', { y: 20, opacity: 0, duration: 0.6, ease: 'power3.out' }, '-=0.4')
        .from('.hero-accent', { width: 0, duration: 1, ease: 'power2.inOut' }, '-=0.6')
    }, rootRef)
    return () => ctx.revert()
  }, [])

  const persistToken = useCallback((value: string | null) => {
    if (value) {
      localStorage.setItem(TOKEN_STORAGE_KEY, value)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
    setToken(value)
  }, [])

  const resetSession = useCallback(() => {
    setUser(null)
    setConversations([])
    setActiveConversation(null)
    setMessages([])
    setDocuments([])
    setSelectedDocumentIds([])
  }, [])

  const loadDocuments = useCallback(async (authToken: string) => {
    const items = await api.listDocuments(authToken)
    setDocuments(items)
  }, [])

  const loadConversations = useCallback(async (authToken: string, preserveActive = false) => {
    const items = await api.listConversations(authToken)
    setConversations(items)

    const currentActive = activeConversationRef.current

    if (!preserveActive || !currentActive) {
      if (items.length > 0) {
        const detail = await api.retrieveConversation(authToken, items[0].id)
        setActiveConversation(detail)
        setMessages(detail.messages ?? [])
      } else {
        setActiveConversation(null)
        setMessages([])
      }
    } else if (!items.some((item) => item.id === currentActive.id)) {
      setActiveConversation(null)
      setMessages([])
    }
  }, [])

  const loadInitialData = useCallback(
    async (authToken: string) => {
    setInitialLoading(true)
    setGlobalError(null)
    try {
      const [profile] = await Promise.all([
        api.profile(authToken),
        loadDocuments(authToken),
        loadConversations(authToken),
      ])
      setUser(profile)
    } catch (err) {
      if (err instanceof Error) {
        setGlobalError(err.message)
      } else {
        setGlobalError('Unable to load your workspace.')
      }
      persistToken(null)
      resetSession()
    } finally {
      setInitialLoading(false)
    }
    },
    [loadConversations, loadDocuments, persistToken, resetSession],
  )

  useEffect(() => {
    if (!token) {
      resetSession()
      return
    }
    loadInitialData(token)
  }, [token, loadInitialData, resetSession])

  useEffect(() => {
    setSelectedDocumentIds((prev) => prev.filter((id) => documents.some((doc) => doc.id === id && doc.processed)))
  }, [documents])

  const handleAuthSuccess = (nextToken: string, nextUser: User) => {
    persistToken(nextToken)
    setUser(nextUser)
    setAuthError(null)
  }

  const handleLogin = async (payload: LoginPayload) => {
    setAuthLoading(true)
    setAuthError(null)
    try {
      const response = await api.login(payload)
      handleAuthSuccess(response.token, response.user)
    } catch (err) {
      if (err instanceof Error) {
        setAuthError(err.message)
      } else {
        setAuthError('Login failed. Please try again.')
      }
      throw err
    } finally {
      setAuthLoading(false)
    }
  }

  const handleRegister = async (payload: RegisterPayload) => {
    setAuthLoading(true)
    setAuthError(null)
    try {
      const response = await api.register(payload)
      handleAuthSuccess(response.token, response.user)
    } catch (err) {
      if (err instanceof Error) {
        setAuthError(err.message)
      } else {
        setAuthError('Registration failed. Please try again.')
      }
      throw err
    } finally {
      setAuthLoading(false)
    }
  }

  const handleLogout = async () => {
    if (!token) {
      persistToken(null)
      resetSession()
      return
    }
    try {
      await api.logout(token)
    } catch (err) {
      console.warn('Logout error', err)
    } finally {
      persistToken(null)
      resetSession()
    }
  }

  const handleSelectConversation = useCallback(
    async (conversation: ConversationItem | null) => {
    if (!token) return
    if (!conversation) {
      setActiveConversation(null)
      setMessages([])
      setSelectedDocumentIds([])
      return
    }

    setSidebarLoading(true)
    setGlobalError(null)
    try {
      const detail = await api.retrieveConversation(token, conversation.id)
      setActiveConversation(detail)
      setMessages(detail.messages ?? [])
      setSelectedDocumentIds([])
    } catch (err) {
      if (err instanceof Error) {
        setGlobalError(err.message)
      }
    } finally {
      setSidebarLoading(false)
    }
    },
    [token],
  )

  const handleStartNewConversation = useCallback(() => {
    setActiveConversation(null)
    setMessages([])
    setSelectedDocumentIds([])
    setGlobalError(null)
  }, [])

  const handleToggleDocument = useCallback((id: number) => {
    setSelectedDocumentIds((prev) =>
      prev.includes(id) ? prev.filter((docId) => docId !== id) : [...prev, id],
    )
  }, [])

  const handleUploadDocument = useCallback(
    async (file: File) => {
    if (!token) {
      throw new Error('Please sign in to upload documents.')
    }
    setDocumentUploading(true)
    setGlobalError(null)
    try {
      await api.uploadDocument(token, file)
      await loadDocuments(token)
    } finally {
      setDocumentUploading(false)
    }
    },
    [loadDocuments, token],
  )

  const handleDeleteDocument = useCallback(
    async (id: number) => {
    if (!token) return
    try {
      await api.deleteDocument(token, id)
      await loadDocuments(token)
    } catch (err) {
      if (err instanceof Error) {
        setGlobalError(err.message)
      }
    }
    },
    [loadDocuments, token],
  )

  const refreshDocuments = useCallback(async () => {
    if (!token) return
    try {
      await loadDocuments(token)
    } catch (err) {
      if (err instanceof Error) {
        setGlobalError(err.message)
      }
    }
  }, [loadDocuments, token])

  const refreshConversations = useCallback(async () => {
    if (!token) return
    try {
      await loadConversations(token, true)
    } catch (err) {
      if (err instanceof Error) {
        setGlobalError(err.message)
      }
    }
  }, [loadConversations, token])

  const handleSendMessage = useCallback(
    async (message: string, options?: { title?: string }) => {
    if (!token) {
      throw new Error('Please sign in to chat with your documents.')
    }
    setChatSending(true)
    setGlobalError(null)
    try {
      const payload = {
        message,
        document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
        conversation_id: activeConversation?.id,
        title: options?.title,
      }
      const response = await api.sendChat(token, payload)
      setActiveConversation(response)
      setMessages(response.messages ?? [])
      setSelectedDocumentIds([])
      setConversations((prev) => {
        const exists = prev.find((item) => item.id === response.id)
        if (exists) {
          return prev.map((item) => (item.id === response.id ? { ...item, ...response } : item))
        }
        return [response, ...prev]
      })
      await loadDocuments(token)
    } catch (err) {
      if (err instanceof Error) {
        setGlobalError(err.message)
      }
      throw err
    } finally {
      setChatSending(false)
      await refreshConversations()
    }
    },
    [activeConversation, loadDocuments, refreshConversations, selectedDocumentIds, token],
  )

  const conversationMessages = useMemo(() => messages ?? [], [messages])

  const isAuthenticated = Boolean(token)

  return (
    <div
      className="relative mx-auto flex min-h-screen max-w-6xl flex-col gap-8 px-4 pb-16 pt-10 sm:px-6 lg:px-10"
      ref={rootRef}
    >
      <header className="relative flex flex-col gap-4 overflow-hidden rounded-3xl border border-sky-400/30 bg-gradient-to-br from-sky-500/20 via-blue-500/10 to-indigo-900/40 px-6 py-8 backdrop-blur-md sm:flex-row sm:items-center sm:justify-between">
        <div className="relative z-10 space-y-2">
          <h1 className="brand-title text-4xl font-bold tracking-tight text-slate-100 sm:text-5xl">Atlas Q&A</h1>
          <p className="brand-subtitle text-base text-slate-300/85 sm:text-lg">
            Animate insight from PDFs, spreadsheets, and databases.
          </p>
        </div>
        {isAuthenticated && (
          <button
            type="button"
            className="relative z-10 inline-flex items-center gap-2 self-start text-sm font-medium text-sky-200 transition hover:text-sky-100"
            onClick={handleLogout}
          >
            Sign out
          </button>
        )}
  <span className="hero-accent pointer-events-none absolute -bottom-10 right-5 h-[220px] w-[220px] rounded-full bg-hero-accent" />
      </header>

      {globalError && (
        <p className="mx-auto w-full max-w-xl rounded-xl border border-rose-400/40 bg-rose-500/15 px-4 py-3 text-center text-sm text-rose-200 sm:text-base">
          {globalError}
        </p>
      )}

      {!isAuthenticated ? (
        <div className="flex justify-center px-4 pb-24 pt-12 sm:px-0">
          <AuthPanel
            mode={authMode}
            loading={authLoading}
            error={authError}
            onToggleMode={() => setAuthMode((prev) => (prev === 'login' ? 'register' : 'login'))}
            onLogin={handleLogin}
            onRegister={handleRegister}
          />
        </div>
      ) : (
        <main className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)] lg:gap-7 xl:gap-8">
          {initialLoading ? (
            <p className="text-sm text-slate-400">Preparing your workspace…</p>
          ) : (
            <>
              <div className="flex flex-col gap-6 md:flex-row md:flex-wrap lg:flex-col">
                <ConversationSidebar
                  conversations={conversations}
                  activeConversationId={activeConversation?.id ?? null}
                  loading={sidebarLoading}
                  onSelectConversation={handleSelectConversation}
                  onStartNewConversation={handleStartNewConversation}
                />
                <DocumentManager
                  documents={documents}
                  selectedDocumentIds={selectedDocumentIds}
                  uploading={documentUploading}
                  onUpload={handleUploadDocument}
                  onToggleDocument={handleToggleDocument}
                  onDeleteDocument={handleDeleteDocument}
                  onRefresh={refreshDocuments}
                />
              </div>
              <ChatWindow
                user={user}
                conversation={activeConversation}
                messages={conversationMessages}
                selectedDocumentIds={selectedDocumentIds}
                documents={documents}
                sending={chatSending}
                onSendMessage={handleSendMessage}
              />
            </>
          )}
        </main>
      )}
    </div>
  )
}

export default App
