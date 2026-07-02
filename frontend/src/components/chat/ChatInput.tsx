'use client';

import {
  useState,
  useRef,
  useEffect,
  KeyboardEvent,
} from 'react';
import {
  Send,
  Loader2,
} from 'lucide-react';

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const PLACEHOLDERS = [
  'Plan my trip from Delhi to Mumbai tomorrow',
  'I have a meeting tomorrow at 11 AM at Taj Hotel Mumbai. I am in Delhi.',
  'Find a 5-star hotel in Goa under ₹6000.',
  'Book a return flight from Ahmedabad to Bangalore next Monday.',
  'Plan a 3-day vacation to Kerala.',
  'Find the cheapest train from Delhi to Jaipur.',
];

const MAX_LENGTH = 4000;

export function ChatInput({
  onSend,
  disabled = false,
}: Props) {
  const [value, setValue] = useState('');
  const [placeholderIndex, setPlaceholderIndex] = useState(0);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDERS.length);
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  const resize = () => {
    const ta = textareaRef.current;
    if (!ta) return;

    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  };

  const submit = () => {
    const text = value.trim();

    if (!text || disabled) return;

    onSend(text);

    setValue('');

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (
    e: KeyboardEvent<HTMLTextAreaElement>
  ) => {
    // Enter → Send
    if (
      e.key === 'Enter' &&
      !e.shiftKey &&
      !e.ctrlKey &&
      !e.metaKey
    ) {
      e.preventDefault();
      submit();
      return;
    }

    // Ctrl/Cmd + Enter → Send
    if (
      e.key === 'Enter' &&
      (e.ctrlKey || e.metaKey)
    ) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm p-3">

      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        disabled={disabled}
        maxLength={MAX_LENGTH}
        placeholder={PLACEHOLDERS[placeholderIndex]}
        onChange={(e) => {
          setValue(e.target.value);
          resize();
        }}
        onKeyDown={handleKeyDown}
        className="
          w-full
          resize-none
          bg-transparent
          outline-none
          text-sm
          text-gray-900
          dark:text-gray-100
          placeholder:text-gray-400
          disabled:opacity-60
          max-h-40
        "
      />

      <div className="mt-3 flex items-center justify-between">

        <div className="text-xs text-gray-400">
          {value.length}/{MAX_LENGTH}
        </div>

        <button
          onClick={submit}
          disabled={!value.trim() || disabled}
          aria-label="Send message"
          className="
            h-10
            w-10
            rounded-xl
            flex
            items-center
            justify-center
            bg-blue-600
            hover:bg-blue-700
            transition
            disabled:bg-gray-300
            dark:disabled:bg-gray-700
            disabled:cursor-not-allowed
          "
        >
          {disabled ? (
            <Loader2
              size={18}
              className="animate-spin text-white"
            />
          ) : (
            <Send
              size={18}
              className="text-white"
            />
          )}
        </button>

      </div>

      <div className="mt-2 text-[11px] text-gray-400">
        Press <b>Enter</b> to send • <b>Shift + Enter</b> for a new line • <b>Ctrl/Cmd + Enter</b> also sends.
      </div>

    </div>
  );
}