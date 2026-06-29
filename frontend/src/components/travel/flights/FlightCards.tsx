'use client';

import { useState } from 'react';
import { Plane, Clock, ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';
import { FlightResult } from '@/types';
import { formatPrice, formatTime } from '@/lib/utils';

interface Props { flights: FlightResult[]; }

export function FlightCards({ flights }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? flights : flights.slice(0, 3);

  if (!flights.length) return null;

  return (
    <div className="space-y-2 w-full">
      <div className="flex items-center gap-2 px-1">
        <Plane size={13} className="text-blue-500" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {flights.length} Flight{flights.length !== 1 ? 's' : ''} Found
        </span>
      </div>

      {visible.map((f) => {
        const first = f.segments[0];
        const last  = f.segments[f.segments.length - 1];
        const isOpen = expanded === f.result_id;

        return (
          <div key={f.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
            {/* Main row */}
            <div
              className="flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              onClick={() => setExpanded(isOpen ? null : f.result_id)}
            >
              {/* Airline badge */}
              <div className="w-11 h-11 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-bold text-blue-600 dark:text-blue-400">
                  {first?.airline_code || 'FL'}
                </span>
              </div>

              {/* Route info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-900 dark:text-gray-100 flex-wrap">
                  <span>{first?.departure_airport || '---'}</span>
                  <span className="text-xs text-gray-400">{formatTime(first?.departure_time)}</span>
                  <ArrowRight size={12} className="text-gray-400 flex-shrink-0" />
                  <span>{last?.arrival_airport || '---'}</span>
                  <span className="text-xs text-gray-400">{formatTime(last?.arrival_time)}</span>
                </div>
                <div className="flex items-center gap-1.5 mt-0.5 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                  <span>{first?.airline}</span>
                  <span>·</span>
                  <span>{first?.flight_number}</span>
                  <span>·</span>
                  <span>{f.total_duration}</span>
                  <span>·</span>
                  <span className={f.stops === 0 ? 'text-green-500 font-medium' : 'text-orange-500'}>
                    {f.stops === 0 ? 'Non-stop' : `${f.stops} stop${f.stops > 1 ? 's' : ''}`}
                  </span>
                </div>
              </div>

              {/* Price */}
              <div className="text-right flex-shrink-0">
                <div className="text-base font-bold text-gray-900 dark:text-gray-100">
                  {formatPrice(f.price, f.currency)}
                </div>
                <div className="text-[10px] text-gray-400 capitalize">
                  {f.cabin_class.replace('_', ' ')}
                </div>
                {f.is_mock && (
                  <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 px-1 rounded">
                    sample
                  </span>
                )}
              </div>

              <div className="text-gray-400 flex-shrink-0">
                {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </div>
            </div>

            {/* Expanded details */}
            {isOpen && (
              <div className="px-3 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-3">
                {f.segments.map((seg, i) => (
                  <div key={i} className="flex items-start gap-3 text-xs text-gray-600 dark:text-gray-400">
                    <div className="w-6 h-6 rounded bg-gray-100 dark:bg-gray-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Plane size={10} className="text-blue-500" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-800 dark:text-gray-200">
                        {seg.departure_city} ({seg.departure_airport}) → {seg.arrival_city} ({seg.arrival_airport})
                      </div>
                      <div className="mt-0.5 text-gray-500 flex gap-2 flex-wrap">
                        <span>{formatTime(seg.departure_time)} – {formatTime(seg.arrival_time)}</span>
                        <span>· {seg.duration}</span>
                        {seg.aircraft && <span>· {seg.aircraft}</span>}
                      </div>
                    </div>
                  </div>
                ))}

                <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-100 dark:border-gray-700">

                  <span className="flex items-center gap-1">
                    <Clock size={11} />
                    {f.total_duration}
                  </span>

                </div>

                <button className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors">
                  Select this flight →
                </button>
              </div>
            )}
          </div>
        );
      })}

      {flights.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-blue-600 dark:text-blue-400 hover:underline py-1 font-medium">
          {showAll ? '↑ Show fewer' : `↓ Show all ${flights.length} flights`}
        </button>
      )}
    </div>
  );
}
