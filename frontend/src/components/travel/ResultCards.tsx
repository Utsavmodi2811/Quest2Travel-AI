'use client';

import { useState } from 'react';
import { Hotel, Star, Wifi, Coffee, Dumbbell, Car, Train, Bus } from 'lucide-react';
import { HotelResult, TrainResult, BusResult, CarResult } from '@/types';
import { formatPrice } from '@/lib/utils';

// ── Hotel Cards ───────────────────────────────────────────────────────────────

export function HotelCards({ hotels }: { hotels: HotelResult[] }) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? hotels : hotels.slice(0, 3);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400 px-1">
        <Hotel size={13} />
        <span>{hotels.length} hotel{hotels.length !== 1 ? 's' : ''} found</span>
      </div>
      {visible.map((h) => (
        <div key={h.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
          <div className="flex justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{h.name}</span>
                <StarsDisplay stars={h.stars} />
              </div>
              <p className="text-xs text-gray-500 mt-0.5 truncate">{h.address}</p>
              <div className="flex flex-wrap gap-1 mt-1.5">
                {h.amenities.slice(0, 4).map((a) => (
                  <span key={a} className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-1.5 py-0.5 rounded-full">{a}</span>
                ))}
              </div>
              <div className="flex gap-3 mt-1.5 text-[11px]">
                {h.breakfast_included && <span className="text-green-500 flex items-center gap-0.5"><Coffee size={10} /> Breakfast</span>}
                {h.free_cancellation && <span className="text-green-500">Free cancel</span>}
                {h.distance_from_center && <span className="text-gray-400">{h.distance_from_center.toFixed(1)} km from center</span>}
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              {h.review_score && (
                <div className="flex items-center justify-end gap-1 mb-1">
                  <span className="text-xs font-bold text-white bg-blue-600 px-1.5 py-0.5 rounded">{h.review_score.toFixed(1)}</span>
                  {h.review_count && <span className="text-[10px] text-gray-400">{h.review_count} reviews</span>}
                </div>
              )}
              <div className="text-base font-bold text-gray-900 dark:text-gray-100">
                {formatPrice(h.price_per_night, h.currency)}
              </div>
              <div className="text-[10px] text-gray-400">/night</div>
              {h.is_mock && <span className="text-[10px] text-amber-500">Sample</span>}
            </div>
          </div>
        </div>
      ))}
      {hotels.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-blue-600 dark:text-blue-400 hover:underline py-1">
          {showAll ? 'Show less' : `Show all ${hotels.length} hotels`}
        </button>
      )}
    </div>
  );
}

function StarsDisplay({ stars }: { stars: number }) {
  return (
    <div className="flex">
      {[...Array(stars)].map((_, i) => (
        <Star key={i} size={10} className="text-amber-400 fill-amber-400" />
      ))}
    </div>
  );
}

// ── Train Cards ───────────────────────────────────────────────────────────────

export function TrainCards({ trains }: { trains: TrainResult[] }) {
  const [showAll, setShowAll] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const visible = showAll ? trains : trains.slice(0, 3);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400 px-1">
        <Train size={13} />
        <span>{trains.length} train{trains.length !== 1 ? 's' : ''} found</span>
      </div>
      {visible.map((t) => {
        const isOpen = expanded === t.result_id;
        const cheapestClass = t.classes.length > 0 ? t.classes.reduce((a, b) => a.price < b.price ? a : b) : null;
        return (
          <div key={t.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
            <div className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750" onClick={() => setExpanded(isOpen ? null : t.result_id)}>
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {t.train_name}
                    <span className="ml-2 text-xs text-gray-400">#{t.train_number}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-600 dark:text-gray-400">
                    <span>{t.departure_time}</span>
                    <span className="text-gray-300">→</span>
                    <span>{t.arrival_time}</span>
                    <span className="text-gray-400">({t.duration})</span>
                  </div>
                </div>
                {cheapestClass && (
                  <div className="text-right">
                    <div className="text-sm font-bold text-gray-900 dark:text-gray-100">
                      from {formatPrice(cheapestClass.price)}
                    </div>
                    <div className="text-[10px] text-gray-400">{cheapestClass.class_name}</div>
                  </div>
                )}
              </div>
            </div>
            {isOpen && (
              <div className="px-3 pb-3 border-t border-gray-100 dark:border-gray-700">
                <div className="grid grid-cols-2 gap-1.5 mt-2">
                  {t.classes.map((cls) => (
                    <div key={cls.class_code} className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div>
                        <div className="text-xs font-medium text-gray-800 dark:text-gray-200">{cls.class_code}</div>
                        <div className="text-[10px] text-gray-500">{cls.available_seats} seats</div>
                      </div>
                      <div className="text-xs font-bold text-gray-900 dark:text-gray-100">{formatPrice(cls.price)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
      {trains.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-blue-600 dark:text-blue-400 hover:underline py-1">
          {showAll ? 'Show less' : `Show all ${trains.length} trains`}
        </button>
      )}
    </div>
  );
}

// ── Bus Cards ─────────────────────────────────────────────────────────────────

export function BusCards({ buses }: { buses: BusResult[] }) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? buses : buses.slice(0, 3);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400 px-1">
        <Bus size={13} />
        <span>{buses.length} bus{buses.length !== 1 ? 'es' : ''} found</span>
      </div>
      {visible.map((b) => (
        <div key={b.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{b.operator}</div>
              <div className="text-xs text-gray-500 mt-0.5">{b.bus_type}</div>
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-600 dark:text-gray-400">
                <span>{b.departure_time}</span>
                <span>→</span>
                <span>{b.arrival_time}</span>
                <span className="text-gray-400">({b.duration})</span>
              </div>
              <div className="text-[10px] text-gray-400 mt-1">{b.available_seats} seats left</div>
            </div>
            <div className="text-right">
              <div className="text-base font-bold text-gray-900 dark:text-gray-100">{formatPrice(b.price, b.currency)}</div>
              {b.is_mock && <span className="text-[10px] text-amber-500">Sample</span>}
            </div>
          </div>
        </div>
      ))}
      {buses.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-blue-600 dark:text-blue-400 hover:underline py-1">
          {showAll ? 'Show less' : `Show all ${buses.length} buses`}
        </button>
      )}
    </div>
  );
}

// ── Car Cards ─────────────────────────────────────────────────────────────────

export function CarCards({ cars }: { cars: CarResult[] }) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? cars : cars.slice(0, 3);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400 px-1">
        <Car size={13} />
        <span>{cars.length} car{cars.length !== 1 ? 's' : ''} available</span>
      </div>
      {visible.map((c) => (
        <div key={c.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{c.vehicle_name}</div>
              <div className="text-xs text-gray-500 mt-0.5">{c.vendor} · {c.vehicle_type} · {c.transmission}</div>
              <div className="flex gap-2 mt-1 text-[10px] text-gray-500 flex-wrap">
                <span>{c.seats} seats</span>
                <span>{c.fuel_type}</span>
                {c.features.slice(0, 3).map((f) => <span key={f}>{f}</span>)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-base font-bold text-gray-900 dark:text-gray-100">{formatPrice(c.price_per_day, c.currency)}</div>
              <div className="text-[10px] text-gray-400">/day</div>
              {c.is_mock && <span className="text-[10px] text-amber-500">Sample</span>}
            </div>
          </div>
        </div>
      ))}
      {cars.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-blue-600 dark:text-blue-400 hover:underline py-1">
          {showAll ? 'Show less' : `Show all ${cars.length} cars`}
        </button>
      )}
    </div>
  );
}
