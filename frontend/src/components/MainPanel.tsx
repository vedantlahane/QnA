import React, { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ChatDisplay from "./ChatDisplay";
import InputSection from "./InputSection";
import type { ChatMessage, ConversationSummary } from "../App";
import type { UserProfile } from "../services/chatApi";

interface MainPanelProps {
  currentView: "chat" | "history";
  onViewChange: (view: "chat" | "history") => void;
  messages: ChatMessage[];
  historyConversations: ConversationSummary[];
  selectedHistoryId: string | null;
  onSelectHistory: (conversationId: string) => void;
  onSendMessage: (content: string, options?: { documentIds?: string[] }) => Promise<void> | void;
  onStartNewChat: () => void;
  isChatLoading: boolean;
  onDeleteConversation: (conversationId: string) => Promise<void> | void;
  inputSessionKey: string;
  isAuthenticated: boolean;
  currentUser: UserProfile | null;
  onOpenAuthModal: (mode: 'signin' | 'signup') => void;
  onSignOut: () => Promise<void> | void;
  onOpenDatabaseSettings: () => void;
  databaseSummary: string;
}

const MainPanel: React.FC<MainPanelProps> = ({
  currentView,
  onViewChange,
  messages,
  historyConversations,
  selectedHistoryId,
  onSelectHistory,
  onSendMessage,
  onStartNewChat,
  isChatLoading,
  onDeleteConversation,
  inputSessionKey,
  isAuthenticated,
  currentUser,
  onOpenAuthModal,
  onSignOut,
  onOpenDatabaseSettings,
  databaseSummary,
}) => {
  const [showSettingsMenu, setShowSettingsMenu] = useState(false);
  const settingsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!showSettingsMenu) return;
    const handleClick = (event: MouseEvent) => {
      if (!settingsRef.current) return;
      if (settingsRef.current.contains(event.target as Node)) return;
      setShowSettingsMenu(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showSettingsMenu]);

  const selectedHistory = useMemo(
    () =>
      historyConversations.find(
        (conversation) => conversation.id === selectedHistoryId
      ) ?? null,
    [historyConversations, selectedHistoryId]
  );

  const subtitle = useMemo(() => {
    if (isChatLoading) {
      return "   •   Axon is thinking…";
    }
    if (selectedHistory) {
      return `   •   Resuming "${selectedHistory.title}"`;
    }
    if (messages.length > 0) {
      return "   •   Continuing your current conversation";
    }
    return "   •   Start a new conversation or revisit one from history";
  }, [isChatLoading, messages.length, selectedHistory]);

  const showLanding = currentView === "chat" && messages.length === 0;

  const handleBack = () => {
    onStartNewChat();
  };

  return (
    <div className="flex flex-1 flex-col dark:bg-[radial-gradient(ellipse_at_top,_rgba(0,100,100,0.25),_transparent_65%)] bg-[radial-gradient(ellipse_at_top,_rgba(30,45,85,0.25),_transparent_65%)]">
      <div className="px-8 pt-4">
        <div className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-4 rounded-3xl  backdrop-blur-xl">
          <motion.button
            type="button"
            onClick={handleBack}
            className={`group/back flex items-center gap-2 rounded-full  text-sm font-medium text-white/70 transition ${
              showLanding
                ? "opacity-60 hover:opacity-100"
                : "hover:bg-white/10 hover:text-white"
            }`}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            <span
              className="grid h-9 w-9 place-items-center rounded-full bg-white/10 text-white"
              aria-hidden
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </span>
            <span className="max-w-0 overflow-hidden text-xs uppercase tracking-[0.25em] text-white/60 opacity-0 transition-all duration-300 group-hover/back:max-w-[80px] group-hover/back:opacity-100">
              Back
            </span>
          </motion.button>

            <div className="flex justify-center items-center text-center">
            <span className="text-sm font-semibold uppercase tracking-[0.3em] text-white/50">
              Axon Copilot
            </span>
            
            <span className="text-sm text-white/60">{subtitle}</span>
            </div>

          <div className="relative" ref={settingsRef}>
            <motion.button
              type="button"
              className="group/settings flex items-center gap-2 rounded-full text-sm font-medium text-white/70 transition hover:text-white"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setShowSettingsMenu((prev) => !prev)}
            >
              <span
                className="grid h-9 w-9 place-items-center rounded-full bg-white/10 text-white"
                aria-hidden
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              </span>
              <span className="max-w-0 overflow-hidden text-xs uppercase tracking-[0.25em] text-white/60 opacity-0 transition-all duration-300 group-hover/settings:max-w-[100px] group-hover/settings:opacity-100">
                Settings
              </span>
            </motion.button>

            <AnimatePresence>
              {showSettingsMenu && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.18 }}
                  className="absolute right-0 z-30 mt-3 w-56 rounded-2xl border border-white/10 bg-[#0b1220]/95 p-3 text-sm text-white/80 shadow-lg backdrop-blur"
                >
                  <p className="mb-2 text-xs uppercase tracking-[0.25em] text-white/40">Account</p>
                  {isAuthenticated ? (
                    <>
                      <div className="flex w-full flex-col gap-1 rounded-xl bg-white/5 px-3 py-2 text-left text-xs text-white/70">
                        <span className="text-[10px] uppercase text-white/40">Signed in as</span>
                        <span className="text-sm font-medium text-white">{currentUser?.name ?? currentUser?.email}</span>
                        <span className="text-xs text-white/50">{currentUser?.email}</span>
                      </div>
                      <button
                        type="button"
                        className="mt-2 flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-rose-300 transition hover:bg-rose-500/10 hover:text-rose-200"
                        onClick={() => {
                          setShowSettingsMenu(false);
                          void onSignOut();
                        }}
                      >
                        Sign out
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:bg-white/10 hover:text-white"
                        onClick={() => {
                          setShowSettingsMenu(false);
                          onOpenAuthModal('signin');
                        }}
                      >
                        Sign in
                      </button>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:bg-white/10 hover:text-white"
                        onClick={() => {
                          setShowSettingsMenu(false);
                          onOpenAuthModal('signup');
                        }}
                      >
                        Create account
                      </button>
                    </>
                  )}
                  <div className="mt-3 border-t border-white/10 pt-3">
                    <p className="mb-2 text-xs uppercase tracking-[0.25em] text-white/40">Appearance</p>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:bg-white/10 hover:text-white"
                      onClick={() => {
                        setShowSettingsMenu(false);
                        onStartNewChat();
                      }}
                    >
                      Reset workspace
                      <span className="text-[10px] uppercase text-white/40">Clear</span>
                    </button>
                    {isAuthenticated ? null : (
                      <button
                        type="button"
                        className="mt-2 flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:bg-white/10 hover:text-white"
                        onClick={() => {
                          setShowSettingsMenu(false);
                          onOpenAuthModal('signin');
                        }}
                      >
                        Unlock more
                        <span className="text-[10px] uppercase text-white/40">Sign in</span>
                      </button>
                    )}
                    <button
                      type="button"
                      className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:bg-white/10 hover:text-white"
                      onClick={() => setShowSettingsMenu(false)}
                    >
                      Theme
                      <span className="text-[10px] uppercase text-white/40">Auto</span>
                    </button>
                  </div>
                  {isAuthenticated && (
                    <div className="mt-3 border-t border-white/10 pt-3">
                      <p className="mb-2 text-xs uppercase tracking-[0.25em] text-white/40">Data</p>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:bg-white/10 hover:text-white"
                        onClick={() => {
                          setShowSettingsMenu(false);
                          onOpenDatabaseSettings();
                        }}
                      >
                        Database
                        <span className="text-[10px] uppercase text-white/40">{databaseSummary}</span>
                      </button>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <ChatDisplay
          view={currentView}
          messages={messages}
          historyConversations={historyConversations}
          selectedHistoryId={selectedHistoryId}
          onSelectHistory={onSelectHistory}
          onViewChange={onViewChange}
          onDeleteConversation={onDeleteConversation}
          isChatLoading={isChatLoading}
        />
      </div>

      <InputSection
        key={inputSessionKey}
        onSend={onSendMessage}
        isHistoryActive={currentView === "history"}
        isSending={isChatLoading}
        isAuthenticated={isAuthenticated}
        onRequireAuth={onOpenAuthModal}
        onOpenDatabaseSettings={onOpenDatabaseSettings}
        databaseSummary={databaseSummary}
      />
    </div>
  );
};

export default MainPanel;
