import React, { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import SchemaDiagram from "./SchemaDiagram";
import type {
  SqlQueryResult,
  SqlQuerySuggestion,
  SqlSchemaPayload,
} from "../services/chatApi";

export interface SqlQueryHistoryEntry {
  id: string;
  query: string;
  executedAt: string;
  type: SqlQueryResult["type"];
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
  onRequestSuggestions: (
    query: string,
    options?: { includeSchema?: boolean; maxSuggestions?: number }
  ) => Promise<void>;
  isSuggesting: boolean;
  suggestions: SqlQuerySuggestion[];
  suggestionsError: string | null;
  suggestionAnalysis: string | null;
  queryText: string;
  onChangeQuery: (value: string) => void;
}

interface CanvasProps {
  children: React.ReactNode;
  sideWindow: SqlSideWindowProps;
}

type CanvasTab = "editor" | "results" | "schema";
type EditorPanel = "suggestions" | "history";

const DEFAULT_QUERY_LIMIT = 200;
const QUERY_LIMIT_MIN = 1;
const QUERY_LIMIT_MAX = 10000;
const CANVAS_TABS: CanvasTab[] = ["editor", "results", "schema"];

const TAB_LABELS: Record<CanvasTab, string> = {
  editor: "Editor",
  results: "Results",
  schema: "Schema",
};

const DATE_UNITS: Intl.DateTimeFormatOptions = {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
};

const formatExecutionTimestamp = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }
  return date.toLocaleString(undefined, DATE_UNITS);
};

