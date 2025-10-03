import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Textarea } from './ui/Textarea'
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

  return (
    <section className="flex h-full flex-col gap-6 rounded-3xl border border-slate-500/25 bg-slate-900/80 p-8 shadow-xl shadow-slate-900/50 backdrop-blur-xl" aria-labelledby="chat-window-title">
      <header className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h3 id="chat-window-title" className="text-2xl font-semibold text-slate-100">{conversation?.title || 'New conversation'}</h3>
          <p className="text-sm text-slate-400">Ask questions about your documents or start a fresh topic.</p>
        </div>
        {user && <span className="text-sm text-slate-400">Signed in as {user.username}</span>}
      </header>
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto pr-2" aria-live="polite" aria-label="Chat messages" role="log">
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
              role="article"
              aria-label={`Message from ${message.role === 'assistant' ? 'Assistant' : 'You'}`}
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
      <form className="flex flex-col gap-5" onSubmit={handleSubmit} aria-label="Send message form">
        {isNewConversation && (
          <>
            <Input
              label="Conversation title"
              type="text"
              placeholder="Optional title"
              value={conversationTitle}
              onChange={(event) => setConversationTitle(event.currentTarget.value)}
              disabled={sending}
              aria-describedby="conversation-title-help"
            />
            <p id="conversation-title-help" className="text-xs text-slate-400">Give your conversation a descriptive title</p>
          </>
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
        <Textarea
          label="Message"
          ref={textareaRef}
          value={draft}
          placeholder={conversation ? 'Continue the thread…' : 'What would you like to learn?'}
          onChange={(event) => setDraft(event.currentTarget.value)}
          rows={3}
          disabled={sending}
          aria-describedby="message-help"
        />
        <p id="message-help" className="text-xs text-slate-400">Type your message and press Enter or click Send</p>
        <Button
          type="submit"
          disabled={sending}
          loading={sending}
          className="w-full"
        >
          {sending ? 'Sending…' : 'Send'}
        </Button>
      </form>
    </section>
  )
}
