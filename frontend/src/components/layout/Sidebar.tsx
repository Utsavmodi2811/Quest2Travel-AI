'use client';

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  MessageSquare,
  Trash2,
  X,
  PlaneTakeoff,
} from 'lucide-react';
import { useChatStore } from '@/store/chat';
import { sessionsApi, chatApi } from '@/lib/api';
import toast from 'react-hot-toast';

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;

  return `${days}d ago`;
}

export function Sidebar() {
  const {
    sessions,
    sessionsLoading,
    sidebarOpen,
    sessionId,
    setSessions,
    setSessionsLoading,
    setSidebarOpen,
    startNewChat,
    setSessionId,
    setMessages,
  } = useChatStore();

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setSessionsLoading(true);

    try {
      const data = await sessionsApi.list(30);
      setSessions(data);
    } catch {
      // Sidebar is non-critical
    } finally {
      setSessionsLoading(false);
    }
  };

  const handleNew = () => {
    startNewChat();

    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  const handleSelect = async (sid: string) => {
    if (sid === sessionId) return;

    try {
      const history = await chatApi.getHistory(sid, 100);

      setSessionId(sid);
      setMessages(
        history.map((m: any) => ({
          ...m,
          status: 'sent',
        }))
      );

      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    } catch {
      toast.error('Failed to load conversation');
    }
  };

  const handleDelete = async (
    e: React.MouseEvent,
    sid: string
  ) => {
    e.stopPropagation();

    try {
      await sessionsApi.delete(sid);

      setSessions(
        sessions.filter((s) => s.session_id !== sid)
      );

      if (sid === sessionId) {
        startNewChat();
      }

      toast.success('Deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  const getTitle = (s: typeof sessions[0]) => {
    const ctx = s.travel_context;

    if (ctx?.origin && ctx?.destination) {
      return `${ctx.origin} → ${ctx.destination}`;
    }

    if (ctx?.destination) {
      return `📍 ${ctx.destination}`;
    }

    return 'New conversation';
  };

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            className="fixed inset-0 bg-black/40 z-20 md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{
              type: 'spring',
              damping: 28,
              stiffness: 220,
            }}
            className="fixed md:relative z-30 md:z-auto w-72 h-full flex flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 shadow-xl md:shadow-none flex-shrink-0"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3.5 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
                  <PlaneTakeoff
                    size={14}
                    className="text-white"
                  />
                </div>

                <span className="font-semibold text-gray-900 dark:text-white text-sm">
                  Quest2Travel
                </span>
              </div>

              <button
                type="button"
                onClick={() => setSidebarOpen(false)}
                className="md:hidden p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
              >
                <X size={16} />
              </button>
            </div>

            {/* New chat button */}
            <div className="p-3">
              <button
                type="button"
                onClick={handleNew}
                className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
              >
                <Plus size={15} />
                New conversation
              </button>
            </div>

            {/* Session list */}
            <div className="flex-1 overflow-y-auto scrollbar-thin px-2 pb-4">
              {sessionsLoading ? (
                <div className="space-y-2 px-1">
                  {[...Array(6)].map((_, i) => (
                    <div
                      key={i}
                      className="h-14 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"
                    />
                  ))}
                </div>
              ) : sessions.length === 0 ? (
                <p className="text-xs text-gray-400 text-center py-10">
                  No conversations yet
                </p>
              ) : (
                <div className="space-y-0.5">
                  {sessions.map((s) => (
                    <div
                      key={s.session_id}
                      role="button"
                      tabIndex={0}
                      onClick={() =>
                        handleSelect(s.session_id)
                      }
                      onKeyDown={(e) => {
                        if (
                          e.key === 'Enter' ||
                          e.key === ' '
                        ) {
                          handleSelect(s.session_id);
                        }
                      }}
                      className={[
                        'w-full flex items-start gap-2.5 px-3 py-2.5 rounded-lg text-left group transition-colors cursor-pointer',
                        s.session_id === sessionId
                          ? 'bg-blue-50 dark:bg-blue-900/30'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-800',
                      ].join(' ')}
                    >
                      <MessageSquare
                        size={14}
                        className={`mt-0.5 flex-shrink-0 ${
                          s.session_id === sessionId
                            ? 'text-blue-600'
                            : 'text-gray-400'
                        }`}
                      />

                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">
                          {getTitle(s)}
                        </p>

                        <p className="text-[11px] text-gray-400 mt-0.5">
                          {timeAgo(s.updated_at)} ·{' '}
                          {s.message_count} msgs
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={(e) =>
                          handleDelete(e, s.session_id)
                        }
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-400 transition-all flex-shrink-0"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}