const Canvas: React.FC<CanvasProps> = ({ children, sideWindow }) => {
  const {
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
  } = sideWindow;

  const [queryLimit, setQueryLimit] = useState<number>(DEFAULT_QUERY_LIMIT);
  const [result, setResult] = useState<SqlQueryResult | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<CanvasTab>("editor");
  const [editorPanel, setEditorPanel] = useState<EditorPanel>("suggestions");

  useEffect(() => {
    if (!isOpen) {
      setResult(null);
      setLocalError(null);
      setActiveTab("editor");
      setEditorPanel("suggestions");
      setQueryLimit(DEFAULT_QUERY_LIMIT);
      return;
    }
  }, [isOpen]);

  const handleRunQuery = useCallback(async () => {
    const trimmed = queryText.trim();
    if (!trimmed) {
      setLocalError("Provide a SQL query to run.");
      setResult(null);
      return;
    }

    setLocalError(null);

    try {
      const executionResult = await onExecuteQuery(trimmed, queryLimit);
      setResult(executionResult);
      setActiveTab("results");
    } catch (error) {
      setResult(null);
      if (error instanceof Error && error.message) {
        setLocalError(error.message);
      } else {
        setLocalError("Unable to execute SQL query.");
      }
    }
  }, [onExecuteQuery, queryLimit, queryText]);

  const handleSuggestionRequest = useCallback(async () => {
    const trimmed = queryText.trim();
    if (!trimmed) {
      setLocalError("Provide a SQL query before requesting suggestions.");
      return;
    }

    setLocalError(null);
    setEditorPanel("suggestions");
    try {
      await onRequestSuggestions(trimmed, { includeSchema: true });
    } catch (error) {
      if (error instanceof Error && error.message) {
        setLocalError(error.message);
      } else {
        setLocalError("Unable to generate SQL suggestions.");
      }
    }
  }, [onRequestSuggestions, queryText]);

  const handleHistorySelect = useCallback(
    (entry: SqlQueryHistoryEntry) => {
      onChangeQuery(entry.query);
      setEditorPanel("history");
      setActiveTab("editor");
    },
    [onChangeQuery]
  );

  const handleSuggestionSelect = useCallback(
    (suggestion: SqlQuerySuggestion) => {
      onChangeQuery(suggestion.query);
      setEditorPanel("suggestions");
      setActiveTab("editor");
    },
    [onChangeQuery]
  );

  const combinedQueryError = useMemo(
    () => localError ?? errorMessage ?? null,
    [errorMessage, localError]
  );

  const resultSummary = useMemo(() => {
    if (!result) {
      return "Run a SQL query to see results.";
    }

    const base =
      result.type === "rows"
        ? `${result.rowCount} row${result.rowCount === 1 ? "" : "s"}`
        : result.message;
    return `${base} • ${result.executionTimeMs}ms`;
  }, [result]);

  const renderResultContent = () => {
    if (!result) {
      return (
        <div className="rounded-xl border border-dashed border-white/10 bg-white/5 p-4 text-sm text-white/50">
          Run a query to view results.
        </div>
      );
    }

    if (result.type === "rows") {
      return (
        <div className="max-h-[360px] overflow-auto rounded-xl border border-white/10 bg-[#0b1220]/70">
          <table className="min-w-full border-separate border-spacing-0 text-left text-sm text-white/80">
            <thead className="sticky top-0 bg-white/10 text-[13px] uppercase tracking-wide text-white/60">
              <tr>
                {result.columns.map((column) => (
                  <th key={column} className="px-4 py-3 font-semibold">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.length === 0 ? (
                <tr>
                  <td
                    className="px-4 py-3 text-white/40"
                    colSpan={result.columns.length || 1}
                  >
                    No rows returned.
                  </td>
                </tr>
              ) : (
                result.rows.map((row, index) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <tr key={index} className="odd:bg-white/5">
                    {row.map((value, cellIndex) => (
                      <td
                        key={`${index}-${cellIndex}`}
                        className="px-4 py-3 align-top text-xs text-white/70"
                      >
                        {String(value)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      );
    }

    return (
      <div className="rounded-xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
        <p className="font-medium">Statement acknowledged</p>
        <p className="text-xs text-emerald-100/70">{result.message}</p>
        <p className="mt-2 text-xs text-emerald-100/50">
          {result.rowCount} row{result.rowCount === 1 ? "" : "s"} affected •{" "}
          {result.executionTimeMs}ms
        </p>
      </div>
    );
  };

  const renderEditorSupportingPanel = () => {
    if (editorPanel === "history") {
      return (
        <section className="flex flex-col gap-3">
          <header className="flex items-center justify-between">
            <span className="text-xs text-white/40">
              {history.length} saved
            </span>
          </header>
          {history.length === 0 ? (
            <p className="rounded-xl border border-dashed border-white/10 bg-white/5 p-4 text-sm text-white/50">
              Run queries to build your history.
            </p>
          ) : (
            <div className="flex max-h-48 flex-col gap-2 overflow-y-auto">
              {history.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => handleHistorySelect(entry)}
                  className="flex flex-col gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-left text-xs text-white/70 transition hover:border-[#2563eb]/40 hover:bg-[#1d4ed8]/10 hover:text-white"
                >
                  <span className="font-mono text-[11px] text-white/60">
                    {entry.query.slice(0, 120)}
                  </span>
                  <span className="flex items-center justify-between text-[10px] text-white/40">
                    <span>{entry.type.toUpperCase()}</span>
                    <span>{entry.rowCount} rows</span>
                    <span>{formatExecutionTimestamp(entry.executedAt)}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      );
    }

    return (
      <section className="flex flex-col gap-3">
        <header className="flex items-center justify-between">
          
          {suggestionAnalysis && (
            <span className="text-[10px] text-white/40">Updated just now</span>
          )}
        </header>
        {suggestionAnalysis && (
          <p className="rounded-xl border border-cyan-400/30 bg-cyan-500/10 p-3 text-xs text-cyan-200">
            {suggestionAnalysis}
          </p>
        )}
        {suggestionsError && (
          <div className="rounded-lg border border-rose-400/40 bg-rose-500/10 p-3 text-xs text-rose-200">
            {suggestionsError}
          </div>
        )}
        {suggestions.length === 0 ? (
          <p className="rounded-xl border border-dashed border-white/10 bg-white/5 p-4 text-sm text-white/50">
            Request suggestions to see AI-assisted improvements.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {suggestions.map((suggestion) => (
              <div
                key={suggestion.id}
                className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/70 shadow-inner"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-white/50">
                    {suggestion.title}
                  </h3>
                  <button
                    type="button"
                    onClick={() => handleSuggestionSelect(suggestion)}
                    className="rounded-lg border border-white/15 bg-white/5 px-2 py-1 text-[11px] font-semibold text-white/70 transition hover:border-[#2563eb]/40 hover:bg-[#1d4ed8]/10 hover:text-white"
                  >
                    Load query
                  </button>
                </div>
                <p className="text-xs text-white/60">{suggestion.summary}</p>
                <pre className="mt-2 overflow-x-auto rounded-lg border border-white/10 bg-[#060a18] p-3 font-mono text-[11px] text-white/70">
                  {suggestion.query}
                </pre>
                {suggestion.rationale && (
                  <p className="mt-2 text-[11px] text-cyan-200/80">
                    {suggestion.rationale}
                  </p>
                )}
                {suggestion.warnings?.length ? (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-[11px] text-amber-200/80">
                    {suggestion.warnings.map((warning, index) => (
                      // eslint-disable-next-line react/no-array-index-key
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>
    );
  };

  const renderActiveTab = () => {
    if (activeTab === "schema") {
      return (
        <section className="flex flex-col gap-3">
          <header className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-[0.3em] text-white/40">
              Schema
            </span>
            <span className="text-xs text-white/40">
              {schema
                ? schema.connection.label
                : isSchemaLoading
                ? "Loading…"
                : "Unavailable"}
            </span>
          </header>
          {isSchemaLoading ? (
            <div className="grid h-32 place-items-center rounded-xl border border-white/10 bg-white/5 text-sm text-white/60">
              Loading schema…
            </div>
          ) : (
            <SchemaDiagram schema={schema} />
          )}
        </section>
      );
    }

    if (activeTab === "results") {
      return (
        <section className="flex flex-col gap-3">
          <header className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-[0.3em] text-white/40">
              Results
            </span>
            <span className="text-xs text-white/50">{resultSummary}</span>
          </header>
          {isExecuting ? (
            <div className="grid h-32 place-items-center rounded-xl border border-white/10 bg-white/5 text-sm text-white/60">
              Running query…
            </div>
          ) : (
            renderResultContent()
          )}
        </section>
      );
    }

    return (
      <>
        <section className="flex flex-col gap-3">
          <label
            htmlFor="sql-editor"
            className="text-xs uppercase tracking-[0.3em] text-white/40"
          >
            Editor
          </label>
          <textarea
            id="sql-editor"
            value={queryText}
            onChange={(event) => onChangeQuery(event.target.value)}
            spellCheck={false}
            onKeyDown={(event) => {
              if (event.key === "Enter" && event.shiftKey) {
                event.preventDefault();
                void handleRunQuery();
              }
            }}
            className="h-36 w-full rounded-xl border border-white/10 bg-[#060a1841] p-4 font-mono text-sm text-white/80 shadow-inner focus:border-[#2563eb]/50 focus:outline-none"
            placeholder="SELECT * FROM users LIMIT 10;"
          />
          <div className="flex flex-wrap items-center gap-3 text-xs text-white/50">
            <label htmlFor="sql-limit" className="flex items-center gap-2">
              <span>Limit</span>
              <input
                id="sql-limit"
                type="number"
                min={QUERY_LIMIT_MIN}
                max={QUERY_LIMIT_MAX}
                value={queryLimit}
                onChange={(event) => {
                  const parsed = Number.parseInt(event.target.value, 10);
                  if (Number.isNaN(parsed)) {
                    setQueryLimit(DEFAULT_QUERY_LIMIT);
                    return;
                  }
                  const bounded = Math.min(
                    QUERY_LIMIT_MAX,
                    Math.max(QUERY_LIMIT_MIN, parsed)
                  );
                  setQueryLimit(bounded);
                }}
                className="w-20 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-right text-xs text-white focus:border-[#2563eb]/50 focus:outline-none"
              />
            </label>
            <span className="hidden items-center gap-1 md:flex">
              <span className="h-1 w-1 rounded-full bg-white/20" aria-hidden />
              <span>Shift + Enter to run</span>
            </span>
            <span className="hidden items-center gap-1 md:flex">
              <span className="h-1 w-1 rounded-full bg-white/20" aria-hidden />
              <span>Suggestions include schema context</span>
            </span>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void handleRunQuery()}
              disabled={isExecuting}
              className="flex items-center gap-2 rounded-lg bg-[#2563eb] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-white/40"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              {isExecuting ? "Running…" : "Run query"}
            </button>
            <button
              type="button"
              onClick={() => void handleSuggestionRequest()}
              disabled={isSuggesting}
              className="flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-white/80 transition hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:border-white/5 disabled:text-white/30"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 19c.7 0 1.37-.12 2-.34 1.86-.63 6 1.22 7 2.34-1-2.86-1.8-6.56-1.17-8.42A6 6 0 1 0 12 19Z" />
                <path d="M9 13a3 3 0 0 0 4 4" />
              </svg>
              {isSuggesting ? "Analysing…" : "Suggest improvements"}
            </button>
            <button
              type="button"
              onClick={() => void onRefreshSchema()}
              disabled={isSchemaLoading}
              className="flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-white/80 transition hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:border-white/5 disabled:text-white/30"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="1 4 1 10 7 10" />
                <polyline points="23 20 23 14 17 14" />
                <path d="M20.49 9A9 9 0 0 0 4.51 15M3.51 9A9 9 0 0 1 19.49 15" />
              </svg>
              {isSchemaLoading ? "Refreshing…" : "Refresh schema"}
            </button>
          </div>
          {combinedQueryError && (
            <div className="rounded-lg border border-rose-400/40 bg-rose-500/10 p-3 text-xs text-rose-200">
              {combinedQueryError}
            </div>
          )}
        </section>
        <div className="flex items-center gap-2">
          
          <div className="flex gap-1 rounded-lg border border-white/10 bg-white/5 p-1 text-xs text-white/60">
            <button
              type="button"
              onClick={() => setEditorPanel("suggestions")}
              className={`rounded-md px-3 py-1 transition ${
                editorPanel === "suggestions"
                  ? "bg-[#2563eb]/20 text-white"
                  : "hover:bg-white/10 hover:text-white"
              }`}
            >
              Suggestions
            </button>
            <button
              type="button"
              onClick={() => setEditorPanel("history")}
              className={`rounded-md px-3 py-1 transition ${
                editorPanel === "history"
                  ? "bg-[#2563eb]/20 text-white"
                  : "hover:bg-white/10 hover:text-white"
              }`}
            >
              History
            </button>
          </div>
        </div>
        {renderEditorSupportingPanel()}
      </>
    );
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6 lg:flex-row py-5">
      <div
        className={`flex min-w-0 flex-1 overflow-hidden transition-[flex-basis] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          isOpen ? "lg:basis-1/2 lg:max-w-[50%]" : "lg:basis-full lg:max-w-full "
        }`}
      >
        {children}
      </div>
      <AnimatePresence>
        {isOpen ? (
          <motion.aside
            key="canvas-panel"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 40 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-[28px] border-dashed border border-white/10 px-4 text-white shadow-[0_30px_80px_-35px_rgba(37,99,235,0.75)] backdrop-blur-lg lg:basis-1/2 lg:max-w-[50%]"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-1 flex-col gap-1">
                <nav className="mt-4 flex gap-2 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-white/50">
                {CANVAS_TABS.map((tab) => {
                    const isActive = activeTab === tab;
                    return (
                      <button
                        key={tab}
                        type="button"
                        onClick={() => setActiveTab(tab)}
                        className={`flex-1 rounded-lg px-3 py-2 transition ${
                          isActive
                            ? "bg-[#2563eb] text-white shadow-[0_12px_24px_-16px_rgba(37,99,235,0.9)]"
                            : "hover:bg-white/10 hover:text-white"
                        }`}
                      >
                        {TAB_LABELS[tab]}
                      </button>
                    );
                  })}
                </nav>
                <p className="text-[11px] text-white/40">{connectionSummary}</p>
              </div>
                <button
                  type="button"
                  onClick={onCollapse}
                  className="rounded-lg border border-white/10 bg-white/5 p-2 text-white/60 transition hover:bg-white/10 hover:text-white"
                  aria-label="Close SQL canvas"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>

            

            <div className=" flex-1 space-y-5 overflow-y-auto pb-6">
              {renderActiveTab()}
            </div>
          </motion.aside>
        ) : null}
      </AnimatePresence>
    </div>
  );
};

export default Canvas;
