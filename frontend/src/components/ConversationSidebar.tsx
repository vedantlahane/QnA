import { memo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

import type { ConversationItem } from '../types'

type ConversationSidebarProps = {
  conversations: ConversationItem[]
  activeConversationId: number | null
  loading: boolean
  onSelectConversation: (conversation: ConversationItem | null) => void
  onStartNewConversation: () => void
}

const listVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
}

function ConversationSidebarComponent({
  conversations,
  activeConversationId,
  loading,
  onSelectConversation,
  onStartNewConversation,
}: ConversationSidebarProps) {
  return (
    <aside className="flex flex-col gap-4 rounded-2xl border border-slate-500/25 bg-slate-900/70 p-6 shadow-lg shadow-slate-900/30 backdrop-blur-xl">
      <header className="flex items-center justify-between gap-4">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold text-slate-100">Conversations</h3>
          <p className="text-sm text-slate-400">Choose a thread or begin a new one</p>
        </div>
        <button
          type="button"
          className="inline-flex h-9 items-center justify-center rounded-lg bg-gradient-to-br from-sky-400 to-indigo-500 px-3 text-sm font-semibold text-slate-950 shadow-md shadow-sky-500/25 transition hover:from-sky-300 hover:to-indigo-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          onClick={onStartNewConversation}
        >
          New
        </button>
      </header>
      <div className="flex flex-col gap-3">
        {loading && <p className="text-sm text-slate-400">Loading…</p>}
        {!loading && conversations.length === 0 && <p className="text-sm text-slate-400">No conversations yet.</p>}
        <AnimatePresence initial={false}>
          {conversations.map((conversation) => (
            <motion.button
              key={conversation.id}
              className={`flex flex-col gap-1.5 rounded-2xl border border-slate-500/25 px-4 py-4 text-left text-slate-200 transition hover:border-sky-400/40 hover:text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${
                conversation.id === activeConversationId
                  ? 'border-sky-400/60 bg-sky-900/35'
                  : 'bg-slate-900/60'
              }`}
              onClick={() => onSelectConversation(conversation)}
              variants={listVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
              layout
            >
              <span className="text-sm font-semibold text-slate-100">
                {conversation.title || `Conversation ${conversation.id}`}
              </span>
              <span className="text-xs text-slate-400">
                {new Date(conversation.updated_at).toLocaleString()}
              </span>
            </motion.button>
          ))}
        </AnimatePresence>
      </div>
    </aside>
  )
}

export const ConversationSidebar = memo(ConversationSidebarComponent)
