import { create } from 'zustand';
import { UIMessage, TravelContext, SessionSummary } from '@/types';

interface ChatState {
  sessionId: string | null;
  messages: UIMessage[];
  travelContext: TravelContext | null;
  isLoading: boolean;
  suggestions: string[];
  sessions: SessionSummary[];
  sessionsLoading: boolean;
  sidebarOpen: boolean;
  darkMode: boolean;

  setSessionId: (id: string | null) => void;
  addMessage: (msg: UIMessage) => void;
  updateMessage: (id: string, updates: Partial<UIMessage>) => void;
  setMessages: (msgs: UIMessage[]) => void;
  setTravelContext: (ctx: TravelContext | null) => void;
  setLoading: (v: boolean) => void;
  setSuggestions: (s: string[]) => void;
  setSessions: (s: SessionSummary[]) => void;
  setSessionsLoading: (v: boolean) => void;
  setSidebarOpen: (v: boolean) => void;
  toggleDarkMode: () => void;
  startNewChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  sessionId: null,
  messages: [],
  travelContext: null,
  isLoading: false,
  suggestions: [],
  sessions: [],
  sessionsLoading: false,
  sidebarOpen: true,
  darkMode: false,

  setSessionId: (id) => set({ sessionId: id }),

  addMessage: (msg) =>
    set((s) => ({
      messages: [...s.messages, msg],
    })),

  updateMessage: (id, updates) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.message_id === id ? { ...m, ...updates } : m
      ),
    })),

  setMessages: (msgs) => set({ messages: msgs }),

  setTravelContext: (ctx) => set({ travelContext: ctx }),

  setLoading: (v) => set({ isLoading: v }),

  setSuggestions: (s) => set({ suggestions: s }),

  setSessions: (s) => set({ sessions: s }),

  setSessionsLoading: (v) => set({ sessionsLoading: v }),

  setSidebarOpen: (v) => set({ sidebarOpen: v }),

  toggleDarkMode: () =>
    set((s) => ({
      darkMode: !s.darkMode,
    })),

  startNewChat: () =>
    set({
      sessionId: null,
      messages: [],
      travelContext: null,
      suggestions: [],
      isLoading: false,
    }),
}));