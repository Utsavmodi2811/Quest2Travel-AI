'use client';

import { useCallback } from 'react';
import { chatApi } from '@/lib/api';
import { useChatStore } from '@/store/chat';
import { UIMessage } from '@/types';
import { tempId } from '@/lib/utils'; // Moved from inline helper
import toast from 'react-hot-toast';

export function useChat() {
  const {
    sessionId,
    messages,
    isLoading,
    suggestions,
    travelContext,
    setSessionId,
    addMessage,
    updateMessage,
    setLoading,
    setSuggestions,
    setTravelContext,
  } = useChatStore();

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userTempId = tempId();
      const assistantTempId = tempId();

      // Optimistic user bubble
      const userMsg: UIMessage = {
        message_id: userTempId,
        session_id: sessionId || '',
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
        status: 'sending',
      };

      addMessage(userMsg);
      setLoading(true);

      // Typing indicator
      addMessage({
        message_id: assistantTempId,
        session_id: sessionId || '',
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
        isStreaming: true,
      });

      try {
        const response = await chatApi.sendMessage({
          session_id: sessionId || undefined,
          message: text,
        });
        console.log("BACKEND RESPONSE");
        console.log(response.suggestions);

        if (!sessionId) {
          setSessionId(response.session_id);
        }

        // Mark user message as sent
        updateMessage(userTempId, {
          status: 'sent',
          session_id: response.session_id,
        });

        // Replace typing indicator with assistant response
        updateMessage(assistantTempId, {
          message_id: response.message_id,
          session_id: response.session_id,
          content: response.reply,
          travel_results: response.travel_results ?? undefined,

          // ✅ New fields
          journey_plan: response.journey_plan ?? undefined,
          intent_type: response.intent_type,
          permission_denied: response.permission_denied,
          denied_service: response.denied_service,

          suggestions: response.suggestions,
          isStreaming: false,
          status: 'sent',
        });

        if (response.travel_context) {
          setTravelContext(response.travel_context);
        }

        if (response.suggestions?.length) {
          setSuggestions(response.suggestions);
        }
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : 'Something went wrong';

        updateMessage(userTempId, {
          status: 'error',
        });

        updateMessage(assistantTempId, {
          content: `Sorry, I ran into an issue: ${msg}. Please try again.`,
          isStreaming: false,
          status: 'error',
        });

        toast.error(msg);
      } finally {
        setLoading(false);
      }
    },
    [
      sessionId,
      isLoading,
      addMessage,
      updateMessage,
      setSessionId,
      setLoading,
      setSuggestions,
      setTravelContext,
    ]
  );

  return {
    sendMessage,
    messages,
    isLoading,
    suggestions,
    travelContext,
    sessionId,
  };
}