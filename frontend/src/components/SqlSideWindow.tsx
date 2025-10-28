import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import Editor, { type OnMount } from '@monaco-editor/react';
import type * as Monaco from 'monaco-editor';
import SchemaDiagram from './SchemaDiagram';
import type { SqlQueryResult, SqlQuerySuggestion, SqlSchemaPayload } from '../services/chatApi';

export interface SqlQueryHistoryEntry {
  id: string;
  query: string;
  executedAt: string;
  type: SqlQueryResult['type'];
  rowCount: number;
}

export interface SqlSideWindowProps {
  isOpen: boolean;
  onCollapse: () => void;
  connectionSummary: string;
  schema: SqlSchemaPayload | null;
  isSchemaLoading: boolean;
  onRefreshSchema: () => Promise<void> | void;
  onExecuteQuery: (query: string, limit?: number) => Promise<SqlQueryResult>;
  isExecuting: boolean;
  history: SqlQueryHistoryEntry[];
  errorMessage: string | null;
  onRequestSuggestions: (query: string, options?: { includeSchema?: boolean; maxSuggestions?: number }) => Promise<void>;
  isSuggesting: boolean;
  suggestions: SqlQuerySuggestion[];
  suggestionsError: string | null;
  suggestionAnalysis?: string | null;
  queryText: string;
  onChangeQuery: (value: string) => void;
}

const formatTimestamp = (value: string): string => {
  try {
    const date = new Date(value);
    return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  } catch (error) {
    return value;
  }
};

