import React, { useMemo } from "react";
import { motion } from "framer-motion";
import ChatDisplay from "./ChatDisplay";
import InputSection from "./InputSection";
import type { ChatMessage, ConversationSummary } from "../App";

interface MainPanelProps {
  currentView: "chat" | "history";
  onViewChange: (view: "chat" | "history") => void;
  messages: ChatMessage[];
  historyConversations: ConversationSummary[];
  selectedHistoryId: string | null;
  onSelectHistory: (conversationId: string) => void;
  onSendMessage: (content: string) => Promise<void> | void;
  onStartNewChat: () => void;
  isChatLoading: boolean;
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
}) => {
  const selectedHistory = useMemo(
    () =>
      historyConversations.find(
        (conversation) => conversation.id === selectedHistoryId
      ) ?? null,
    [historyConversations, selectedHistoryId]
  );

  const subtitle = useMemo(() => {
    if (selectedHistory) {
      return `   •   Resuming "${selectedHistory.title}"`;
    }
    if (messages.length > 0) {
      return "   •   Continuing your current conversation";
    }
    return "   •   Start a new conversation or revisit one from history";
  }, [messages.length, selectedHistory]);

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

          <motion.button
            type="button"
            className="group/settings flex items-center gap-2 rounded-full text-sm font-medium text-white/70 transition hover:text-white"
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
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </span>
            <span className="max-w-0 overflow-hidden text-xs uppercase tracking-[0.25em] text-white/60 opacity-0 transition-all duration-300 group-hover/settings:max-w-[100px] group-hover/settings:opacity-100">
              Settings
            </span>
          </motion.button>
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
        />
      </div>

      <InputSection
        onSend={onSendMessage}
        isHistoryActive={currentView === "history"}
        isSending={isChatLoading}
      />
    </div>
  );
};

export default MainPanel;
