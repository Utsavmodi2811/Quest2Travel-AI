'use client';

import { motion } from 'framer-motion';
import { Bot, User, AlertCircle } from 'lucide-react';
import { UIMessage } from '@/types';
import { FlightCards } from '@/components/travel/flights/FlightCards';
import { HotelCards } from '@/components/travel/hotels/HotelCards';
import { TrainCards } from '@/components/travel/trains/TrainCards';
import { BusCards } from '@/components/travel/buses/BusCards';
import { CarCards } from '@/components/travel/cars/CarCards';
import { MockDisclaimer } from '@/components/ui/MockDisclaimer';

interface Props {
  message: UIMessage;
  onSuggestionClick?: (text: string) => void;
}

export function ChatMessage({ message, onSuggestionClick }: Props) {
  const isUser      = message.role === 'user';
  const isError     = message.status === 'error';
  const isStreaming = message.isStreaming;
  const results     = message.travel_results;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
          <Bot size={15} className="text-white" />
        </div>
      )}

      <div className={`flex flex-col gap-2 ${isUser ? 'items-end max-w-[75%]' : 'items-start w-full max-w-[90%]'}`}>

        {/* Message bubble */}
        <div
          className={[
            'px-4 py-3 rounded-2xl text-sm leading-relaxed',
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : isError
                ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-bl-sm'
                : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-sm shadow-sm border border-gray-100 dark:border-gray-700',
          ].join(' ')}
        >
          {isStreaming ? (
            <TypingDots />
          ) : isError ? (
            <span className="flex items-center gap-2">
              <AlertCircle size={14} />
              {message.content}
            </span>
          ) : (
            <FormattedText text={message.content} />
          )}
        </div>

        {/* Travel result cards */}
        {!isStreaming && results && (
          <div className="w-full space-y-3">
            {results.is_partial_mock && results.mock_reason && (
              <MockDisclaimer message={results.mock_reason} />
            )}
            {results.flights  && results.flights.length  > 0 && <FlightCards flights={results.flights} />}
            {results.trains   && results.trains.length   > 0 && <TrainCards  trains={results.trains}  />}
            {results.buses    && results.buses.length    > 0 && <BusCards    buses={results.buses}    />}
            {results.hotels   && results.hotels.length   > 0 && <HotelCards  hotels={results.hotels}  />}
            {results.cars     && results.cars.length     > 0 && <CarCards    cars={results.cars}      />}
          </div>
        )}

        {/* Follow-up suggestion chips */}
        {!isUser && !isStreaming && message.suggestions && message.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-1">
            {message.suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => onSuggestionClick?.(s)}
                className="px-3 py-1.5 text-xs rounded-full border border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors font-medium"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center flex-shrink-0 mt-1">
          <User size={14} className="text-gray-600 dark:text-gray-300" />
        </div>
      )}
    </motion.div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1 px-1">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 bg-gray-400 rounded-full"
          animate={{ y: [0, -5, 0] }}
          transition={{ duration: 0.55, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </div>
  );
}

function FormattedText({ text }: { text: string }) {
  if (!text) return null;
  const lines = text.split('\n');
  return (
    <div className="space-y-0.5">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-2" />;
        // Bold **text**
        const parts = line.split(/\*\*(.*?)\*\*/g);
        return (
          <p key={i}>
            {parts.map((part, j) =>
              j % 2 === 1
                ? <strong key={j}>{part}</strong>
                : <span key={j}>{part}</span>
            )}
          </p>
        );
      })}
    </div>
  );
}
