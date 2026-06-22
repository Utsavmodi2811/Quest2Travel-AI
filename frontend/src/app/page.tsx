'use client';

import { useEffect, useRef } from 'react';
import { Menu, Moon, Sun, PlaneTakeoff, Plus } from 'lucide-react';
import { useChatStore } from '@/store/chat';
import { useChat } from '@/hooks/useChat';
import { Sidebar } from '@/components/layout/Sidebar';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { ChatInput } from '@/components/chat/ChatInput';

const QUICK_PROMPTS = [
  '✈️ Delhi to Mumbai flights tomorrow',
  '🏨 5-star hotels in Goa under ₹8,000',
  '🚂 Train from Ahmedabad to Bangalore',
  '🚌 Bus from Pune to Hyderabad tonight',
];

export default function ChatPage() {
  const { sidebarOpen, darkMode, setSidebarOpen, toggleDarkMode, startNewChat } =
    useChatStore();
  const { messages, isLoading, sendMessage, sessionId } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Apply dark mode class to <html>
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">

      {/* Sidebar */}
      <Sidebar />

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0 h-full">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0 shadow-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors"
              title="Toggle sidebar"
            >
              <Menu size={18} />
            </button>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
                <PlaneTakeoff size={14} className="text-white" />
              </div>
              <span className="font-semibold text-gray-900 dark:text-white text-sm hidden sm:block">
                Quest2Travel
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {sessionId && (
              <span className="text-[10px] text-gray-400 font-mono hidden md:block">
                {sessionId.slice(0, 8)}…
              </span>
            )}
            <button
              onClick={startNewChat}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
            >
              <Plus size={13} />
              <span className="hidden sm:block">New chat</span>
            </button>
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors"
              title="Toggle dark mode"
            >
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </header>

        {/* ── Messages ───────────────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-6">

            {/* Empty state */}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 gap-6 text-center">
                <div className="w-16 h-16 rounded-2xl bg-blue-600 flex items-center justify-center shadow-lg">
                  <PlaneTakeoff size={28} className="text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                    Where would you like to go?
                  </h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
                    I can search flights, trains, buses, hotels & cars — and remember your preferences throughout our conversation.
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                  {QUICK_PROMPTS.map((p) => (
                    <button
                      key={p}
                      onClick={() => sendMessage(p.replace(/^[^\s]+\s/, ''))}
                      className="px-4 py-3 rounded-xl text-left text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message list */}
            {messages.map((msg) => (
              <ChatMessage
                key={msg.message_id}
                message={msg}
                onSuggestionClick={sendMessage}
              />
            ))}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* ── Input ──────────────────────────────────────────────────────── */}
        <div className="flex-shrink-0 px-4 pb-4 pt-2 bg-gray-50 dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800">
          <div className="max-w-3xl mx-auto">
            <ChatInput onSend={sendMessage} disabled={isLoading} />
            <p className="text-[10px] text-center text-gray-400 mt-2">
              Quest2Travel uses live APIs with intelligent fallback. Results marked "sample" use mock data.
            </p>
          </div>
        </div>

      </main>
    </div>
  );
}
