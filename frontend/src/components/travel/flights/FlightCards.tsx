'use client';

import { useState } from 'react';
import {
  Plane,
  Clock,
  Luggage,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  BadgeCheck,
  Timer,
  IndianRupee,
} from 'lucide-react';

import { motion, AnimatePresence } from 'framer-motion';

import { FlightResult } from '@/types';
import { formatPrice, formatTime } from '@/lib/utils';

interface Props {
  flights: FlightResult[];
}

export function FlightCards({ flights }: Props) {

  const [expanded, setExpanded] =
    useState<string | null>(null);

  const [showAll, setShowAll] =
    useState(false);

  if (!flights.length) return null;

  const visible = showAll
    ? flights
    : flights.slice(0, 3);

  function badge(index: number) {

    if (index === 0)
      return {
        text: 'Best Value',
        color:
          'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
      };

    if (index === 1)
      return {
        text: 'Cheapest',
        color:
          'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
      };

    if (index === 2)
      return {
        text: 'Fastest',
        color:
          'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
      };

    return null;

  }

  return (

    <div className="space-y-3 w-full">

      <div className="flex items-center gap-2 px-1">

        <Plane
          size={14}
          className="text-blue-500"
        />

        <span className="uppercase tracking-wide text-xs font-semibold text-gray-500">

          {flights.length} Flight

          {flights.length > 1 && 's'}

          Found

        </span>

      </div>

      {visible.map((flight, index) => {

        const first = flight.segments[0];

        const last =
          flight.segments[
            flight.segments.length - 1
          ];

        const isOpen =
          expanded === flight.result_id;

        const rank = badge(index);

        return (

          <motion.div

            key={flight.result_id}

            layout

            initial={{
              opacity: 0,
              y: 10,
            }}

            animate={{
              opacity: 1,
              y: 0,
            }}

            className="overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm"

          >

            <div

              onClick={() =>
                setExpanded(

                  isOpen
                    ? null
                    : flight.result_id

                )
              }

              className="cursor-pointer p-4"

            >

              <div className="flex items-start gap-3">

                {/* Airline */}

                <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">

                  <span className="font-bold text-blue-600">

                    {first?.airline_code ??

                      'FL'}

                  </span>

                </div>

                <div className="flex-1">

                  <div className="flex items-center justify-between gap-2">

                    <div>

                      <h3 className="font-semibold">

                        {first?.airline}

                      </h3>

                      <p className="text-xs text-gray-400">

                        {first?.flight_number}

                      </p>

                    </div>

                    {rank && (

                      <span

                        className={`text-[10px] px-2 py-1 rounded-full font-medium ${rank.color}`}

                      >

                        {rank.text}

                      </span>

                    )}

                  </div>

                  {/* Timeline */}

                  <div className="mt-4">

                    <div className="flex items-center justify-between">

                      <div>

                        <p className="font-semibold">

                          {formatTime(
                            first?.departure_time
                          )}

                        </p>

                        <p className="text-xs text-gray-400">

                          {

                            first?.departure_airport

                          }

                        </p>

                      </div>

                      <div className="flex-1 px-3">

                        <div className="relative">

                          <div className="h-[2px] bg-gray-300 dark:bg-gray-700" />

                          <Plane

                            size={12}

                            className="absolute left-1/2 -translate-x-1/2 -top-[5px] text-blue-500"

                          />

                        </div>

                        <p className="text-[11px] text-center mt-1 text-gray-400">

                          {flight.total_duration}

                        </p>

                      </div>

                      <div className="text-right">

                        <p className="font-semibold">

                          {formatTime(
                            last?.arrival_time
                          )}

                        </p>

                        <p className="text-xs text-gray-400">

                          {

                            last?.arrival_airport

                          }

                        </p>

                      </div>

                    </div>

                  </div>

                  {/* Tags */}

                  <div className="flex flex-wrap gap-2 mt-4">

                    <span className="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700">

                      {

                        flight.stops === 0

                          ? 'Non-stop'

                          : `${flight.stops} Stop`

                      }

                    </span>

                    <span className="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 capitalize">

                      {flight.cabin_class.replace(
                        '_',
                        ' '
                      )}

                    </span>

                    {flight.is_refundable && (

                      <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-700">

                        Refundable

                      </span>

                    )}

                  </div>

                </div>

                {/* Price */}

                <div className="text-right">

                  <div className="flex items-center justify-end font-bold text-lg">

                    <IndianRupee size={16} />

                    {flight.price.toLocaleString()}

                  </div>

                  <p className="text-xs text-gray-400">

                    Per Person

                  </p>

                  {flight.is_mock && (

                    <span className="mt-2 inline-block text-[10px] px-2 py-1 rounded bg-yellow-100 text-yellow-700">

                      Sample

                    </span>

                  )}

                  <div className="mt-3">

                    {isOpen

                      ? <ChevronUp size={18} />

                      : <ChevronDown size={18} />

                    }

                  </div>

                </div>

              </div>
                            {/* ====================================================== */}
              {/* Expanded Details */}
              {/* ====================================================== */}

              <AnimatePresence>

                {isOpen && (

                  <motion.div

                    initial={{
                      height: 0,
                      opacity: 0,
                    }}

                    animate={{
                      height: 'auto',
                      opacity: 1,
                    }}

                    exit={{
                      height: 0,
                      opacity: 0,
                    }}

                    transition={{
                      duration: .25,
                    }}

                    className="overflow-hidden border-t border-gray-100 dark:border-gray-700"

                  >

                    <div className="p-4 space-y-4">

                      {/* Flight Segments */}

                      {flight.segments.map((segment, i) => (

                        <div

                          key={i}

                          className="rounded-xl border border-gray-100 dark:border-gray-700 p-3"

                        >

                          <div className="flex items-start gap-3">

                            <div className="w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">

                              <Plane
                                size={13}
                                className="text-blue-500"
                              />

                            </div>

                            <div className="flex-1">

                              <div className="font-medium">

                                {segment.departure_city}

                                {' ('}

                                {segment.departure_airport}

                                {')'}

                                <ArrowRight
                                  size={12}
                                  className="inline mx-2"
                                />

                                {segment.arrival_city}

                                {' ('}

                                {segment.arrival_airport}

                                {')'}

                              </div>

                              <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">

                                <span>

                                  {formatTime(segment.departure_time)}

                                  {' - '}

                                  {formatTime(segment.arrival_time)}

                                </span>

                                <span>

                                  {segment.duration}

                                </span>

                                {segment.aircraft && (

                                  <span>

                                    {segment.aircraft}

                                  </span>

                                )}

                              </div>

                            </div>

                          </div>

                        </div>

                      ))}

                      {/* Extra Information */}

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">

                        <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">

                          <div className="flex items-center gap-2">

                            <Clock size={13} />

                            Duration

                          </div>

                          <p className="mt-2 font-semibold">

                            {flight.total_duration}

                          </p>

                        </div>

                        <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">

                          <div className="flex items-center gap-2">

                            <Luggage size={13} />

                            Baggage

                          </div>

                          <p className="mt-2 font-semibold">

                            {flight.baggage_allowance || 'Standard'}

                          </p>

                        </div>

                        <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">

                          <div className="flex items-center gap-2">

                            <RefreshCw size={13} />

                            Refund

                          </div>

                          <p className="mt-2 font-semibold">

                            {flight.is_refundable

                              ? 'Refundable'

                              : 'Non-refundable'}

                          </p>

                        </div>

                        <div className="rounded-lg bg-gray-50 dark:bg-gray-700 p-3">

                          <div className="flex items-center gap-2">

                            <BadgeCheck size={13} />

                            Provider

                          </div>

                          <p className="mt-2 font-semibold capitalize">

                            {flight.source}

                          </p>

                        </div>

                      </div>

                      {/* CTA */}

                      <button

                        className="

                        w-full

                        rounded-xl

                        bg-blue-600

                        hover:bg-blue-700

                        transition

                        py-3

                        text-white

                        font-semibold

                      "

                      >

                        Choose Flight

                      </button>

                    </div>

                  </motion.div>

                )}

              </AnimatePresence>
             </div> 
            </motion.div>

          );

      })}

      {/* ====================================================== */}
      {/* Show More */}
      {/* ====================================================== */}

      {flights.length > 3 && (

        <button

          onClick={() =>

            setShowAll(!showAll)

          }

          className="

            w-full

            rounded-lg

            py-2

            text-sm

            text-blue-600

            hover:bg-blue-50

            dark:hover:bg-blue-900/20

            transition

          "

        >

          {showAll

            ? 'Show Fewer Flights'

            : `Show All ${flights.length} Flights`

          }

        </button>

      )}

    </div>

  );

}