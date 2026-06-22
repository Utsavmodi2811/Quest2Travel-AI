'use client';

import { useState } from 'react';
import { Car, Users, Fuel, Settings2, ChevronDown, ChevronUp, Zap } from 'lucide-react';
import { CarResult } from '@/types';
import { formatPrice } from '@/lib/utils';

const TYPE_BADGE: Record<string, string> = {
  sedan:    'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  suv:      'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
  hatchback:'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  luxury:   'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
  minivan:  'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
};

interface Props { cars: CarResult[]; }

export function CarCards({ cars }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? cars : cars.slice(0, 3);

  if (!cars.length) return null;

  return (
    <div className="space-y-2 w-full">
      <div className="flex items-center gap-2 px-1">
        <Car size={13} className="text-teal-500" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {cars.length} Car{cars.length !== 1 ? 's' : ''} Available
        </span>
      </div>

      {visible.map((c) => {
        const isOpen   = expanded === c.result_id;
        const badge    = TYPE_BADGE[c.vehicle_type] || TYPE_BADGE.hatchback;

        return (
          <div key={c.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
            <div
              className="flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              onClick={() => setExpanded(isOpen ? null : c.result_id)}
            >
              <div className="w-11 h-11 rounded-lg bg-teal-50 dark:bg-teal-900/30 flex items-center justify-center flex-shrink-0">
                <Car size={18} className="text-teal-500" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{c.vehicle_name}</div>
                <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full capitalize ${badge}`}>
                    {c.vehicle_type}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">{c.vendor}</span>
                </div>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                  <span className="flex items-center gap-0.5"><Users size={10} />{c.seats} seats</span>
                  <span className="flex items-center gap-0.5"><Fuel size={10} />{c.fuel_type}</span>
                  <span className="flex items-center gap-0.5"><Settings2 size={10} />{c.transmission}</span>
                </div>
              </div>

              <div className="text-right flex-shrink-0">
                <div className="text-base font-bold text-gray-900 dark:text-gray-100">
                  {formatPrice(c.price_per_day, c.currency)}
                </div>
                <div className="text-[10px] text-gray-400">/day</div>
                {c.is_mock && (
                  <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1 rounded">sample</span>
                )}
              </div>

              <div className="text-gray-400 flex-shrink-0">
                {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </div>
            </div>

            {isOpen && (
              <div className="px-3 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-3">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-2">
                    <div className="text-gray-400 text-[10px] uppercase">Pickup</div>
                    <div className="font-medium text-gray-800 dark:text-gray-200 mt-0.5">{c.pickup_location}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-2">
                    <div className="text-gray-400 text-[10px] uppercase">Transmission</div>
                    <div className="font-medium text-gray-800 dark:text-gray-200 mt-0.5 capitalize">{c.transmission}</div>
                  </div>
                </div>
                {c.features.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {c.features.map((f) => (
                      <span key={f} className="flex items-center gap-1 text-xs bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full">
                        <Zap size={9} className="text-teal-400" />{f}
                      </span>
                    ))}
                  </div>
                )}
                <button className="w-full py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold transition-colors">
                  Rent this car →
                </button>
              </div>
            )}
          </div>
        );
      })}

      {cars.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-teal-600 dark:text-teal-400 hover:underline py-1 font-medium">
          {showAll ? '↑ Show fewer' : `↓ Show all ${cars.length} cars`}
        </button>
      )}
    </div>
  );
}