const SqlSideWindow: React.FC<SqlSideWindowProps> = ({
  isOpen,
  onCollapse,
  connectionSummary,
  schema,
  isSchemaLoading,
  onRefreshSchema,
  onExecuteQuery,
  isExecuting,
  history,
  errorMessage,
  onRequestSuggestions,
  isSuggesting,
  suggestions,
  suggestionsError,
  suggestionAnalysis,
  queryText,
  onChangeQuery,
}) => {
  const [resultLimit, setResultLimit] = useState<number>(200);
  const [runError, setRunError] = useState<string | null>(null);
  const [includeSchemaInSuggestions, setIncludeSchemaInSuggestions] = useState(true);
  const [showSchema, setShowSchema] = useState(false);
  const completionProviderRef = useRef<Monaco.IDisposable | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setRunError(null);
      setShowSchema(false);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || queryText.trim()) {
      return;
    }
    const firstTable = schema?.tables?.[0]?.name;
    if (firstTable) {
      onChangeQuery(`SELECT * FROM ${firstTable} LIMIT 10;`);
    }
  }, [isOpen, onChangeQuery, queryText, schema]);

  useEffect(() => {
    return () => {
      if (completionProviderRef.current) {
        completionProviderRef.current.dispose();
        completionProviderRef.current = null;
      }
    };
  }, []);

  const validationHint = useMemo(() => {
    const trimmed = queryText.trim();
    if (!trimmed) {
      return 'Query editor is empty.';
    }
    if (!trimmed.endsWith(';')) {
      return 'Consider terminating statements with a semicolon for clarity.';
    }
    const dangerKeywords = ['drop table', 'truncate', 'delete from'];
    const lowered = trimmed.toLowerCase();
    if (dangerKeywords.some((keyword) => lowered.startsWith(keyword))) {
      return 'This statement mutates data. Double-check before running.';
    }
    return null;
  }, [queryText]);

  const recentHistory = useMemo(() => history.slice(0, 8), [history]);

  const handleRunQuery = async () => {
    const trimmed = queryText.trim();
    if (!trimmed || isExecuting) {
      return;
    }
    setRunError(null);
    try {
      await onExecuteQuery(trimmed, resultLimit);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to execute SQL query.';
      setRunError(message);
    }
  };

  const handleEditorMount: OnMount = (editorInstance, monacoInstance) => {
    if (completionProviderRef.current) {
      completionProviderRef.current.dispose();
    }

    completionProviderRef.current = monacoInstance.languages.registerCompletionItemProvider('sql', {
      triggerCharacters: [' ', '.'],
      provideCompletionItems: (model, position) => {
        const wordUntil = model.getWordUntilPosition(position);
        const range = new monacoInstance.Range(
          position.lineNumber,
          wordUntil.startColumn,
          position.lineNumber,
          wordUntil.endColumn,
        );

        const suggestionsList: Monaco.languages.CompletionItem[] = [];
        if (schema?.tables) {
          schema.tables.forEach((table) => {
            suggestionsList.push({
              label: table.name,
              kind: monacoInstance.languages.CompletionItemKind.Struct,
              insertText: table.name,
              detail: 'Table',
              range,
            });
            table.columns.forEach((column) => {
              suggestionsList.push({
                label: `${table.name}.${column.name}`,
                kind: monacoInstance.languages.CompletionItemKind.Field,
                insertText: `${table.name}.${column.name}`,
                detail: column.type,
                range,
              });
            });
          });
        }
        return { suggestions: suggestionsList };
      },
    });

    editorInstance.onDidDispose(() => {
      if (completionProviderRef.current) {
        completionProviderRef.current.dispose();
        completionProviderRef.current = null;
      }
    });
  };

  const containerClasses = [
    'relative flex h-full min-h-0 min-w-0 flex-col overflow-hidden backdrop-blur-xl transition-[max-width,opacity,transform] duration-300 ease-out',
    isOpen
  ? 'max-w-[45%] basis-[45%] rounded-l-3xl border-l border-white/10 bg-white/10 shadow-[0_0_40px_rgba(8,13,32,0.35)] translate-x-0 opacity-100 pointer-events-auto'
      : 'max-w-0 basis-0 border-l-0 bg-transparent shadow-none translate-x-4 opacity-0 pointer-events-none',
  ].join(' ');

  const handleToggleSchema = () => {
    const next = !showSchema;
    setShowSchema(next);
    if (next && !schema && !isSchemaLoading) {
      void onRefreshSchema();
    }
  };

  return (
    <aside className={containerClasses} aria-hidden={!isOpen}>
      <div className="flex items-center justify-between border-b border-white/10 bg-white/10 px-5 py-4">
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] uppercase tracking-[0.35em] text-white/40">SQL Side Window</span>
          <span className="text-sm font-semibold text-white/90">{connectionSummary}</span>
        </div>
        <button
          type="button"
          className="rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:border-white/40 hover:text-white"
          onClick={onCollapse}
        >
          Close
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 pr-6 py-5">
        <div className="flex flex-col gap-5">
          <section className="rounded-2xl border border-white/10 bg-white/10 p-4">
            <div className="flex items-center justify-between gap-4">
              <label
                htmlFor="sql-query-editor"
                className="text-xs uppercase tracking-[0.28em] text-white/50"
              >
                Query Editor
              </label>
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.25em] text-white/50">
                <span>Limit</span>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={resultLimit}
                  onChange={(event) => {
                    const next = Number.parseInt(event.target.value, 10);
                    if (Number.isNaN(next)) {
                      setResultLimit(200);
                    } else {
                      setResultLimit(Math.min(Math.max(next, 1), 1000));
                    }
                  }}
                  className="w-20 rounded-lg border border-white/10 bg-black/40 px-2 py-1 text-right text-white focus:border-[#2563eb] focus:outline-none"
                />
              </div>
            </div>
            <div className="mt-3 overflow-hidden rounded-2xl border border-white/15">
              <Editor
                height="230px"
                language="sql"
                theme="vs-dark"
                value={queryText}
                onChange={(value: string | undefined) => onChangeQuery(value ?? '')}
                onMount={handleEditorMount}
                options={{
                  fontSize: 14,
                  minimap: { enabled: false },
                  padding: { top: 12, bottom: 12 },
                  lineNumbersMinChars: 2,
                  quickSuggestions: true,
                  scrollBeyondLastLine: false,
                }}
                path="user-sql.sql"
              />
            </div>
            {validationHint && <p className="mt-3 text-xs text-white/60">{validationHint}</p>}
          </section>

          <section className="flex flex-wrap items-center gap-3">
            <motion.button
              type="button"
              className="rounded-xl bg-[#2563eb] px-4 py-2 text-sm font-semibold text-white shadow-lg transition hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40"
              whileHover={isExecuting ? {} : { scale: 1.03 }}
              whileTap={isExecuting ? {} : { scale: 0.97 }}
              onClick={() => void handleRunQuery()}
              disabled={isExecuting || !queryText.trim()}
            >
              {isExecuting ? 'Running…' : 'Run query'}
            </motion.button>
            <button
              type="button"
              className="rounded-xl border border-white/15 px-4 py-2 text-sm text-white/70 transition hover:border-white/30 hover:text-white"
              onClick={() => {
                setRunError(null);
                onChangeQuery('');
              }}
              disabled={isExecuting}
            >
              Clear
            </button>
            <button
              type="button"
              className="rounded-xl border border-white/15 px-4 py-2 text-sm text-white/70 transition hover:border-white/30 hover:text-white"
              onClick={() => void onRequestSuggestions(queryText.trim(), { includeSchema: includeSchemaInSuggestions })}
              disabled={isSuggesting || !queryText.trim()}
            >
              {isSuggesting ? 'Analysing…' : 'Suggest' }
            </button>
            <button
              type="button"
              className="rounded-xl border border-white/15 px-4 py-2 text-sm text-white/70 transition hover:border-white/30 hover:text-white"
              onClick={handleToggleSchema}
            >
              {showSchema ? 'Hide schema' : 'Show schema'}
            </button>
            <label className="ml-auto flex items-center gap-2 text-[11px] uppercase tracking-[0.25em] text-white/50">
              <input
                type="checkbox"
                checked={includeSchemaInSuggestions}
                onChange={(event) => setIncludeSchemaInSuggestions(event.target.checked)}
                className="h-3.5 w-3.5 rounded border-white/30 bg-black/40"
              />
              Use schema context
            </label>
          </section>

          {(runError || errorMessage) && (
            <section className="rounded-2xl border border-rose-400/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {runError || errorMessage}
            </section>
          )}

          {(suggestionAnalysis || suggestions.length > 0 || suggestionsError) && (
            <section className="rounded-2xl border border-white/10 bg-white/10 p-4 text-sm text-white/80">
              <div className="mb-3 flex items-center justify-between text-xs uppercase tracking-[0.25em] text-white/50">
                <span>Suggestions</span>
                {isSuggesting ? <span className="text-[11px] text-white/50">Analysing…</span> : null}
              </div>
              {suggestionAnalysis && (
                <p className="mb-3 text-xs text-white/70">{suggestionAnalysis}</p>
              )}
              {suggestionsError && (
                <div className="mb-3 rounded-xl border border-rose-400/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                  {suggestionsError}
                </div>
              )}
              {suggestions.length > 0 ? (
                <ul className="space-y-3">
                  {suggestions.map((suggestion) => (
                    <li key={suggestion.id} className="rounded-xl border border-white/10 bg-black/30 p-3 text-xs">
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1 text-white">
                          <h4 className="text-sm font-semibold">{suggestion.title}</h4>
                          {suggestion.summary && <p className="text-white/70">{suggestion.summary}</p>}
                        </div>
                        <button
                          type="button"
                          className="rounded-lg border border-white/15 px-2.5 py-1 text-[11px] uppercase tracking-[0.25em] text-white/70 transition hover:border-white/40 hover:text-white"
                          onClick={() => onChangeQuery(suggestion.query)}
                        >
                          Apply
                        </button>
                      </div>
                      <div className="mt-2 rounded-lg bg-black/50 p-2 font-mono text-[11px] text-white/70">
                        {suggestion.query}
                      </div>
                      {suggestion.rationale && (
                        <p className="mt-2 text-[11px] text-white/60">{suggestion.rationale}</p>
                      )}
                      {suggestion.warnings && suggestion.warnings.length > 0 && (
                        <ul className="mt-2 space-y-1 text-[11px] text-amber-200">
                          {suggestion.warnings.map((warning, index) => (
                            <li key={`${suggestion.id}-warn-${index}`}>⚠️ {warning}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              ) : null}
            </section>
          )}

          {recentHistory.length > 0 && (
            <section className="rounded-2xl border border-white/10 bg-black/30 p-4 text-xs text-white/70">
              <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[0.25em] text-white/40">
                <span>Recent queries</span>
                <span>{history.length}</span>
              </div>
              <ul className="space-y-2">
                {recentHistory.map((entry) => (
                  <li key={entry.id}>
                    <button
                      type="button"
                      className="flex w-full flex-col items-start gap-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-left text-white/80 transition hover:border-white/30 hover:text-white"
                      onClick={() => onChangeQuery(entry.query)}
                    >
                      <span className="font-mono text-[11px] leading-snug">{entry.query}</span>
                      <span className="inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.25em] text-white/40">
                        <span>{formatTimestamp(entry.executedAt)}</span>
                        <span>•</span>
                        <span>{entry.type === 'rows' ? `${entry.rowCount} rows` : `${entry.rowCount} affected`}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {showSchema && (
            <section className="rounded-2xl border border-white/10 bg-white/10 p-4">
              {isSchemaLoading && !schema ? (
                <p className="text-sm text-white/60">Loading schema…</p>
              ) : schema ? (
                <SchemaDiagram schema={schema} />
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-white/60">No schema information available.</p>
                  <button
                    type="button"
                    className="rounded-xl border border-white/15 px-3 py-2 text-xs text-white/70 transition hover:border-white/30 hover:text-white"
                    onClick={() => void onRefreshSchema()}
                    disabled={isSchemaLoading}
                  >
                    {isSchemaLoading ? 'Refreshing…' : 'Refresh schema'}
                  </button>
                </div>
              )}
            </section>
          )}
        </div>
      </div>
    </aside>
  );
};

export default SqlSideWindow;
