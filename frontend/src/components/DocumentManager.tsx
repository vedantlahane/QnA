import { type ChangeEvent, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

import type { DocumentItem } from '../types'

type DocumentManagerProps = {
  documents: DocumentItem[]
  selectedDocumentIds: number[]
  uploading: boolean
  onUpload: (file: File) => Promise<void>
  onToggleDocument: (id: number) => void
  onDeleteDocument?: (id: number) => Promise<void>
  onRefresh: () => void
}

const listVariants = {
  initial: { opacity: 0, y: 15 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -15 },
}

function formatSize(bytes: number): string {
  if (!bytes) return '—'
  if (bytes > 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  if (bytes > 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${bytes} B`
}

export function DocumentManager({
  documents,
  selectedDocumentIds,
  uploading,
  onUpload,
  onToggleDocument,
  onDeleteDocument,
  onRefresh,
}: DocumentManagerProps) {
  const [localError, setLocalError] = useState<string | null>(null)

  const processedCount = useMemo(() => documents.filter((doc) => doc.processed).length, [documents])

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setLocalError(null)
    if (!/(pdf|csv|sqlite|db|sql)$/i.test(file.name)) {
      setLocalError('Supported formats: PDF, CSV, SQLite, SQL dumps.')
      return
    }

    try {
      await onUpload(file)
      event.target.value = ''
    } catch (err) {
      if (err instanceof Error) {
        setLocalError(err.message)
      } else {
        setLocalError('Upload failed')
      }
    }
  }

  const handleDelete = async (id: number) => {
    if (!onDeleteDocument) return
    try {
      await onDeleteDocument(id)
    } catch (err) {
      if (err instanceof Error) {
        setLocalError(err.message)
      }
    }
  }

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-slate-500/25 bg-slate-900/70 p-6 shadow-lg shadow-slate-900/30 backdrop-blur-xl">
      <header className="flex items-center justify-between gap-4">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold text-slate-100">Documents</h3>
          <p className="text-sm text-slate-400">
            {processedCount}/{documents.length} processed
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="relative inline-flex items-center justify-center gap-2 rounded-xl border border-sky-400/40 bg-sky-500/15 px-4 py-2 text-sm font-medium text-sky-100 transition hover:border-sky-300/60 hover:text-sky-50">
            <input
              type="file"
              accept=".pdf,.csv,.sql,.sqlite,.db"
              onChange={handleUpload}
              disabled={uploading}
              className="absolute inset-0 cursor-pointer opacity-0"
            />
            <span>{uploading ? 'Uploading…' : 'Upload'}</span>
          </label>
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-500/30 bg-slate-800/60 text-lg text-slate-200 transition hover:border-sky-400/50 hover:text-sky-200"
            onClick={onRefresh}
            aria-label="Refresh documents"
          >
            ⟳
          </button>
        </div>
      </header>
      {localError && (
        <p className="rounded-lg border border-rose-400/40 bg-rose-500/15 px-4 py-2 text-sm text-rose-200">{localError}</p>
      )}
      <div className="flex flex-col gap-3">
        <AnimatePresence initial={false}>
          {documents.map((doc) => {
            const isSelected = selectedDocumentIds.includes(doc.id)
            return (
              <motion.article
                key={doc.id}
                className={`flex flex-col gap-3 rounded-2xl border border-slate-500/25 bg-slate-900/60 px-4 py-4 transition hover:border-sky-400/40 ${
                  isSelected ? 'border-sky-400/60' : ''
                }`}
                variants={listVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                layout
                transition={{ duration: 0.25, ease: 'easeOut' }}
              >
                <div className="flex items-center justify-between gap-3">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleDocument(doc.id)}
                      disabled={!doc.processed || uploading}
                      className="h-4 w-4 rounded border border-slate-500/50 text-sky-400 focus:ring-sky-400"
                    />
                    <span className="text-sm font-semibold text-slate-100">{doc.original_name}</span>
                  </label>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                      doc.processed
                        ? 'bg-emerald-500/15 text-emerald-200'
                        : 'bg-slate-500/20 text-slate-300'
                    }`}
                  >
                    {doc.processed ? 'Ready' : 'Processing'}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                  <span>{doc.content_type || 'unknown'}</span>
                  <span>{formatSize(doc.size)}</span>
                  {doc.processing_error && <span className="text-rose-300">{doc.processing_error}</span>}
                </div>
                {onDeleteDocument && (
                  <button
                    type="button"
                    className="self-start text-xs font-medium text-sky-200/90 transition hover:text-sky-100"
                    onClick={() => handleDelete(doc.id)}
                    disabled={uploading}
                  >
                    Remove
                  </button>
                )}
              </motion.article>
            )
          })}
        </AnimatePresence>
        {documents.length === 0 && <p className="text-sm text-slate-400">Upload a document to get started.</p>}
      </div>
    </section>
  )
}
