import React, { useCallback, useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import MainPanel from './components/MainPanel';
import AuthModal from './components/AuthModal';
import DatabaseConnectionModal from './components/DatabaseConnectionModal';
import {
  fetchConversation,
  fetchConversations,
  sendChatMessage,
  deleteConversation,
  type RawConversationDetail,
  type RawConversationSummary,
  type RawMessage,
  type RawAttachment,
  getCurrentUser,
  signIn,
  signOut,
  signUp,
  requestPasswordReset,
  confirmPasswordReset,
  type UserProfile,
  fetchDatabaseConnectionSettings,
  updateDatabaseConnectionSettings,
  clearDatabaseConnectionSettings,
  testDatabaseConnectionSettings,
  type DatabaseConnectionSettings,
  type UpdateDatabaseConnectionPayload,
  type DatabaseMode,
} from './services/chatApi';

export type ChatSender = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  sender: ChatSender;
  content: string;
  timestamp: string;
  attachments?: RawAttachment[];
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
  attachments: raw.attachments ?? [],
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
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [currentMessages, setCurrentMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState<boolean>(false);
  const [inputSessionKey, setInputSessionKey] = useState<string>(() => `new-${Date.now()}`);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [authModalState, setAuthModalState] = useState<{ open: boolean; mode: 'signin' | 'signup' }>({
    open: false,
    mode: 'signin',
  });
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccessMessage, setAuthSuccessMessage] = useState<string | null>(null);
  const [databaseModalOpen, setDatabaseModalOpen] = useState(false);
  const [databaseSettings, setDatabaseSettings] = useState<DatabaseConnectionSettings | null>(null);
  const [databaseModes, setDatabaseModes] = useState<DatabaseMode[]>([]);
  const [isDatabaseLoading, setIsDatabaseLoading] = useState(false);
  const [isDatabaseBusy, setIsDatabaseBusy] = useState(false);
  const [databaseFeedback, setDatabaseFeedback] = useState<{ status: 'success' | 'error'; message: string } | null>(null);

  const deriveErrorMessage = (error: unknown, fallback: string): string => {
    if (error instanceof Error && error.message) {
      return error.message;
    }
    return fallback;
  };

  const refreshConversations = useCallback(async () => {
    try {
      const items = await fetchConversations();
      setHistoryConversations(sortSummaries(items.map(mapSummary)));
    } catch (error) {
      console.error('Failed to load conversations', error);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const profile = await getCurrentUser();
        if (profile) {
          setCurrentUser(profile);
        }
      } catch (error) {
        console.error('Failed to determine current user', error);
      }
    })();
  }, []);

  useEffect(() => {
    if (!currentUser) {
      setHistoryConversations([]);
      return;
    }

    void refreshConversations();
  }, [currentUser, refreshConversations]);

  useEffect(() => {
    if (!currentUser) {
      setDatabaseSettings(null);
      setDatabaseModes([]);
      setIsDatabaseLoading(false);
      return;
    }

    setIsDatabaseLoading(true);
    (async () => {
      try {
        const result = await fetchDatabaseConnectionSettings();
        setDatabaseSettings(result.connection);
        setDatabaseModes(result.availableModes);
      } catch (error) {
        console.error('Failed to load database settings', error);
      } finally {
        setIsDatabaseLoading(false);
      }
    })();
  }, [currentUser]);

  const openAuthModal = (mode: 'signin' | 'signup') => {
    setAuthError(null);
    setAuthSuccessMessage(null);
    setAuthModalState({ open: true, mode });
  };

  const closeAuthModal = () => {
    setAuthModalState((prev) => ({ ...prev, open: false }));
    setAuthError(null);
    setAuthSuccessMessage(null);
  };

  const handleOpenDatabaseSettings = () => {
    if (!currentUser) {
      openAuthModal('signin');
      return;
    }

    setDatabaseFeedback(null);
    setDatabaseModalOpen(true);
    setIsDatabaseLoading(true);

    (async () => {
      try {
        const result = await fetchDatabaseConnectionSettings();
        setDatabaseSettings(result.connection);
        setDatabaseModes(result.availableModes);
      } catch (error) {
        setDatabaseFeedback({
          status: 'error',
          message: deriveErrorMessage(error, 'Unable to load database settings.'),
        });
      } finally {
        setIsDatabaseLoading(false);
      }
    })();
  };

  const handleCloseDatabaseModal = () => {
    setDatabaseModalOpen(false);
    setDatabaseFeedback(null);
  };

  const handleSaveDatabaseSettings = async (payload: UpdateDatabaseConnectionPayload) => {
    setIsDatabaseBusy(true);
    setDatabaseFeedback(null);

    try {
      const result = await updateDatabaseConnectionSettings(payload);
      setDatabaseSettings(result.connection);
      setDatabaseModes(result.availableModes);
      const successMessage = payload.testConnection
        ? 'Database connection saved and verified.'
        : 'Database connection updated.';
      setDatabaseFeedback({ status: 'success', message: successMessage });
    } catch (error) {
      setDatabaseFeedback({
        status: 'error',
        message: deriveErrorMessage(error, 'Unable to save database configuration.'),
      });
    } finally {
      setIsDatabaseBusy(false);
    }
  };

  const handleTestDatabaseSettings = async (payload: UpdateDatabaseConnectionPayload) => {
    setIsDatabaseBusy(true);
    setDatabaseFeedback(null);

    try {
      const result = await testDatabaseConnectionSettings(payload);
      setDatabaseFeedback({
        status: result.ok ? 'success' : 'error',
        message: result.message,
      });
    } catch (error) {
      setDatabaseFeedback({
        status: 'error',
        message: deriveErrorMessage(error, 'Unable to test database connection.'),
      });
    } finally {
      setIsDatabaseBusy(false);
    }
  };

  const handleResetDatabaseSettings = async () => {
    setIsDatabaseBusy(true);
    setDatabaseFeedback(null);

    try {
      const result = await clearDatabaseConnectionSettings();
      setDatabaseSettings(result.connection);
      setDatabaseModes(result.availableModes);
      setDatabaseFeedback({
        status: 'success',
        message: 'Reverted to the default database configuration.',
      });
    } catch (error) {
      setDatabaseFeedback({
        status: 'error',
        message: deriveErrorMessage(error, 'Unable to reset database configuration.'),
      });
    } finally {
      setIsDatabaseBusy(false);
    }
  };

  const handleSignIn = async (payload: { email: string; password: string }) => {
    setIsAuthSubmitting(true);
    setAuthError(null);
    setAuthSuccessMessage(null);

    try {
      const user = await signIn(payload);
      setCurrentUser(user);
      closeAuthModal();
      await refreshConversations();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to sign in.';
      setAuthError(message);
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleSignUp = async (payload: { name: string; email: string; password: string }) => {
    setIsAuthSubmitting(true);
    setAuthError(null);
    setAuthSuccessMessage(null);

    try {
      const user = await signUp(payload);
      setCurrentUser(user);
      closeAuthModal();
      await refreshConversations();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to sign up.';
      setAuthError(message);
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (error) {
      console.error('Failed to sign out', error);
    } finally {
      setCurrentUser(null);
      setHistoryConversations([]);
      handleStartNewChat();
      setDatabaseModalOpen(false);
      setDatabaseSettings(null);
      setDatabaseModes([]);
      setDatabaseFeedback(null);
    }
  };

  const handleRequestPasswordReset = async (email: string) => {
    setIsAuthSubmitting(true);
    setAuthError(null);
    setAuthSuccessMessage(null);

    try {
      const result = await requestPasswordReset(email);
      if (result.resetToken) {
        setAuthSuccessMessage('Reset code generated. Enter it below to choose a new password.');
      } else {
        setAuthSuccessMessage('If that email is registered, you will receive reset instructions soon.');
      }
      return result.resetToken ?? null;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to start password reset.';
      setAuthError(message);
      throw new Error(message);
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleConfirmPasswordReset = async (payload: { token: string; password: string }) => {
    setIsAuthSubmitting(true);
    setAuthError(null);
    setAuthSuccessMessage(null);

    try {
      const user = await confirmPasswordReset(payload);
      setCurrentUser(user);
      setAuthSuccessMessage('Password updated successfully.');
      closeAuthModal();
      await refreshConversations();
      handleStartNewChat();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to reset password.';
      setAuthError(message);
      throw new Error(message);
    } finally {
      setIsAuthSubmitting(false);
    }
  };

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
    setActiveConversationId(detail.id);
    setInputSessionKey(detail.id);
  };

  const handleSendMessage = async (
    content: string,
    options?: {
      documentIds?: string[];
    },
  ) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    if (!currentUser) {
      openAuthModal('signin');
      return;
    }

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
        conversationId: activeConversationId ?? undefined,
        title: activeConversationId ? undefined : trimmed,
        documentIds: options?.documentIds,
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
    setActiveConversationId(conversationId);
    setInputSessionKey(conversationId);
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
    setActiveConversationId(null);
    setInputSessionKey(`new-${Date.now()}`);
    setCurrentView('chat');
    setActiveSidebarItem('chat');
  };

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await deleteConversation(conversationId);
      setHistoryConversations((prev) => prev.filter((conversation) => conversation.id !== conversationId));

      if (selectedHistoryId === conversationId || activeConversationId === conversationId) {
        handleStartNewChat();
      }
    } catch (error) {
      console.error('Failed to delete conversation', error);
    }
  };

  const databaseSummary = databaseSettings
    ? databaseSettings.displayName
    : currentUser
      ? 'Default database'
      : 'Sign in';

  return (
    <div className="flex h-screen text-white bg-[#030407] dark:bg-[radial-gradient(ellipse_at_top,_rgba(25,40,85,0.35),_transparent_70%)]">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeItem={activeSidebarItem}
        onSelect={handleSidebarSelect}
        onStartNewChat={handleStartNewChat}
        isAuthenticated={Boolean(currentUser)}
        onRequireAuth={(mode: 'signin' | 'signup') => openAuthModal(mode)}
        currentUser={currentUser}
        onSignOut={handleSignOut}
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
        onDeleteConversation={handleDeleteConversation}
        inputSessionKey={inputSessionKey}
        isAuthenticated={Boolean(currentUser)}
        currentUser={currentUser}
        onOpenAuthModal={openAuthModal}
        onSignOut={handleSignOut}
        onOpenDatabaseSettings={handleOpenDatabaseSettings}
        databaseSummary={databaseSummary}
      />
      <AuthModal
        isOpen={authModalState.open}
        mode={authModalState.mode}
        onClose={closeAuthModal}
        onModeChange={(mode) => setAuthModalState({ open: true, mode })}
        onSignIn={handleSignIn}
        onSignUp={handleSignUp}
        onRequestPasswordReset={handleRequestPasswordReset}
        onConfirmPasswordReset={handleConfirmPasswordReset}
        isSubmitting={isAuthSubmitting}
        errorMessage={authError}
        successMessage={authSuccessMessage}
      />
      <DatabaseConnectionModal
        isOpen={databaseModalOpen}
        onClose={handleCloseDatabaseModal}
        config={databaseSettings}
        availableModes={databaseModes}
        onSave={handleSaveDatabaseSettings}
        onTest={handleTestDatabaseSettings}
        onReset={handleResetDatabaseSettings}
        isBusy={isDatabaseBusy}
        isLoading={isDatabaseLoading}
        feedback={databaseFeedback}
      />
    </div>
  );
};

export default App;
