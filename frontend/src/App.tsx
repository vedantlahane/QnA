import React, { useMemo, useState } from 'react';
import Sidebar from './components/Sidebar';
import MainPanel from './components/MainPanel';

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
  messages: ChatMessage[];
}

const App: React.FC = () => {
  const historyConversations = useMemo<ConversationSummary[]>(
    () => [
      {
        id: 'product-launch',
        title: 'Product launch ideas',
        updatedAt: 'Sep 12, 2025',
        summary: 'Exploring creative launch angles for Axon AI.',
        messages: [
          {
            id: 'pl-1',
            sender: 'user',
            content: 'I need three compelling launch ideas for the Axon AI copilot.',
            timestamp: '2025-09-12T09:12:00Z',
          },
          {
            id: 'pl-2',
            sender: 'assistant',
            content:
              'Consider a live, streamed “build your first agent” challenge, a partner hackathon with real-world prizes, and a guided migration clinic for legacy teams.',
            timestamp: '2025-09-12T09:12:20Z',
          },
          {
            id: 'pl-3',
            sender: 'user',
            content: 'Give me three memorable taglines for the challenge.',
            timestamp: '2025-09-12T09:13:01Z',
          },
        ],
      },
      {
        id: 'financial-model',
        title: 'Financial model walkthrough',
        updatedAt: 'Aug 28, 2025',
        summary: 'Deep dive on assumptions for ARR growth and churn.',
        messages: [
          {
            id: 'fm-1',
            sender: 'user',
            content: 'Summarise the ARR growth assumptions from the spreadsheet I uploaded.',
            timestamp: '2025-08-28T14:32:00Z',
          },
          {
            id: 'fm-2',
            sender: 'assistant',
            content:
              'The model assumes 18% ARR growth QoQ driven by enterprise expansion and a 6% logo churn rate mitigated by a new success program.',
            timestamp: '2025-08-28T14:32:45Z',
          },
          {
            id: 'fm-3',
            sender: 'user',
            content: 'Does the churn assumption align with last quarter’s reality?',
            timestamp: '2025-08-28T14:33:10Z',
          },
          {
            id: 'fm-4',
            sender: 'assistant',
            content:
              'Last quarter churn was 5.4%, so the model is slightly conservative; we could tighten to 5.6% if we expect the new onboarding flow to land.',
            timestamp: '2025-08-28T14:33:40Z',
          },
        ],
      },
      {
        id: 'support-playbook',
        title: 'Support automation playbook',
        updatedAt: 'Jul 14, 2025',
        summary: 'Evaluating AI responses for Tier 1 triage scripts.',
        messages: [
          {
            id: 'sp-1',
            sender: 'user',
            content: 'Draft an escalation flow for unresolved Tier 1 tickets.',
            timestamp: '2025-07-14T11:08:00Z',
          },
          {
            id: 'sp-2',
            sender: 'assistant',
            content:
              'Begin with scripted empathy, gather context, attempt knowledge base resolution, then escalate to a human within 12 minutes if confidence < 0.4.',
            timestamp: '2025-07-14T11:08:35Z',
          },
        ],
      },
    ],
    []
  );

  const [currentView, setCurrentView] = useState<'chat' | 'history'>('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeSidebarItem, setActiveSidebarItem] = useState('chat');
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  const [currentMessages, setCurrentMessages] = useState<ChatMessage[]>([]);

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

  const handleSendMessage = (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    const timestamp = new Date().toISOString();
    setCurrentMessages((prev) => [
      ...prev,
      {
        id: `user-${timestamp}`,
        sender: 'user',
        content: trimmed,
        timestamp,
      },
    ]);
    setSelectedHistoryId(null);
  };

  const handleSelectHistoryConversation = (conversationId: string) => {
    const conversation = historyConversations.find((item) => item.id === conversationId);
    if (!conversation) return;

    setCurrentMessages(conversation.messages.map((message) => ({ ...message })));
    setSelectedHistoryId(conversationId);
    setCurrentView('chat');
    setActiveSidebarItem('chat');
  };

  const handleStartNewChat = () => {
    setCurrentMessages([]);
    setSelectedHistoryId(null);
    setCurrentView('chat');
    setActiveSidebarItem('chat');
  };

  return (
    <div className="flex h-screen text-white bg-[#030407] bg-[radial-gradient(ellipse_at_top,_rgba(25,40,85,0.35),_transparent_70%)]">
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
      />
    </div>
  );
};

export default App;
