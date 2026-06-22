'use client';

import { useState } from 'react';
import { Hotel, Star, Coffee, MapPin, ChevronDown, ChevronUp, Wifi, Dumbbell, Waves } from 'lucide-react';
import { HotelResult } from '@/types';
import { formatPrice } from '@/lib/utils';

function StarsRow({ stars }: { stars: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[...Array(5)].map((_, i) => (
        <Star key={i} size={10}
          className={i < stars ? 'text-amber-400 fill-amber-400' : 'text-gray-200 dark:text-gray-700 fill-current'} />
      ))}
    </div>
  );
}

function AmenityIcon({ name }: { name: string }) {
  const n = name.toLowerCase();
  if (n.includes('wifi') || n.includes('internet')) return <Wifi size={10} />;
  if (n.includes('gym') || n.includes('fitness'))   return <Dumbbell size={10} />;
  if (n.includes('pool') || n.includes('swim'))     return <Waves size={10} />;
  if (n.includes('breakfast') || n.includes('cafe')) return <Coffee size={10} />;
  return null;
}

interface Props { hotels: HotelResult[]; }

export function HotelCards({ hotels }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? hotels : hotels.slice(0, 3);

  if (!hotels.length) return null;

  return (
    <div className="space-y-2 w-full">
      <div className="flex items-center gap-2 px-1">
        <Hotel size={13} className="text-purple-500" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {hotels.length} Hotel{hotels.length !== 1 ? 's' : ''} Found
        </span>
      </div>

      {visible.map((h) => {
        const isOpen = expanded === h.result_id;
        return (
          <div key={h.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
            <div
              className="flex gap-3 p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              onClick={() => setExpanded(isOpen ? null : h.result_id)}
            >
              {/* Stars badge */}
              <div className="w-11 h-11 rounded-lg bg-purple-50 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-bold text-purple-600 dark:text-purple-400">{h.stars}★</span>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{h.name}</p>
                    <StarsRow stars={h.stars} />
                    <div className="flex items-center gap-1 mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                      <MapPin size={10} />
                      <span className="truncate">{h.address}</span>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    {h.review_score != null && (
                      <div className="flex items-center justify-end gap-1 mb-1">
                        <span className="text-xs font-bold text-white bg-blue-600 px-1.5 py-0.5 rounded">
                          {h.review_score.toFixed(1)}
                        </span>
                      </div>
                    )}
                    <div className="text-base font-bold text-gray-900 dark:text-gray-100">
                      {formatPrice(h.price_per_night, h.currency)}
                    </div>
                    <div className="text-[10px] text-gray-400">/night</div>
                    {h.is_mock && (
                      <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1 rounded">sample</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap gap-1 mt-1.5">
                  {h.breakfast_included && (
                    <span className="flex items-center gap-0.5 text-[10px] bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 px-1.5 py-0.5 rounded-full">
                      <Coffee size={9} /> Breakfast
                    </span>
                  )}
                  {h.free_cancellation && (
                    <span className="text-[10px] bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 px-1.5 py-0.5 rounded-full">
                      Free cancel
                    </span>
                  )}
                  {h.distance_from_center != null && (
                    <span className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 px-1.5 py-0.5 rounded-full">
                      {h.distance_from_center.toFixed(1)} km centre
                    </span>
                  )}
                </div>
              </div>

              <div className="text-gray-400 flex-shrink-0 self-center">
                {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </div>
            </div>

            {isOpen && (
              <div className="px-3 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-3">
                {h.amenities.length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1.5">Amenities</p>
                    <div className="flex flex-wrap gap-1.5">
                      {h.amenities.map((a) => (
                        <span key={a} className="flex items-center gap-1 text-xs bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full">
                          <AmenityIcon name={a} />{a}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {h.review_count != null && (
                  <p className="text-xs text-gray-500">{h.review_count.toLocaleString()} guest reviews</p>
                )}
                <button className="w-full py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold transition-colors">
                  View hotel details →
                </button>
              </div>
            )}
          </div>
        );
      })}

      {hotels.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-purple-600 dark:text-purple-400 hover:underline py-1 font-medium">
          {showAll ? '↑ Show fewer' : `↓ Show all ${hotels.length} hotels`}
        </button>
      )}
    </div>
  );
}
