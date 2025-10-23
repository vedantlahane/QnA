import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import type { UserProfile } from '../services/chatApi';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  activeItem: string;
  onSelect: (itemId: string) => void;
  onStartNewChat: () => void;
  isAuthenticated: boolean;
  onRequireAuth: (mode: 'signin' | 'signup') => void;
  currentUser: UserProfile | null;
  onSignOut: () => Promise<void> | void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const baseIconProps = {
  width: 20,
  height: 20,
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggle,
  activeItem,
  onSelect,
  onStartNewChat,
  isAuthenticated,
  onRequireAuth,
  currentUser,
  onSignOut,
}) => {
  const [darkTheme, setDarkTheme] = useState(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    return localStorage.getItem('theme') !== 'light';
  });

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }

    if (darkTheme) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkTheme]);


  const navItems = useMemo<NavItem[]>(
    () => [
      {
        id: 'chat',
        label: 'Chat',
        icon: (
          <svg {...baseIconProps} viewBox="0 0 24 24" aria-hidden>
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        ),
      },
      {
        id: 'history',
        label: 'History',
        icon: (
          <svg {...baseIconProps} viewBox="0 0 24 24" aria-hidden>
            <path d="M3 3v5h5M3 8.5A9 9 0 1 0 12 3" />
          </svg>
        ),
      },
      {
        id: 'library',
        label: 'Library',
        icon: (
          <svg {...baseIconProps} viewBox="0 0 24 24" aria-hidden>
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5z" />
          </svg>
        ),
      },
      {
        id: 'notifications',
        label: 'Notifications',
        icon: (
          <svg {...baseIconProps} viewBox="0 0 24 24" aria-hidden>
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        ),
      },
    ],
    []
  );

  const navButtonClass = (isActive: boolean) =>
    [
      'group relative flex items-center rounded-xl transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]',
      collapsed ? 'justify-center px-3 py-3' : 'justify-start gap-3 px-4 py-2.5',
      isActive
        ? 'bg-gradient-blue text-white border border-white/20'
        : 'text-white/50 hover:bg-white/5 hover:text-white/80 border border-transparent',
    ].join(' ');


  return (
    <motion.aside
      className="flex flex-col overflow-hidden border-r border-white/10  backdrop-blur-xl"
      animate={{ width: collapsed ? 80 : 260 }}
      transition={{ duration: 0.3, ease: [0.22, 0.61, 0.36, 1] }}
    >
      <div className="flex items-center justify-between gap-4 px-5 pb-4 pt-5">
        {!collapsed && (
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-[#2563eb] to-[#3b82f6] text-lg font-black text-white shadow-lg">
              <svg
                              width="26"
                              height="26"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.8"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              className="text-sky-200"
                            >
                              <path d="M4 4h9l7 8-7 8H4l7-8z" />
                              <path d="M11 4 7 12l4 8" />
                            </svg>
            </div>
            <span className="text-sm font-semibold tracking-wide text-white">Axon</span>
          </motion.div>
        )}

        <motion.button
          type="button"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-white/70 transition hover:bg-white/10 hover:text-white"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onToggle}
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
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </motion.button>
      </div>

      <nav
        className={`flex flex-1 flex-col gap-1.5 overflow-y-auto pb-5 pt-2 ${
          collapsed ? 'px-3' : 'px-4'
        }`}
        aria-label="Primary navigation"
      >
        {navItems.map((item, index) => {
          const isActive = activeItem === item.id;
          return (
            <motion.button
              key={item.id}
              type="button"
              className={navButtonClass(isActive)}
              onClick={() => onSelect(item.id)}
              aria-pressed={isActive}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              whileHover={{ x: collapsed ? 0 : 2 }}
            >
              <span className="flex items-center justify-center" aria-hidden>
                {item.icon}
              </span>
              {!collapsed && (
                <motion.span
                  className="text-sm font-medium"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2, delay: 0.1 }}
                >
                  {item.label}
                </motion.span>
              )}
            </motion.button>
          );
        })}
      </nav>

      <div
        className={`flex flex-col gap-3 border-t border-white/10 pb-5 pt-4 ${collapsed ? 'px-3' : 'px-4'}`}
      >
        <motion.button
          type="button"
          onClick={() => (isAuthenticated ? onStartNewChat() : onRequireAuth('signup'))}
          className="flex h-11 items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/5 text-sm font-semibold text-white/80 transition hover:bg-white/10 hover:text-white"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <span className="grid h-6 w-6 place-items-center rounded-lg bg-[#2563eb]/20 text-white" aria-hidden>
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
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </span>
          {!collapsed && <span>New chat</span>}
        </motion.button>
        {isAuthenticated ? (
          <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-left text-white/70">
            <div className="text-xs uppercase tracking-[0.25em] text-white/40">Account</div>
            <div className="text-sm font-medium text-white">{currentUser?.name ?? currentUser?.email}</div>
            <div className="text-xs text-white/50">{currentUser?.email}</div>
            <motion.button
              type="button"
              className="flex h-9 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/10 text-xs font-semibold text-rose-300 transition hover:bg-rose-500/10 hover:text-rose-200"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                void onSignOut();
              }}
            >
              Sign out
            </motion.button>
          </div>
        ) : (
          <motion.button
            type="button"
            className="flex h-9 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onRequireAuth('signin')}
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
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
              <polyline points="10 17 15 12 10 7" />
              <line x1="15" y1="12" x2="3" y2="12" />
            </svg>
            {!collapsed && <span>Sign in</span>}
          </motion.button>
        )}
        <motion.button
          type="button"
          className="flex h-9 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setDarkTheme((prev) => !prev)}
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
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
          </svg>
          {!collapsed && <span>{darkTheme ? 'Dark theme' : 'Light theme'}</span>}
        </motion.button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;
