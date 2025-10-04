import React from 'react';
import { motion } from 'framer-motion';

interface HeaderProps {
  currentView: 'chat' | 'history';
  onViewChange: (view: 'chat' | 'history') => void;
}

const Header: React.FC<HeaderProps> = ({ currentView, onViewChange }) => {
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between border-b border-white/10 bg-[#0f1420]/80 backdrop-blur-xl px-6 py-4">
      <motion.h1
        className="text-lg font-semibold text-white"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        Chat with Genie
      </motion.h1>

      <div className="flex items-center gap-4">
        <div
          className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1"
          role="tablist"
          aria-label="View selector"
        >
          {(['chat', 'history'] as const).map((view) => {
            const isActive = currentView === view;
            const label = view === 'chat' ? 'Chat' : 'History';
            return (
              <motion.button
                key={view}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={`relative rounded-full px-4 py-1.5 text-xs font-medium tracking-wide transition-all duration-200 ${
                  isActive
                    ? 'bg-white/10 text-white'
                    : 'text-white/50 hover:text-white/80'
                }`}
                onClick={() => onViewChange(view)}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                {label}
              </motion.button>
            );
          })}
        </div>

        <motion.button
          className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/70 transition hover:bg-white/10 hover:text-white"
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          <span className="h-2 w-2 rounded-full bg-green-400" />
          <span className="font-medium">Ethereum</span>
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
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </motion.button>

        <motion.button
          className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 bg-white/5 text-white/70 transition hover:bg-white/10 hover:text-white"
          whileHover={{ scale: 1.05, rotate: 90 }}
          whileTap={{ scale: 0.95 }}
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
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m5.08 5.08 4.24 4.24M1 12h6m6 0h6M4.22 19.78l4.24-4.24m5.08-5.08 4.24-4.24" />
          </svg>
        </motion.button>
      </div>
    </header>
  );
};

export default Header;
