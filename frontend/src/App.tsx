import React, { useCallback, useEffect, useRef, useState } from 'react';
import Sidebar from './components/Sidebar';
import MainPanel from './components/MainPanel';
import AuthModal from './components/AuthModal';
import DatabaseConnectionModal from './components/DatabaseConnectionModal';
import { type SqlSideWindowProps, type SqlQueryHistoryEntry } from './components/SqlSideWindow';
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
  runSqlQuery,
  fetchDatabaseSchema,
  requestSqlSuggestions,
  type DatabaseConnectionSettings,
  type UpdateDatabaseConnectionPayload,
  type DatabaseMode,
  type SqlQueryResult,
  type SqlSchemaPayload,
  type SqlQuerySuggestion,
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
  const [environmentFallback, setEnvironmentFallback] = useState<DatabaseConnectionSettings | null>(null);
  const [isDatabaseLoading, setIsDatabaseLoading] = useState(false);
  const [isDatabaseBusy, setIsDatabaseBusy] = useState(false);
  const [databaseFeedback, setDatabaseFeedback] = useState<{ status: 'success' | 'error'; message: string } | null>(null);
  const [isSideWindowOpen, setIsSideWindowOpen] = useState(false);
  const [sqlEditorValue, setSqlEditorValue] = useState<string>('');
  const [sqlSchema, setSqlSchema] = useState<SqlSchemaPayload | null>(null);
  const [isSchemaLoading, setIsSchemaLoading] = useState(false);
  const [isExecutingSql, setIsExecutingSql] = useState(false);
  const [sqlConsoleError, setSqlConsoleError] = useState<string | null>(null);
  const [sqlHistory, setSqlHistory] = useState<SqlQueryHistoryEntry[]>([]);
  const [sqlSuggestions, setSqlSuggestions] = useState<SqlQuerySuggestion[]>([]);
  const [sqlSuggestionAnalysis, setSqlSuggestionAnalysis] = useState<string | null>(null);
  const [isFetchingSqlSuggestions, setIsFetchingSqlSuggestions] = useState(false);
  const [sqlSuggestionsError, setSqlSuggestionsError] = useState<string | null>(null);

  const lastAssistantMessageIdRef = useRef<string | null>(null);

  const deriveErrorMessage = (error: unknown, fallback: string): string => {
    if (error instanceof Error && error.message) {
      return error.message;
    }
    return fallback;
  };

  const activeConnection = databaseSettings ?? environmentFallback;
  const canUseDatabaseTools = Boolean(activeConnection);

  const resetSqlConsoleState = (options?: { close?: boolean }) => {
    setSqlEditorValue('');
    setSqlSchema(null);
    setSqlConsoleError(null);
    setSqlHistory([]);
    setIsSchemaLoading(false);
    setIsExecutingSql(false);
    setSqlSuggestions([]);
    setSqlSuggestionAnalysis(null);
    setSqlSuggestionsError(null);
    setIsFetchingSqlSuggestions(false);
    if (options?.close) {
      setIsSideWindowOpen(false);
    }
  };

  const handleRefreshDatabaseSchema = async () => {
    if (!canUseDatabaseTools) {
      setSqlSchema(null);
      setSqlConsoleError('Configure a database connection to inspect the schema.');
      return;
    }

    setIsSchemaLoading(true);
    setSqlConsoleError(null);

    try {
      const schemaPayload = await fetchDatabaseSchema();
      setSqlSchema(schemaPayload);
    } catch (error) {
      setSqlConsoleError(deriveErrorMessage(error, 'Unable to load database schema.'));
    } finally {
      setIsSchemaLoading(false);
    }
  };

  const handleExecuteSqlQuery = async (query: string, limit = 200): Promise<SqlQueryResult> => {
    if (!canUseDatabaseTools) {
      const error = new Error('Configure a database connection before running SQL queries.');
      setSqlConsoleError(error.message);
      throw error;
    }

  setIsSideWindowOpen(true);
    setSqlEditorValue(query);
    setIsExecutingSql(true);
    setSqlConsoleError(null);

    try {
      const result = await runSqlQuery({ query, limit });

      const historyEntry: SqlQueryHistoryEntry = {
        id: `sql-${Date.now()}`,
        query,
        executedAt: new Date().toISOString(),
        type: result.type,
        rowCount: result.rowCount,
      };

      setSqlHistory((prev) => [historyEntry, ...prev].slice(0, 25));
      return result;
    } catch (error) {
      const message = deriveErrorMessage(error, 'Unable to execute SQL query.');
      setSqlConsoleError(message);
      throw new Error(message);
    } finally {
      setIsExecutingSql(false);
    }
  };

  const handleRequestSqlSuggestions = async (
    query: string,
    options?: { includeSchema?: boolean; maxSuggestions?: number },
  ): Promise<void> => {
    if (!canUseDatabaseTools) {
      const error = new Error('Configure a database connection before requesting suggestions.');
      setSqlSuggestionsError(error.message);
      throw error;
    }

    const trimmed = query.trim();
    if (!trimmed) {
      const error = new Error('Provide a SQL query to analyse.');
      setSqlSuggestionsError(error.message);
      throw error;
    }

  setIsSideWindowOpen(true);
    setSqlEditorValue(trimmed);
    setIsFetchingSqlSuggestions(true);
    setSqlSuggestionsError(null);

    try {
      const response = await requestSqlSuggestions({
        query: trimmed,
        includeSchema: options?.includeSchema ?? true,
        maxSuggestions: options?.maxSuggestions,
      });
      setSqlSuggestions(response.suggestions ?? []);
      setSqlSuggestionAnalysis(response.analysis ?? null);
    } catch (error) {
      const message = deriveErrorMessage(error, 'Unable to generate SQL suggestions.');
      setSqlSuggestionsError(message);
      throw new Error(message);
    } finally {
      setIsFetchingSqlSuggestions(false);
    }
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
    if (currentMessages.length === 0) {
      lastAssistantMessageIdRef.current = null;
      return;
    }

    const latest = currentMessages[currentMessages.length - 1];
    if (!latest || latest.id === lastAssistantMessageIdRef.current) {
      return;
    }

    lastAssistantMessageIdRef.current = latest.id;
    if (latest.sender !== 'assistant') {
      return;
    }

    const match = latest.content.match(/```sql\s*([\s\S]*?)```/i);
    if (match) {
      const extracted = match[1].trim();
      if (extracted) {
        setSqlEditorValue(extracted);
  setIsSideWindowOpen(true);
      }
    }
  }, [currentMessages]);

  useEffect(() => {
    if (!currentUser) {
      setDatabaseSettings(null);
      setDatabaseModes([]);
      setEnvironmentFallback(null);
      setIsDatabaseLoading(false);
      return;
    }

    setIsDatabaseLoading(true);
    (async () => {
      try {
        const result = await fetchDatabaseConnectionSettings();
        setDatabaseSettings(result.connection);
        setDatabaseModes(result.availableModes);
        setEnvironmentFallback(result.environmentFallback ?? null);
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
        setEnvironmentFallback(result.environmentFallback ?? null);
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

  const handleToggleSideWindow = () => {
    if (!currentUser) {
      openAuthModal('signin');
      return;
    }

    if (!canUseDatabaseTools) {
      handleOpenDatabaseSettings();
      return;
    }

    setSqlConsoleError(null);
    setSqlSuggestionsError(null);

    if (!isSideWindowOpen) {
      setSqlSuggestions([]);
      setSqlSuggestionAnalysis(null);
      if (!sqlSchema) {
        void handleRefreshDatabaseSchema();
      }
    }

    setIsSideWindowOpen((prev) => !prev);
  };

  const handleCollapseSideWindow = () => {
    setIsSideWindowOpen(false);
    setSqlConsoleError(null);
    setSqlSuggestionsError(null);
  };

  const handleSaveDatabaseSettings = async (payload: UpdateDatabaseConnectionPayload) => {
    setIsDatabaseBusy(true);
    setDatabaseFeedback(null);

    try {
      const result = await updateDatabaseConnectionSettings(payload);
      setDatabaseSettings(result.connection);
      setDatabaseModes(result.availableModes);
      setEnvironmentFallback(result.environmentFallback ?? null);
      resetSqlConsoleState();
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

  const handleDisconnectDatabase = async () => {
    setIsDatabaseBusy(true);
    setDatabaseFeedback(null);

    try {
      const result = await clearDatabaseConnectionSettings();
      setDatabaseSettings(result.connection);
      setDatabaseModes(result.availableModes);
      setEnvironmentFallback(result.environmentFallback ?? null);
      resetSqlConsoleState({ close: true });
      setDatabaseFeedback({
        status: 'success',
        message: 'Database connection removed. Configure a new source to run SQL queries.',
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
      setEnvironmentFallback(null);
      setDatabaseFeedback(null);
      resetSqlConsoleState({ close: true });
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

  const databaseSummary = (() => {
    if (!currentUser) return 'Sign in';
    if (isDatabaseLoading) return 'Loading...';
    if (activeConnection) return activeConnection.displayName || activeConnection.label || 'Connected';
    return 'Select database';
  })();

  const sqlConnectionSummary = activeConnection
    ? activeConnection.displayName || activeConnection.label || 'Connected database'
    : 'Database not configured';

  const sideWindowProps: SqlSideWindowProps = {
    isOpen: isSideWindowOpen,
    onCollapse: handleCollapseSideWindow,
    connectionSummary: sqlConnectionSummary,
    schema: sqlSchema,
    isSchemaLoading,
    onRefreshSchema: handleRefreshDatabaseSchema,
    onExecuteQuery: handleExecuteSqlQuery,
    isExecuting: isExecutingSql,
    history: sqlHistory,
    errorMessage: sqlConsoleError,
    onRequestSuggestions: handleRequestSqlSuggestions,
    isSuggesting: isFetchingSqlSuggestions,
    suggestions: sqlSuggestions,
    suggestionsError: sqlSuggestionsError,
    suggestionAnalysis: sqlSuggestionAnalysis,
    queryText: sqlEditorValue,
    onChangeQuery: setSqlEditorValue,
  };

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
        onToggleSideWindow={handleToggleSideWindow}
        isSideWindowOpen={isSideWindowOpen}
        canUseDatabaseTools={canUseDatabaseTools}
        sideWindow={sideWindowProps}
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
        environmentFallback={environmentFallback}
        onSave={handleSaveDatabaseSettings}
        onTest={handleTestDatabaseSettings}
        onDisconnect={handleDisconnectDatabase}
        isBusy={isDatabaseBusy}
        isLoading={isDatabaseLoading}
        feedback={databaseFeedback}
      />
    </div>
  );
};

export default App;
