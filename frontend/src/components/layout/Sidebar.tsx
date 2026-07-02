'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  MessageSquare,
  Trash2,
  X,
  PlaneTakeoff,
  Search,
  CalendarDays,
  MapPin,
  Briefcase,
} from 'lucide-react';

import toast from 'react-hot-toast';

import { useChatStore } from '@/store/chat';
import { sessionsApi, chatApi } from '@/lib/api';

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

  const [search, setSearch] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {

    setSessionsLoading(true);

    try {

      const data = await sessionsApi.list(30);

      setSessions(data);

    } catch {

      // Sidebar is optional

    } finally {

      setSessionsLoading(false);

    }

  }

  function handleNew() {

    startNewChat();

    if (window.innerWidth < 768) {

      setSidebarOpen(false);

    }

  }

  async function handleSelect(
    sid: string,
  ) {

    if (sid === sessionId) return;

    try {

      const history =
        await chatApi.getHistory(
          sid,
          100,
        );

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

      toast.error(
        'Failed to load conversation'
      );

    }

  }

  async function handleDelete(
    e: React.MouseEvent,
    sid: string,
  ) {

    e.stopPropagation();

    try {

      await sessionsApi.delete(sid);

      setSessions(

        sessions.filter(

          s => s.session_id !== sid

        )

      );

      if (sid === sessionId) {

        startNewChat();

      }

      toast.success('Conversation deleted');

    } catch {

      toast.error('Delete failed');

    }

  }

  function getTitle(
    s: typeof sessions[0]
  ) {

    const ctx = s.travel_context;

    if (
      ctx?.meeting?.meeting_location
    ) {

      return `Meeting • ${ctx.meeting.meeting_location}`;

    }

    if (
      ctx?.origin &&
      ctx?.destination
    ) {

      return `${ctx.origin} → ${ctx.destination}`;

    }

    if (ctx?.destination) {

      return `Trip to ${ctx.destination}`;

    }

    return 'New conversation';

  }

  function getIcon(
    s: typeof sessions[0]
  ) {

    const ctx = s.travel_context;

    if (
      ctx?.meeting
    ) {

      return (
        <Briefcase
          size={14}
          className="text-purple-500 mt-0.5"
        />
      );

    }

    if (
      ctx?.origin &&
      ctx?.destination
    ) {

      return (
        <PlaneTakeoff
          size={14}
          className="text-blue-500 mt-0.5"
        />
      );

    }

    if (
      ctx?.destination
    ) {

      return (
        <MapPin
          size={14}
          className="text-green-500 mt-0.5"
        />
      );

    }

    return (
      <MessageSquare
        size={14}
        className="text-gray-400 mt-0.5"
      />
    );

  }

  const filteredSessions = useMemo(() => {

    if (!search.trim()) {

      return sessions;

    }

    return sessions.filter((s) =>

      getTitle(s)

        .toLowerCase()

        .includes(

          search.toLowerCase()

        )

    );

  }, [sessions, search]);

  return (

    <>

      <AnimatePresence>

        {sidebarOpen && (

          <motion.div

            initial={{ opacity: 0 }}

            animate={{ opacity: 1 }}

            exit={{ opacity: 0 }}

            onClick={() =>

              setSidebarOpen(false)

            }

            className="fixed inset-0 bg-black/40 z-20 md:hidden"

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

            className="fixed md:relative z-30 md:z-auto w-72 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 shadow-xl md:shadow-none flex flex-col"

          >

            {/* Header */}

            <div className="flex items-center justify-between px-4 py-4 border-b border-gray-200 dark:border-gray-800">

              <div className="flex items-center gap-2">

                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">

                  <PlaneTakeoff

                    size={15}

                    className="text-white"

                  />

                </div>

                <div>

                  <p className="font-semibold">

                    Quest2Travel

                  </p>

                  <p className="text-[11px] text-gray-400">

                    Enterprise AI Planner

                  </p>

                </div>

              </div>

              <button

                onClick={() =>

                  setSidebarOpen(false)

                }

                className="md:hidden"

              >

                <X size={16} />

              </button>

            </div>

            {/* Search */}

            <div className="p-3">

              <div className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2">

                <Search
                  size={15}
                  className="text-gray-400"
                />

                <input

                  value={search}

                  onChange={(e) =>
                    setSearch(e.target.value)
                  }

                  placeholder="Search conversations..."

                  className="bg-transparent outline-none text-sm flex-1"

                />

              </div>

            </div>

            {/* New Chat */}

            <div className="px-3 pb-3">

              <button

                onClick={handleNew}

                className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white py-2.5 text-sm font-medium transition"

              >

                <Plus size={15} />

                New Conversation

              </button>

            </div>
                        {/* ====================================================== */}
            {/* Session List */}
            {/* ====================================================== */}

            <div className="flex-1 overflow-y-auto px-2 pb-4 scrollbar-thin">

              {sessionsLoading ? (

                <div className="space-y-2 px-1">

                  {[...Array(6)].map((_, i) => (

                    <div
                      key={i}
                      className="rounded-lg border border-gray-200 dark:border-gray-800 p-3 animate-pulse"
                    >

                      <div className="flex items-center gap-2">

                        <div className="w-4 h-4 rounded bg-gray-300 dark:bg-gray-700" />

                        <div className="flex-1">

                          <div className="h-3 w-3/4 rounded bg-gray-300 dark:bg-gray-700 mb-2" />

                          <div className="h-2 w-1/3 rounded bg-gray-200 dark:bg-gray-800" />

                        </div>

                      </div>

                    </div>

                  ))}

                </div>

              ) : filteredSessions.length === 0 ? (

                <div className="flex flex-col items-center justify-center text-center py-14 px-4">

                  <PlaneTakeoff
                    size={40}
                    className="text-gray-300 dark:text-gray-700 mb-4"
                  />

                  <p className="font-medium text-gray-700 dark:text-gray-300">

                    No conversations found

                  </p>

                  <p className="text-xs text-gray-400 mt-1">

                    Start planning your next journey.

                  </p>

                </div>

              ) : (

                <div className="space-y-1">

                  {filteredSessions.map((session) => (

                    <div

                      key={session.session_id}

                      role="button"

                      tabIndex={0}

                      onClick={() =>
                        handleSelect(session.session_id)
                      }

                      onKeyDown={(e) => {

                        if (
                          e.key === 'Enter' ||
                          e.key === ' '
                        ) {

                          handleSelect(session.session_id);

                        }

                      }}

                      className={

                        `

                        group
                        cursor-pointer

                        rounded-xl

                        px-3
                        py-3

                        transition-all

                        border

                        ${

                          session.session_id === sessionId

                            ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700'

                            : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800'

                        }

                        `

                      }

                    >

                      <div className="flex items-start gap-3">

                        {getIcon(session)}

                        <div className="flex-1 min-w-0">

                          <p className="truncate text-sm font-medium text-gray-900 dark:text-white">

                            {getTitle(session)}

                          </p>

                          <div className="flex items-center gap-2 mt-1 text-[11px] text-gray-400">

                            <CalendarDays size={10} />

                            <span>

                              {timeAgo(session.updated_at)}

                            </span>

                            <span>

                              •

                            </span>

                            <span>

                              {session.message_count} msgs

                            </span>

                          </div>

                        </div>

                        <button

                          type="button"

                          onClick={(e) =>
                            handleDelete(
                              e,
                              session.session_id
                            )
                          }

                          className="

                            opacity-0

                            group-hover:opacity-100

                            transition

                            p-1

                            rounded

                            hover:bg-red-100

                            dark:hover:bg-red-900/30

                            text-red-500

                          "

                        >

                          <Trash2 size={13} />

                        </button>

                      </div>

                    </div>

                  ))}

                </div>

              )}

            </div>

            {/* ====================================================== */}
            {/* Footer */}
            {/* ====================================================== */}

            <div className="border-t border-gray-200 dark:border-gray-800 p-3">

              <div className="rounded-lg bg-gray-50 dark:bg-gray-800 px-3 py-2">

                <p className="text-xs font-medium text-gray-700 dark:text-gray-300">

                  Enterprise AI Planner

                </p>

                <p className="text-[11px] text-gray-400 mt-1">

                  Flights • Hotels • Trains • Buses • Cars • Meetings

                </p>

              </div>

            </div>

          </motion.aside>

        )}

      </AnimatePresence>

    </>

  );

}