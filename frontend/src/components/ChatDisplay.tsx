import React, { useEffect, useMemo, useRef } from 'react';
import { AnimatePresence, LayoutGroup, motion } from 'framer-motion';
import type { ChatMessage, ConversationSummary } from '../App';

interface ChatDisplayProps {
  view: 'chat' | 'history';
  messages: ChatMessage[];
  historyConversations: ConversationSummary[];
  selectedHistoryId: string | null;
  onSelectHistory: (conversationId: string) => void;
  onViewChange: (view: 'chat' | 'history') => void;
}

const suggestions = [
  'What is artificial intelligence?',
  'How does machine learning work?',
  'Explain quantum computing',
  'What are the benefits of cloud computing?',
  'How do I migrate a legacy project?'
];

const formatDisplayTime = (timestamp: string) => {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const formatAttachmentSize = (size: number) => {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const ChatDisplay: React.FC<ChatDisplayProps> = ({
  view,
  messages,
  historyConversations,
  selectedHistoryId,
  onSelectHistory,
  onViewChange,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const showLanding = view === 'chat' && messages.length === 0;

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const historyEmpty = useMemo(() => historyConversations.length === 0, [historyConversations]);

  return (
    <section className="flex h-full flex-col items-center">
      <div ref={scrollRef} className="flex h-full w-full flex-col items-center overflow-y-auto px-6 pb-10 pt-6">
        <div className="flex w-full max-w-3xl flex-1 flex-col">
          <AnimatePresence mode="wait">
            {view === 'chat' && showLanding && (
              <motion.div
                key="landing"
                className="flex flex-1 flex-col items-center justify-center"
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -60 }}
                transition={{ duration: 0.55, ease: [0.22, 0.61, 0.36, 1] }}
              >
                <LayoutGroup id="landing-toggle">
                  <div className="mb-10 flex  gap-2">
                    {(['chat', 'history'] as const).map((mode) => {
                      const isActive = view === mode;
                      return (
                        <button
                          key={mode}
                          type="button"
                          onClick={() => onViewChange(mode)}
                          className={`relative flex flex-col items-center  px-2 pb-1 text-xl font-semibold transition-colors ${
                            isActive ? 'text-white' : 'text-white/60 hover:text-white/80'
                          }`}
                        >
                          <span>{mode === 'chat' ? 'Chat' : 'History'}</span>
                          {isActive && (
                            <motion.span
                              layoutId="landing-underline"
                              className="h-[2px] w-full rounded-full bg-[#2563eb]"
                              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
                              initial={false}
                            />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </LayoutGroup>
                <motion.div className="grid w-full max-w-lg place-items-center gap-8 text-center">
                  <div className="grid place-items-center gap-5">
                    <motion.div
                      className="relative"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.6, delay: 0.2 }}
                    >
                      <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-[#1e3a8a] via-[#2563eb] to-[#7dd3fc] opacity-40 blur-3xl" />
                      <div className="relative grid h-28 w-28 place-items-center rounded-[26px] border border-white/15 bg-[#0b1220]/90 shadow-[0_25px_60px_-30px_rgba(37,99,235,0.8)] backdrop-blur-sm">
                        <div className="absolute h-20 w-20 rounded-[22px] border border-[#3b82f6]/40" />
                        <motion.div
                          className="relative flex h-20 w-20 items-center justify-center rounded-[22px] bg-[conic-gradient(from_140deg,_rgba(125,211,252,0.4),_rgba(37,99,235,0.85),_rgba(14,165,233,0.4))] shadow-[0_18px_45px_-18px_rgba(14,165,233,0.9)]"
                        
                          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
                        >
                          
                          <div className="relative flex items-center gap-1 text-xl  font-semibold tracking-wide text-white">
                            <svg
                              width="26"
                              height="26"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.8"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              className="text-sky-200"
                            >
                              <path d="M4 4h9l7 8-7 8H4l7-8z" />
                              <path d="M11 4 7 12l4 8" />
                            </svg>
                            <span className="text-lg font-bold">Axon</span>
                          </div>
                        </motion.div>
                      </div>
                    </motion.div>

                    <motion.div
                      className="space-y-2"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.6, delay: 0.4 }}
                    >
                      <p className="text-2xl leading-relaxed text-white/70">Start your conversation with Axon</p>
                      <p className="text-sm text-white/45">Draft a message below or pick one of the quick ideas.</p>
                    </motion.div>
                  </div>

                  <motion.div
                    className="flex max-w-lg flex-wrap justify-center gap-2"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.6 }}
                  >
                    {suggestions.map((suggestion, index) => (
                      <motion.span
                        key={`${suggestion}-${index}`}
                        className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-white/70"
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.3, delay: 0.7 + index * 0.05 }}
                      >
                        {suggestion}
                      </motion.span>
                    ))}
                  </motion.div>
                </motion.div>
              </motion.div>
            )}

            {view === 'chat' && !showLanding && (
              <motion.div
                key="messages"
                className="flex flex-1 flex-col gap-6"
                initial={{ opacity: 0, y: 32 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 32 }}
                transition={{ duration: 0.4, ease: [0.22, 0.61, 0.36, 1] }}
              >
                {messages.map((message) => {
                  const isUser = message.sender === 'user';
                  const title = isUser ? 'You' : 'Axon';
                  const avatarClasses = isUser
                    ? 'bg-gradient-to-br from-[#2563eb] to-[#1d4ed8] text-white'
                    : 'bg-white/10 text-white';
                  const bubbleClasses = isUser
                    ? 'border border-black/40 bg-[#2563eb]/20 text-white'
                    : 'border border-black bg-white/5 text-white';
                  const hasAttachments = (message.attachments?.length ?? 0) > 0;

                  return (
                    <motion.div
                      key={message.id}
                      className="flex w-full items-start gap-4"
                      initial={{ opacity: 0, y: 24 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35, ease: [0.22, 0.61, 0.36, 1] }}
                    >
                      <div
                        className={`grid h-10 w-10 place-items-center rounded-xl border border-white/10 shadow-inner ${avatarClasses}`}
                        aria-hidden
                      >
                        {isUser ? (
                          <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <circle cx="12" cy="8" r="4" />
                            <path d="M6 20c0-3.314 2.686-6 6-6s6 2.686 6 6" />
                          </svg>
                        ) : (
                          <svg
                              width="26"
                              height="26"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.8"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              className="text-sky-200"
                            >
                              <path d="M4 4h9l7 8-7 8H4l7-8z" />
                              <path d="M11 4 7 12l4 8" />
                            </svg>
                        )}
                      </div>

                        <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-xs text-white/50">
                          <span className="font-semibold text-white">{title}</span>
                          <span className="h-1 w-1 rounded-full bg-white/30" aria-hidden />
                          <span>{formatDisplayTime(message.timestamp)}</span>
                        </div>
                        <div className={`w-fit rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-lg backdrop-blur ${bubbleClasses}`}>
                          <p className="whitespace-pre-wrap">{message.content}</p>
                          {hasAttachments && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {message.attachments!.map((attachment) => (
                                <a
                                  key={attachment.id}
                                  href={attachment.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/80 transition hover:border-white/20 hover:bg-white/10"
                                >
                                  <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="1.5"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  >
                                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                                  </svg>
                                  <span className="truncate max-w-[120px]" title={attachment.name}>
                                    {attachment.name}
                                  </span>
                                  <span className="text-white/40">
                                    {formatAttachmentSize(attachment.size)}
                                  </span>
                                </a>
                              ))}
                            </div>
                          )}
                        </div>
                        </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            )}

            {view === 'history' && (
              <motion.div
                key="history"
                className="flex flex-1 flex-col gap-4"
                initial={{ opacity: 0, y: 32 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 32 }}
                transition={{ duration: 0.4, ease: [0.22, 0.61, 0.36, 1] }}
              >
                {historyEmpty ? (
                  <div className="flex flex-1 items-center justify-center rounded-3xl border border-dashed border-white/10 bg-white/5 text-center text-white/40">
                    <p>No saved conversations yet. Your next chats will appear here.</p>
                  </div>
                ) : (
                  historyConversations.map((conversation) => {
                    const isSelected = conversation.id === selectedHistoryId;
                    return (
                      <motion.button
                        key={conversation.id}
                        type="button"
                        onClick={() => onSelectHistory(conversation.id)}
                        className={`flex w-full flex-col gap-2 rounded-2xl border px-5 py-4 text-left transition ${
                          isSelected
                            ? 'border-[#2563eb] bg-[#2563eb]/15 text-white'
                            : 'border-white/10 bg-white/5 text-white/80 hover:border-white/20 hover:bg-white/10'
                        }`}
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <h3 className="text-base font-semibold text-white">{conversation.title}</h3>
                          <span className="text-xs uppercase tracking-[0.2em] text-white/40">
                            {conversation.updatedAt}
                          </span>
                        </div>
                        <p className="text-sm text-white/60">{conversation.summary}</p>
            <div className="flex items-center gap-2 text-xs text-white/40">
              <span>{conversation.messageCount ?? conversation.messages?.length ?? 0} messages</span>
                          <span>•</span>
                          <span>Tap to reopen this chat</span>
                        </div>
                      </motion.button>
                    );
                  })
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
};

export default ChatDisplay;
