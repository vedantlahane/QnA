import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { gsap } from 'gsap'

import { useAuth } from './hooks/useAuth'
import { useConversations } from './hooks/useConversations'
import { useDocuments } from './hooks/useDocuments'
import { useChat } from './hooks/useChat'
import { AuthPanel } from './components/AuthPanel'
import { ChatWindow } from './components/ChatWindow'
import { ConversationSidebar } from './components/ConversationSidebar'
import { DocumentManager } from './components/DocumentManager'
import type { ConversationItem } from './types'
import type { LoginPayload, RegisterPayload } from './api'

function App() {
  const rootRef = useRef<HTMLDivElement | null>(null)

  // Custom hooks
  const auth = useAuth()
  const conversationsHook = useConversations()
  const documentsHook = useDocuments()
  const chat = useChat()

  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([])
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [initialLoading, setInitialLoading] = useState(false)
  const [sidebarLoading, setSidebarLoading] = useState(false)

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

  const loadInitialData = useCallback(
    async (authToken: string) => {
      setInitialLoading(true)
      setGlobalError(null)
      try {
        await Promise.all([
          auth.loadProfile(authToken),
          documentsHook.loadDocuments(authToken),
          conversationsHook.loadConversations(authToken),
        ])
      } catch (err) {
        if (err instanceof Error) {
          setGlobalError(err.message)
        } else {
          setGlobalError('Unable to load your workspace.')
        }
        auth.resetSession()
      } finally {
        setInitialLoading(false)
      }
    },
    [auth, documentsHook, conversationsHook],
  )

  useEffect(() => {
    if (!auth.token) {
      auth.resetSession()
      return
    }
    loadInitialData(auth.token)
  }, [auth.token, auth, loadInitialData])

  useEffect(() => {
    setSelectedDocumentIds((prev) => prev.filter((id) => documentsHook.documents.some((doc) => doc.id === id && doc.processed)))
  }, [documentsHook.documents])

  const handleAuthSuccess = useCallback(() => {
    setGlobalError(null)
  }, [])

  const handleLogin = useCallback(async (payload: LoginPayload) => {
    await auth.login(payload)
    handleAuthSuccess()
  }, [auth, handleAuthSuccess])

  const handleRegister = useCallback(async (payload: RegisterPayload) => {
    await auth.register(payload)
    handleAuthSuccess()
  }, [auth, handleAuthSuccess])

  const handleLogout = useCallback(async () => {
    await auth.logout()
  }, [auth])

  const handleSelectConversation = useCallback(
    async (conversation: ConversationItem | null) => {
      if (!auth.token) return
      if (!conversation) {
        chat.startNewConversation()
        setSelectedDocumentIds([])
        return
      }

      setSidebarLoading(true)
      setGlobalError(null)
      try {
        await chat.loadConversation(auth.token, conversation.id)
        setSelectedDocumentIds([])
      } catch (err) {
        if (err instanceof Error) {
          setGlobalError(err.message)
        }
      } finally {
        setSidebarLoading(false)
      }
    },
    [auth.token, chat],
  )

  const handleStartNewConversation = useCallback(() => {
    chat.startNewConversation()
    setSelectedDocumentIds([])
    setGlobalError(null)
  }, [chat])

  const handleToggleDocument = useCallback((id: number) => {
    setSelectedDocumentIds((prev) =>
      prev.includes(id) ? prev.filter((docId) => docId !== id) : [...prev, id],
    )
  }, [])

  const handleUploadDocument = useCallback(
    async (file: File) => {
      if (!auth.token) {
        throw new Error('Please sign in to upload documents.')
      }
      setGlobalError(null)
      try {
        await documentsHook.uploadDocument(auth.token, file)
      } catch (err) {
        if (err instanceof Error) {
          setGlobalError(err.message)
        }
      }
    },
    [auth.token, documentsHook],
  )

  const handleDeleteDocument = useCallback(
    async (id: number) => {
      if (!auth.token) return
      try {
        await documentsHook.deleteDocument(auth.token, id)
      } catch (err) {
        if (err instanceof Error) {
          setGlobalError(err.message)
        }
      }
    },
    [auth.token, documentsHook],
  )

  const refreshDocuments = useCallback(async () => {
    if (!auth.token) return
    try {
      await documentsHook.refreshDocuments(auth.token)
    } catch (err) {
      if (err instanceof Error) {
        setGlobalError(err.message)
      }
    }
  }, [auth.token, documentsHook])

  const refreshConversations = useCallback(async () => {
    if (!auth.token) return
    try {
      await conversationsHook.refreshConversations(auth.token)
    } catch (err) {
      if (err instanceof Error) {
        setGlobalError(err.message)
      }
    }
  }, [auth.token, conversationsHook])

  const handleSendMessage = useCallback(
    async (message: string, options?: { title?: string }) => {
      if (!auth.token) {
        throw new Error('Please sign in to chat with your documents.')
      }
      setGlobalError(null)
      try {
        const payload = {
          message,
          document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
          conversation_id: chat.activeConversation?.id,
          title: options?.title,
        }
        const response = await chat.sendMessage(auth.token, payload)
        conversationsHook.addConversation(response)
        setSelectedDocumentIds([])
        await refreshConversations()
      } catch (err) {
        if (err instanceof Error) {
          setGlobalError(err.message)
        }
        throw err
      }
    },
    [auth.token, selectedDocumentIds, chat, conversationsHook, refreshConversations],
  )

  const conversationMessages = useMemo(() => chat.messages ?? [], [chat.messages])

  const isAuthenticated = Boolean(auth.token)

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
            loading={auth.loading}
            error={auth.error}
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
                  conversations={conversationsHook.conversations}
                  activeConversationId={chat.activeConversation?.id ?? null}
                  loading={sidebarLoading}
                  onSelectConversation={handleSelectConversation}
                  onStartNewConversation={handleStartNewConversation}
                />
                <DocumentManager
                  documents={documentsHook.documents}
                  selectedDocumentIds={selectedDocumentIds}
                  uploading={documentsHook.uploading}
                  onUpload={handleUploadDocument}
                  onToggleDocument={handleToggleDocument}
                  onDeleteDocument={handleDeleteDocument}
                  onRefresh={refreshDocuments}
                />
              </div>
              <ChatWindow
                user={auth.user}
                conversation={chat.activeConversation}
                messages={conversationMessages}
                selectedDocumentIds={selectedDocumentIds}
                documents={documentsHook.documents}
                sending={chat.sending}
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
