import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

import type { ConversationItem, DocumentItem, MessageItem, User } from '../types'

const messageVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
}

type ChatWindowProps = {
  user: User | null
  conversation: ConversationItem | null
  messages: MessageItem[]
  selectedDocumentIds: number[]
  documents: DocumentItem[]
  sending: boolean
  onSendMessage: (message: string, options?: { title?: string }) => Promise<void>
}

export function ChatWindow({
  user,
  conversation,
  messages,
  selectedDocumentIds,
  documents,
  sending,
  onSendMessage,
}: ChatWindowProps) {
  const [draft, setDraft] = useState('')
  const [conversationTitle, setConversationTitle] = useState(conversation?.title ?? '')
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setConversationTitle(conversation?.title ?? '')
  }, [conversation?.id, conversation?.title])

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const isNewConversation = !conversation

  const attachedDocuments = useMemo(
    () => documents.filter((doc) => selectedDocumentIds.includes(doc.id)),
    [documents, selectedDocumentIds],
  )
  const conversationDocs = conversation?.documents ?? []

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!draft.trim()) {
      return
    }

    const messageToSend = draft.trim()

    try {
      await onSendMessage(messageToSend, isNewConversation ? { title: conversationTitle.trim() } : undefined)
      setDraft('')
      setTimeout(() => textareaRef.current?.focus(), 0)
    } catch {
      // Parent handles surfacing errors
    }
  }

  const inputClassName =
    'w-full rounded-xl border border-slate-500/30 bg-slate-900/70 px-4 py-3 text-base text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-400/60 focus:border-sky-300/40 disabled:cursor-not-allowed disabled:opacity-60'

  return (
    <section className="flex h-full flex-col gap-6 rounded-3xl border border-slate-500/25 bg-slate-900/80 p-8 shadow-xl shadow-slate-900/50 backdrop-blur-xl">
      <header className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h3 className="text-2xl font-semibold text-slate-100">{conversation?.title || 'New conversation'}</h3>
          <p className="text-sm text-slate-400">Ask questions about your documents or start a fresh topic.</p>
        </div>
        {user && <span className="text-sm text-slate-400">Signed in as {user.username}</span>}
      </header>
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto pr-2" aria-live="polite">
        <AnimatePresence initial={false}>
          {messages.map((message) => (
            <motion.div
              key={message.id || `${message.role}-${message.created_at}`}
              className={`${
                message.role === 'assistant'
                  ? 'self-start border border-sky-400/20 bg-slate-900/90 text-slate-100'
                  : 'self-end bg-gradient-to-br from-indigo-600/90 to-sky-500/70 text-slate-950'
              } flex max-w-3xl flex-col gap-2 rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-xl shadow-slate-900/60`}
              variants={messageVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
              transition={{ duration: 0.25, ease: 'easeOut' }}
            >
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300/80">
                {message.role === 'assistant' ? 'Assistant' : 'You'}
              </div>
              <p className="whitespace-pre-wrap">{message.content}</p>
              <time className="text-[0.65rem] text-slate-300/70">
                {new Date(message.created_at).toLocaleTimeString()}
              </time>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={endRef} />
      </div>
      <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
        {isNewConversation && (
          <label className="flex flex-col gap-2 text-sm text-slate-300">
            <span>Conversation title</span>
            <input
              type="text"
              placeholder="Optional title"
              value={conversationTitle}
              onChange={(event) => setConversationTitle(event.currentTarget.value)}
              disabled={sending}
              className={inputClassName}
            />
          </label>
        )}
        {conversationDocs.length > 0 && (
          <div className="flex flex-col gap-2 text-sm text-slate-300">
            <span className="font-medium text-slate-200">Conversation context:</span>
            <ul className="list-disc space-y-1 pl-5">
              {conversationDocs.map((doc) => (
                <li key={doc.id}>{doc.original_name}</li>
              ))}
            </ul>
          </div>
        )}
        {attachedDocuments.length > 0 && (
          <div className="flex flex-col gap-2 text-sm text-slate-300">
            <span className="font-medium text-slate-200">Attached documents:</span>
            <ul className="list-disc space-y-1 pl-5">
              {attachedDocuments.map((doc) => (
                <li key={doc.id}>{doc.original_name}</li>
              ))}
            </ul>
          </div>
        )}
        <label className="flex flex-col gap-2 text-sm text-slate-300">
          <span>Message</span>
          <textarea
            ref={textareaRef}
            value={draft}
            placeholder={conversation ? 'Continue the thread…' : 'What would you like to learn?'}
            onChange={(event) => setDraft(event.currentTarget.value)}
            rows={3}
            disabled={sending}
            className={`${inputClassName} resize-y min-h-[110px]`}
          />
        </label>
        <motion.button
          type="submit"
          className="inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-sky-400 to-indigo-500 px-5 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-sky-500/25 transition hover:from-sky-300 hover:to-indigo-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 disabled:cursor-wait disabled:opacity-60"
          whileTap={{ scale: 0.97 }}
          whileHover={{ scale: 1.03 }}
          disabled={sending}
        >
          {sending ? 'Sending…' : 'Send'}
        </motion.button>
      </form>
    </section>
  )
}
