import React, { useCallback, useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import MainPanel from './components/MainPanel';
import {
  fetchConversation,
  fetchConversations,
  sendChatMessage,
  type RawConversationDetail,
  type RawConversationSummary,
  type RawMessage,
} from './services/chatApi';

export type ChatSender = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  sender: ChatSender;
  content: string;
  timestamp: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updatedAt: string;
  summary: string;
  updatedAtISO?: string;
  messageCount?: number;
  messages?: ChatMessage[];
}

const mapMessage = (raw: RawMessage): ChatMessage => ({
  id: raw.id,
  sender: raw.sender,
  content: raw.content,
  timestamp: raw.timestamp,
});

const mapSummary = (raw: RawConversationSummary): ConversationSummary => ({
  id: raw.id,
  title: raw.title || 'New chat',
  summary: raw.summary ?? '',
  updatedAt: raw.updatedAt,
  updatedAtISO: raw.updatedAtISO,
  messageCount: raw.messageCount ?? 0,
});

const sortSummaries = (items: ConversationSummary[]): ConversationSummary[] => {
  return [...items].sort((a, b) => {
    const aTime = a.updatedAtISO ? Date.parse(a.updatedAtISO) : Date.parse(a.updatedAt);
    const bTime = b.updatedAtISO ? Date.parse(b.updatedAtISO) : Date.parse(b.updatedAt);
    return bTime - aTime;
  });
};

const App: React.FC = () => {
  const [historyConversations, setHistoryConversations] = useState<ConversationSummary[]>([]);
  const [currentView, setCurrentView] = useState<'chat' | 'history'>('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeSidebarItem, setActiveSidebarItem] = useState('chat');
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  const [currentMessages, setCurrentMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState<boolean>(false);

  const refreshConversations = useCallback(async () => {
    try {
      const items = await fetchConversations();
      setHistoryConversations(sortSummaries(items.map(mapSummary)));
    } catch (error) {
      console.error('Failed to load conversations', error);
    }
  }, []);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  const handleSidebarSelect = (itemId: string) => {
    setActiveSidebarItem(itemId);
    if (itemId === 'chat' || itemId === 'history') {
      setCurrentView(itemId);
    }
  };

  const handleViewChange = (view: 'chat' | 'history') => {
    setCurrentView(view);
    setActiveSidebarItem(view);
  };

  const applyConversationUpdate = (detail: RawConversationDetail) => {
    const summary = mapSummary(detail);
    setHistoryConversations((prev) => {
      const filtered = prev.filter((item) => item.id !== summary.id);
      return sortSummaries([summary, ...filtered]);
    });
  };

  const updateMessagesFromDetail = (detail: RawConversationDetail) => {
    const mappedMessages = detail.messages.map(mapMessage);
    setCurrentMessages(mappedMessages);
    setSelectedHistoryId(detail.id);
  };

  const handleSendMessage = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    const optimisticMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setCurrentMessages((prev) => [...prev, optimisticMessage]);
    setIsChatLoading(true);

    try {
      const detail = await sendChatMessage({
        message: trimmed,
        conversationId: selectedHistoryId ?? undefined,
        title: selectedHistoryId ? undefined : trimmed,
      });

      updateMessagesFromDetail(detail);
      applyConversationUpdate(detail);
      setCurrentView('chat');
      setActiveSidebarItem('chat');
    } catch (error) {
      console.error('Failed to send chat message', error);
      const fallbackReply: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        content: 'Sorry, I could not reach the assistant just now.',
        timestamp: new Date().toISOString(),
      };
      setCurrentMessages((prev) => [...prev, fallbackReply]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleSelectHistoryConversation = async (conversationId: string) => {
    setSelectedHistoryId(conversationId);
    setCurrentView('chat');
    setActiveSidebarItem('chat');
    setIsChatLoading(true);

    try {
      const detail = await fetchConversation(conversationId);
      updateMessagesFromDetail(detail);
      applyConversationUpdate(detail);
    } catch (error) {
      console.error('Failed to load conversation detail', error);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleStartNewChat = () => {
    setCurrentMessages([]);
    setSelectedHistoryId(null);
    setCurrentView('chat');
    setActiveSidebarItem('chat');
  };

  return (
    <div className="flex h-screen text-white bg-[#030407] dark:bg-[radial-gradient(ellipse_at_top,_rgba(25,40,85,0.35),_transparent_70%)]">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeItem={activeSidebarItem}
        onSelect={handleSidebarSelect}
        onStartNewChat={handleStartNewChat}
      />
      <MainPanel
        currentView={currentView}
        onViewChange={handleViewChange}
        messages={currentMessages}
  historyConversations={historyConversations}
        selectedHistoryId={selectedHistoryId}
        onSelectHistory={handleSelectHistoryConversation}
        onSendMessage={handleSendMessage}
        onStartNewChat={handleStartNewChat}
        isChatLoading={isChatLoading}
      />
    </div>
  );
};

export default App;
