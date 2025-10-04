import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

interface FileTile {
  id: string;
  file: File;
  preview?: string;
}

interface InputSectionProps {
  onSend: (message: string) => void;
  isHistoryActive: boolean;
}

const formatFileSize = (size: number) => {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const InputSection: React.FC<InputSectionProps> = ({ onSend, isHistoryActive }) => {
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<FileTile[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const previewsRef = useRef(new Map<string, string>());

  useEffect(() => {
    return () => {
      previewsRef.current.forEach((url) => URL.revokeObjectURL(url));
      previewsRef.current.clear();
    };
  }, []);

  useEffect(() => {
    if (isHistoryActive && message) {
      setMessage('');
    }
  }, [isHistoryActive, message]);

  const revokePreview = useCallback((id: string) => {
    const url = previewsRef.current.get(id);
    if (url) {
      URL.revokeObjectURL(url);
      previewsRef.current.delete(id);
    }
  }, []);

  useEffect(() => {
    if (!isHistoryActive || files.length === 0) return;
    files.forEach(({ id }) => revokePreview(id));
    setFiles([]);
  }, [files, isHistoryActive, revokePreview]);

  const handleSend = () => {
    const trimmed = message.trim();
    if (!trimmed && files.length === 0) return;
    onSend(trimmed);
    setMessage('');
    files.forEach(({ id }) => revokePreview(id));
    setFiles([]);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (!selectedFiles.length) return;

    const enriched = selectedFiles.map((file, index) => {
      const id = `${file.name}-${Date.now()}-${index}`;
      let preview: string | undefined;
      if (file.type.startsWith('image/')) {
        preview = URL.createObjectURL(file);
        previewsRef.current.set(id, preview);
      }
      return { id, file, preview };
    });

    setFiles((prev) => [...prev, ...enriched]);
  };

  const removeFile = (id: string) => {
    revokePreview(id);
    setFiles((prev) => prev.filter((tile) => tile.id !== id));
  };

  const handleVoiceCapture = () => {
    setIsRecording((prev) => !prev);
  };

  const handleUploadTrigger = () => {
    fileInputRef.current?.click();
  };

  const isSendDisabled = (!message.trim() && files.length === 0) || isHistoryActive;

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (!isSendDisabled) {
        handleSend();
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
              {files.map(({ id, file, preview }) => (
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
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
          <motion.button
            type="button"
            className={`grid h-9 w-9 place-items-center rounded-lg transition ${
              isRecording
                ? 'bg-red-500/20 text-red-400'
                : 'bg-white/5 text-white/70 hover:bg-white/10 hover:text-white'
            }`}
            aria-label="Voice input"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleVoiceCapture}
            animate={isRecording ? { scale: [1, 1.1, 1] } : {}}
            transition={isRecording ? { duration: 1, repeat: Infinity } : {}}
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
              isHistoryActive ? 'Switch back to Chat to send a message' : 'Ask AXON ....'
            }
            className="flex-1 bg-transparent py-2 text-sm text-white placeholder:text-white/40 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
            onKeyDown={handleKeyDown}
            disabled={isHistoryActive}
          />

          <motion.button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-lg bg-[#2563eb] text-white transition hover:bg-[#3b82f6] disabled:cursor-not-allowed disabled:opacity-40"
            disabled={isSendDisabled}
            whileHover={isSendDisabled ? {} : { scale: 1.05 }}
            whileTap={isSendDisabled ? {} : { scale: 0.95 }}
            onClick={handleSend}
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
