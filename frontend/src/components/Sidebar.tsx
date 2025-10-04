import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
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

const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  const [activeItem, setActiveItem] = useState('chat');

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
        id: 'analytics',
        label: 'Analytics',
        icon: (
          <svg {...baseIconProps} viewBox="0 0 24 24" aria-hidden>
            <path d="M18 20V10M12 20V4M6 20v-6" />
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
        id: 'settings',
        label: 'Settings',
        icon: (
          <svg {...baseIconProps} viewBox="0 0 24 24" aria-hidden>
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m5.08 5.08 4.24 4.24M1 12h6m6 0h6M4.22 19.78l4.24-4.24m5.08-5.08 4.24-4.24" />
          </svg>
        ),
      },
      {
        id: 'community',
        label: 'Community',
        icon: (
          <svg {...baseIconProps} viewBox="0 0 24 24" aria-hidden>
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
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
        ? 'bg-white/10 text-white border border-white/20'
        : 'text-white/50 hover:bg-white/5 hover:text-white/80 border border-transparent',
    ].join(' ');

  return (
    <motion.aside
      className="flex flex-col overflow-hidden border-r border-white/10 bg-[#0f1420]/60 backdrop-blur-xl"
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
              ◇
            </div>
            <span className="text-sm font-semibold tracking-wide text-white">Genie</span>
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
              onClick={() => setActiveItem(item.id)}
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

      <div className="flex flex-col gap-3 border-t border-white/10 px-4 pb-5 pt-4">
        <motion.button
          type="button"
          className="flex h-9 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
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
          {!collapsed && <span>Theme</span>}
        </motion.button>

        <motion.div
          className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2"
          whileHover={{ scale: 1.02 }}
        >
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-orange-400 to-pink-500" />
          {!collapsed && (
            <motion.div
              className="flex-1"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2, delay: 0.1 }}
            >
              <div className="text-xs font-medium text-white">0xh4l...ef05</div>
              <div className="text-[10px] text-white/50">Ethereum</div>
            </motion.div>
          )}
        </motion.div>
      </div>
    </motion.aside>
  );
};

export default Sidebar;
