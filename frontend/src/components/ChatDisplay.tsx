import React from 'react';
import { motion } from 'framer-motion';

interface ChatDisplayProps {
  view: 'chat' | 'history';
}

const suggestions = [
  ''
];

const ChatDisplay: React.FC<ChatDisplayProps> = ({ view }) => {
  const message =
    view === 'chat'
      ? 'Start your conversation with Genie'
      : 'Your conversation history will appear here';

  return (
    <section className="flex h-full flex-col items-center justify-center px-6">
      <motion.div
        className="grid max-w-md place-items-center gap-8 text-center"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 0.61, 0.36, 1] }}
      >
        <div className="grid place-items-center gap-5">
          <motion.div
            className="relative"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-[#2563eb] to-[#3b82f6] opacity-40 blur-3xl" />
            <div className="relative grid h-24 w-24 place-items-center rounded-3xl border border-white/20 bg-[#0f1420]/90 backdrop-blur-sm">
              <motion.div
                className="text-4xl font-black text-white"
                animate={{ rotate: [0, 5, -5, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              >
                ◇
              </motion.div>
            </div>
          </motion.div>

          <motion.div
            className="space-y-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <h2 className="text-xl font-semibold text-white">Chat with Genie</h2>
            <p className="text-sm leading-relaxed text-white/50">{message}</p>
          </motion.div>
        </div>

        <motion.div
          className="flex max-w-lg flex-wrap justify-center gap-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          {suggestions.map((suggestion, index) => (
            <motion.button
              key={`${suggestion}-${index}`}
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-white/70 transition hover:bg-white/10 hover:text-white"
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.7 + index * 0.05 }}
            >
              {suggestion}
            </motion.button>
          ))}
        </motion.div>
      </motion.div>
    </section>
  );
};

export default ChatDisplay;
