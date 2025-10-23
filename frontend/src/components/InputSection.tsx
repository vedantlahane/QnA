import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { deleteDocument, uploadDocument, type UploadedDocument } from '../services/chatApi';

interface FileTile {
  id: string;
  file: File;
  preview?: string;
  status: 'uploading' | 'uploaded' | 'error';
  document?: UploadedDocument;
  error?: string;
}

interface InputSectionProps {
  onSend: (message: string, options?: { documentIds?: string[] }) => Promise<void> | void;
  isHistoryActive: boolean;
  isSending?: boolean;
  isAuthenticated: boolean;
  onRequireAuth: (mode: 'signin' | 'signup') => void;
  onOpenDatabaseSettings: () => void;
  databaseSummary: string;
}

const formatFileSize = (size: number) => {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const InputSection: React.FC<InputSectionProps> = ({
  onSend,
  isHistoryActive,
  isSending = false,
  isAuthenticated,
  onRequireAuth,
  onOpenDatabaseSettings,
  databaseSummary,
}) => {
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<FileTile[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeechSupported, setIsSpeechSupported] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const previewsRef = useRef(new Map<string, string>());
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const revokePreview = useCallback((id: string) => {
    const url = previewsRef.current.get(id);
    if (url) {
      URL.revokeObjectURL(url);
      previewsRef.current.delete(id);
    }
  }, []);

  useEffect(() => {
    return () => {
      previewsRef.current.forEach((url) => URL.revokeObjectURL(url));
      previewsRef.current.clear();
      if (recognitionRef.current) {
        recognitionRef.current.onresult = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (isHistoryActive && message) {
      setMessage('');
    }
  }, [isHistoryActive, message]);

  useEffect(() => {
    if (!isHistoryActive || files.length === 0) {
      return;
    }
    files.forEach((tile) => {
      revokePreview(tile.id);
      if (tile.document) {
        void deleteDocument(tile.document.id);
      }
    });
    setFiles([]);
  }, [files, isHistoryActive, revokePreview]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const speechWindow = window as unknown as SpeechRecognitionWindow;
    const SpeechRecognitionConstructor =
      speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;

    if (!SpeechRecognitionConstructor) {
      setIsSpeechSupported(false);
      return;
    }

    const recognition = new SpeechRecognitionConstructor();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsRecording(true);
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognition.onerror = () => {
      setIsRecording(false);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcripts: string[] = [];
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result[0]?.transcript ?? '';
        if (transcript) {
          transcripts.push(transcript);
        }
      }
      if (transcripts.length > 0) {
        setMessage((prev) => `${prev} ${transcripts.join(' ')}`.trim());
      }
    };

    recognitionRef.current = recognition;
    setIsSpeechSupported(true);
  }, []);

  const uploadedFileIds = useMemo(
    () => files.filter((tile) => tile.status === 'uploaded' && tile.document).map((tile) => tile.document!.id),
    [files],
  );

  const handleSend = async () => {
    const trimmed = message.trim();
    if (!trimmed) return;
    if (isSending) return;
    if (files.some((tile) => tile.status === 'uploading')) return;
    if (!isAuthenticated) {
      onRequireAuth('signin');
      return;
    }

    const currentFiles = [...files];
    setMessage('');
    try {
      await onSend(trimmed, { documentIds: uploadedFileIds });
    } catch (error) {
      console.error('Failed to send message', error);
      setMessage(trimmed);
      return;
    } finally {
      currentFiles.forEach((tile) => revokePreview(tile.id));
      setFiles([]);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (!selectedFiles.length) {
      event.target.value = '';
      if (!isAuthenticated) {
        onRequireAuth('signup');
      }
      return;
    }

    if (!isAuthenticated) {
      event.target.value = '';
      onRequireAuth('signup');
      return;
    }

    selectedFiles.forEach((file, index) => {
      const id = `${file.name}-${Date.now()}-${index}`;
      let preview: string | undefined;
      if (file.type.startsWith('image/')) {
        preview = URL.createObjectURL(file);
        previewsRef.current.set(id, preview);
      }

      const newTile: FileTile = {
        id,
        file,
        preview,
        status: 'uploading',
      };

      setFiles((prev) => [...prev, newTile]);

      uploadDocument(file)
        .then((document) => {
          setFiles((prev) =>
            prev.map((tile) =>
              tile.id === id
                ? {
                    ...tile,
                    status: 'uploaded',
                    document,
                  }
                : tile,
            ),
          );
        })
        .catch((error) => {
          console.error('Failed to upload document', error);
          setFiles((prev) =>
            prev.map((tile) =>
              tile.id === id
                ? {
                    ...tile,
                    status: 'error',
                    error: 'Upload failed. Remove or retry.',
                  }
                : tile,
            ),
          );
        });
    });

    event.target.value = '';
  };

  const removeFile = (id: string) => {
    const tile = files.find((entry) => entry.id === id);
    revokePreview(id);
    setFiles((prev) => prev.filter((entry) => entry.id !== id));

    if (tile?.document) {
      void deleteDocument(tile.document.id);
    }
  };

  const handleVoiceCapture = () => {
    if (!isSpeechSupported || isHistoryActive || isSending || !isAuthenticated) {
      return;
    }

    const recognition = recognitionRef.current;
    if (!recognition) {
      return;
    }

    if (isRecording) {
      recognition.stop();
    } else {
      try {
        recognition.start();
      } catch (error) {
        console.error('Speech recognition error', error);
      }
    }
  };

  const handleUploadTrigger = () => {
    if (isHistoryActive) return;
    if (!isAuthenticated) {
      onRequireAuth('signup');
      return;
    }
    fileInputRef.current?.click();
  };

  const handleDatabaseConfig = () => {
    if (isHistoryActive) return;
    if (!isAuthenticated) {
      onRequireAuth('signin');
      return;
    }
    onOpenDatabaseSettings();
  };

  const hasUploadingFiles = files.some((tile) => tile.status === 'uploading');
  const canSend = message.trim().length > 0;
  const voiceButtonDisabled = isHistoryActive || isSending || !isSpeechSupported || !isAuthenticated;
  const isSendDisabled =
    isHistoryActive || isSending || hasUploadingFiles || !canSend || !isAuthenticated;
  const databaseButtonDisabled = isHistoryActive || isSending;

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (!isSendDisabled) {
        void handleSend();
      }
    }
  };

  return (
    <footer className="sticky bottom-10 z-30 flex justify-center px-6 pb-5 pt-4 backdrop-blur-xl">
      <div className="w-full max-w-3xl">
        <AnimatePresence>
          {files.length > 0 && (
            <motion.div
              className="mb-4 flex gap-3 overflow-x-auto pb-2"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
            >
              {files.map((tile) => {
                const { id, file, preview, status, error } = tile;
                const statusLabel =
                  status === 'uploading'
                    ? 'Uploading…'
                    : status === 'uploaded'
                      ? 'Ready'
                      : error ?? 'Upload failed';
                const statusClass =
                  status === 'error'
                    ? 'text-red-400'
                    : status === 'uploading'
                      ? 'text-amber-300'
                      : 'text-emerald-300';

                return (
                  <motion.div
                  key={id}
                  className="group relative min-w-[160px] max-w-[180px] overflow-hidden rounded-xl border border-white/10 bg-white/5 p-3"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.3 }}
                  whileHover={{ scale: 1.02 }}
                >
                  <div className="relative mb-2 h-20 w-full overflow-hidden rounded-lg bg-white/5">
                    {preview ? (
                      <img src={preview} alt={file.name} className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex h-full items-center justify-center text-white/50">
                        <svg
                          width="24"
                          height="24"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                          <polyline points="13 2 13 9 20 9" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium text-white" title={file.name}>
                        {file.name}
                      </p>
                      <p className="text-[10px] text-white/50">{formatFileSize(file.size)}</p>
                      <p className={`text-[10px] ${statusClass}`}>{statusLabel}</p>
                    </div>
                    <motion.button
                      type="button"
                      className="rounded-md bg-white/10 p-1 text-white/70 hover:bg-white/20 hover:text-white"
                      onClick={() => removeFile(id)}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                    >
                      <svg
                        width="12"
                        height="12"
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
                    </motion.button>
                  </div>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-center gap-3 rounded-2xl border border-white/10  px-4 py-3 backdrop-blur-sm">
          <motion.button
            type="button"
            className={`grid h-9 w-9 place-items-center rounded-lg transition ${
              isRecording
                ? 'bg-red-500/20 text-red-400'
                : voiceButtonDisabled
                  ? 'bg-white/5 text-white/30'
                  : 'bg-white/5 text-white/70 hover:bg-white/10 hover:text-white'
            }`}
            aria-label="Voice input"
            whileHover={voiceButtonDisabled ? {} : { scale: 1.05 }}
            whileTap={voiceButtonDisabled ? {} : { scale: 0.95 }}
            onClick={handleVoiceCapture}
            animate={isRecording ? { scale: [1, 1.1, 1] } : {}}
            transition={isRecording ? { duration: 1, repeat: Infinity } : {}}
            disabled={voiceButtonDisabled}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" />
            </svg>
          </motion.button>

          <motion.button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-lg bg-white/5 text-white/70 transition hover:bg-white/10 hover:text-white"
            aria-label="Attach files"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleUploadTrigger}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </motion.button>

          <input ref={fileInputRef} type="file" multiple onChange={handleFileUpload} className="sr-only" />

          <input
            type="text"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={
              isHistoryActive
                ? 'Switch back to Chat to send a message'
                : isAuthenticated
                  ? 'Ask AXON ....'
                  : 'Sign in to start chatting'
            }
            className="flex-1 bg-transparent py-2 text-sm text-white placeholder:text-white/40 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
            onKeyDown={handleKeyDown}
            disabled={isHistoryActive || !isAuthenticated}
          />

          <motion.button
            type="button"
            className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70 transition hover:border-white/20 hover:text-white"
            aria-label="Configure database connection"
            whileHover={databaseButtonDisabled ? {} : { scale: 1.03 }}
            whileTap={databaseButtonDisabled ? {} : { scale: 0.97 }}
            onClick={handleDatabaseConfig}
            disabled={databaseButtonDisabled}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <ellipse cx="12" cy="5" rx="8" ry="3" />
              <path d="M4 5v6c0 1.66 3.58 3 8 3s8-1.34 8-3V5" />
              <path d="M4 11v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" />
            </svg>
            <span className="max-w-[120px] truncate">{databaseSummary}</span>
          </motion.button>

          <motion.button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-lg bg-[#2563eb] text-white transition hover:bg-[#3b82f6] disabled:cursor-not-allowed disabled:opacity-40"
            disabled={isSendDisabled}
            whileHover={isSendDisabled ? {} : { scale: 1.05 }}
            whileTap={isSendDisabled ? {} : { scale: 0.95 }}
            onClick={() => void handleSend()}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </motion.button>
        </div>
      </div>
    </footer>
  );
};

export default InputSection;
