'use client';

import { motion } from 'framer-motion';
import {
  Bot,
  User,
  AlertCircle,
  ShieldX,
  Copy,
  Check,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { UIMessage } from '@/types';

import { FlightCards } from '@/components/travel/flights/FlightCards';
import { HotelCards } from '@/components/travel/hotels/HotelCards';
import { TrainCards } from '@/components/travel/trains/TrainCards';
import { BusCards } from '@/components/travel/buses/BusCards';
import { CarCards } from '@/components/travel/cars/CarCards';

import { JourneyPlanCard } from '@/components/journey/JourneyPlanCard';
import { MockDisclaimer } from '@/components/ui/MockDisclaimer';

interface Props {
  message: UIMessage;
  onSuggestionClick?: (text: string) => void;
  onRetry?: () => void;
}

export function ChatMessage({
  message,
  onSuggestionClick,
  onRetry,
}: Props) {

  const isUser = message.role === 'user';
  const isError = message.status === 'error';
  const isStreaming = message.isStreaming;

  const results = message.travel_results;
  const journey = message.journey_plan;

  const [copied, setCopied] = useState(false);

  async function copyMessage() {
    await navigator.clipboard.writeText(message.content);

    setCopied(true);

    setTimeout(() => setCopied(false), 2000);
  }

  return (

    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: .2 }}
      className={`flex gap-3 ${
        isUser
          ? 'justify-end'
          : 'justify-start'
      }`}
    >

      {!isUser && (

        <div
          className={`

            w-9
            h-9
            rounded-full
            flex
            items-center
            justify-center
            shadow-sm
            flex-shrink-0

            ${
              message.permission_denied
                ? 'bg-red-500'
                : 'bg-blue-600'
            }

          `}
        >

          {message.permission_denied
            ? <ShieldX size={16} className="text-white"/>
            : <Bot size={17} className="text-white"/>
          }

        </div>

      )}

      <div
        className={`

        flex
        flex-col
        gap-2

        ${
          isUser
            ? 'items-end max-w-[75%]'
            : 'items-start w-full max-w-[90%]'
        }

      `}
      >

        <div
          className={`

          rounded-2xl
          px-4
          py-3
          text-sm
          leading-7

          ${
            isUser

              ? 'bg-blue-600 text-white rounded-br-sm'

              : isError || message.permission_denied

                ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-300 rounded-bl-sm'

                : 'bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm rounded-bl-sm text-gray-900 dark:text-gray-100'

          }

        `}
        >

          {isStreaming ? (

            <StreamingText text={message.content} />

          ) : isError ? (

            <div className="flex items-center gap-2">

              <AlertCircle size={16}/>

              {message.content}

            </div>

          ) : (

            <ReactMarkdown remarkPlugins={[remarkGfm]}>

              {message.content}

            </ReactMarkdown>

          )}

        </div>

        {!isUser && (

          <div className="flex items-center gap-2 text-gray-400 text-xs">

            <button
              onClick={copyMessage}
              className="hover:text-blue-600 transition"
            >

              {copied

                ? <Check size={15}/>

                : <Copy size={15}/>

              }

            </button>

            {onRetry && (

              <button
                onClick={onRetry}
                className="hover:text-blue-600 transition"
              >

                <RotateCcw size={15}/>

              </button>

            )}

            <button className="hover:text-green-600">

              <ThumbsUp size={15}/>

            </button>

            <button className="hover:text-red-500">

              <ThumbsDown size={15}/>

            </button>

            <span className="ml-2">

              {message.timestamp}

            </span>

          </div>

        )}
                {/* ===================================================== */}
        {/* Journey Plan */}
        {/* ===================================================== */}

        {!isStreaming &&
          journey &&
          journey.legs &&
          journey.legs.length > 0 && (

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full"
            >

              <JourneyPlanCard
                journey={journey}
              />

            </motion.div>

        )}

        {/* ===================================================== */}
        {/* Travel Results */}
        {/* ===================================================== */}

        {!isStreaming &&
          results && (

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-full space-y-3"
          >

            {results.is_partial_mock &&
              results.mock_reason && (

              <MockDisclaimer
                message={results.mock_reason}
              />

            )}

            {results.flights &&
              results.flights.length > 0 && (

              <FlightCards
                flights={results.flights}
              />

            )}

            {results.trains &&
              results.trains.length > 0 && (

              <TrainCards
                trains={results.trains}
              />

            )}

            {results.buses &&
              results.buses.length > 0 && (

              <BusCards
                buses={results.buses}
              />

            )}

            {results.hotels &&
              results.hotels.length > 0 && (

              <HotelCards
                hotels={results.hotels}
              />

            )}

            {results.cars &&
              results.cars.length > 0 && (

              <CarCards
                cars={results.cars}
              />

            )}

          </motion.div>

        )}

        {/* ===================================================== */}
        {/* Suggestions */}
        {/* ===================================================== */}

        {!isUser &&
          !isStreaming &&
          message.suggestions &&
          message.suggestions.length > 0 && (

          <motion.div
            layout
            className="flex flex-wrap gap-2 mt-1"
          >

            {message.suggestions.map((s, i) => (

              <button

                key={i}

                onClick={() =>
                  onSuggestionClick?.(s)
                }

                className="

                  px-3
                  py-1.5

                  rounded-full

                  text-xs
                  font-medium

                  border

                  border-blue-200
                  dark:border-blue-800

                  text-blue-600
                  dark:text-blue-400

                  hover:bg-blue-50
                  dark:hover:bg-blue-900/20

                  transition

                "

              >

                {s}

              </button>

            ))}

          </motion.div>

        )}

      </div>

      {/* ===================================================== */}
      {/* User Avatar */}
      {/* ===================================================== */}

      {isUser && (

        <div

          className="

            w-9
            h-9

            rounded-full

            bg-gray-200
            dark:bg-gray-700

            flex
            items-center
            justify-center

            shadow-sm

            flex-shrink-0

          "

        >

          <User
            size={16}
            className="text-gray-600 dark:text-gray-300"
          />

        </div>

      )}

    </motion.div>

  );

}

/* ========================================================== */
/* Streaming Cursor */
/* ========================================================== */

function StreamingText({

  text,

}: {

  text: string;

}) {

  return (

    <div className="whitespace-pre-wrap break-words">

      <ReactMarkdown remarkPlugins={[remarkGfm]}>

        {text}

      </ReactMarkdown>

      <motion.span

        animate={{
          opacity: [0, 1, 0],
        }}

        transition={{
          repeat: Infinity,
          duration: 1,
        }}

        className="inline-block ml-1"

      >

        ▋

      </motion.span>

    </div>

  );

}

/* ========================================================== */
/* Typing Dots */
/* ========================================================== */

function TypingDots() {

  return (

    <div className="flex gap-1">

      {[0, 1, 2].map((i) => (

        <motion.div

          key={i}

          className="w-2 h-2 rounded-full bg-gray-400"

          animate={{
            y: [0, -4, 0],
          }}

          transition={{
            repeat: Infinity,
            duration: .55,
            delay: i * .15,
          }}

        />

      ))}

    </div>

  );

}