'use client';
import { useState } from 'react';
import { Train, Bus, Car, Clock, Users, Fuel, ChevronDown, ChevronUp, ArrowRight, Settings2, Zap } from 'lucide-react';
import { TrainResult, BusResult, CarResult } from '@/types';
import { formatPrice } from '@/lib/utils';

const CLASS_LABELS: Record<string, string> = {
  SL: 'Sleeper', '3A': '3rd AC', '2A': '2nd AC', '1A': '1st AC', CC: 'Chair Car',
};

// ── Train Cards ───────────────────────────────────────────────────────────────
export function TrainCards({ trains }: { trains: TrainResult[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? trains : trains.slice(0, 3);
  if (!trains.length) return null;

  return (
    <div className="space-y-2 w-full">
      <div className="flex items-center gap-2 px-1">
        <Train size={13} className="text-green-500" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {trains.length} Train{trains.length !== 1 ? 's' : ''} Found
        </span>
      </div>
      {visible.map((t) => {
        const isOpen = expanded === t.result_id;
        const cheapest = t.classes.length > 0 ? t.classes.reduce((a, b) => a.price < b.price ? a : b) : null;
        return (
          <div key={t.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
            <div className="flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              onClick={() => setExpanded(isOpen ? null : t.result_id)}>
              <div className="w-11 h-11 rounded-lg bg-green-50 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0">
                <Train size={18} className="text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                  {t.train_name} <span className="text-xs font-normal text-gray-400">#{t.train_number}</span>
                </div>
                <div className="flex items-center gap-1.5 mt-1 text-xs text-gray-600 dark:text-gray-400 flex-wrap">
                  <span className="font-medium">{t.departure_time}</span>
                  <span className="text-gray-400 text-[10px]">({t.origin_code})</span>
                  <ArrowRight size={10} className="text-gray-400" />
                  <span className="font-medium">{t.arrival_time}</span>
                  <span className="text-gray-400 text-[10px]">({t.destination_code})</span>
                  <span className="text-gray-400">·</span>
                  <span className="flex items-center gap-0.5"><Clock size={10} />{t.duration}</span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                {cheapest && (
                  <>
                    <div className="text-sm font-bold text-gray-900 dark:text-gray-100">from {formatPrice(cheapest.price)}</div>
                    <div className="text-[10px] text-gray-400">{CLASS_LABELS[cheapest.class_code] || cheapest.class_code}</div>
                  </>
                )}
                {t.is_mock && <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1 rounded">sample</span>}
              </div>
              <div className="text-gray-400 flex-shrink-0">{isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</div>
            </div>
            {isOpen && (
              <div className="px-3 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  {t.classes.map((cls) => (
                    <div key={cls.class_code} className="flex items-center justify-between p-2.5 rounded-lg bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600">
                      <div>
                        <div className="text-xs font-semibold text-gray-800 dark:text-gray-200">{cls.class_code}</div>
                        <div className="text-[10px] text-gray-500">{CLASS_LABELS[cls.class_code] || cls.class_name}</div>
                        <div className="text-[10px] text-gray-400">{cls.available_seats} seats</div>
                      </div>
                      <div className="text-sm font-bold text-green-600 dark:text-green-400">{formatPrice(cls.price)}</div>
                    </div>
                  ))}
                </div>
                {t.runs_on.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-[10px] text-gray-400">Runs:</span>
                    {t.runs_on.map((d) => <span key={d} className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-500 px-1.5 py-0.5 rounded">{d}</span>)}
                  </div>
                )}
                <button className="w-full py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-semibold transition-colors">
                  Book on IRCTC →
                </button>
              </div>
            )}
          </div>
        );
      })}
      {trains.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-green-600 dark:text-green-400 hover:underline py-1 font-medium">
          {showAll ? '↑ Show fewer' : `↓ Show all ${trains.length} trains`}
        </button>
      )}
    </div>
  );
}

// ── Bus Cards ─────────────────────────────────────────────────────────────────
export function BusCards({ buses }: { buses: BusResult[] }) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? buses : buses.slice(0, 3);
  if (!buses.length) return null;

  return (
    <div className="space-y-2 w-full">
      <div className="flex items-center gap-2 px-1">
        <Bus size={13} className="text-orange-500" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {buses.length} Bus{buses.length !== 1 ? 'es' : ''} Found
        </span>
      </div>
      {visible.map((b) => (
        <div key={b.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-lg bg-orange-50 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0">
              <Bus size={18} className="text-orange-500" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{b.operator}</div>
              <span className="inline-block text-[10px] font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 px-1.5 py-0.5 rounded-full mt-0.5">{b.bus_type}</span>
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-600 dark:text-gray-400">
                <span>{b.departure_time}</span><span>→</span><span>{b.arrival_time}</span>
                <span>·</span><span className="flex items-center gap-0.5"><Clock size={10} />{b.duration}</span>
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-base font-bold text-gray-900 dark:text-gray-100">{formatPrice(b.price, b.currency)}</div>
              <div className="flex items-center justify-end gap-0.5 text-[10px] text-gray-400 mt-0.5"><Users size={9} />{b.available_seats} left</div>
              {b.is_mock && <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1 rounded">sample</span>}
            </div>
          </div>
          {b.amenities.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {b.amenities.map((a) => <span key={a} className="flex items-center gap-0.5 text-[10px] bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-1.5 py-0.5 rounded-full"><Zap size={8} className="text-orange-400" />{a}</span>)}
            </div>
          )}
        </div>
      ))}
      {buses.length > 3 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-orange-500 dark:text-orange-400 hover:underline py-1 font-medium">
          {showAll ? '↑ Show fewer' : `↓ Show all ${buses.length} buses`}
        </button>
      )}
    </div>
  );
}

// ── Car Cards ─────────────────────────────────────────────────────────────────
const TYPE_BADGE: Record<string, string> = {
  sedan: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  suv: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
  hatchback: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  luxury: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
};

export function CarCards({ cars }: { cars: CarResult[] }) {
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
        const isOpen = expanded === c.result_id;
        return (
          <div key={c.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
            <div className="flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              onClick={() => setExpanded(isOpen ? null : c.result_id)}>
              <div className="w-11 h-11 rounded-lg bg-teal-50 dark:bg-teal-900/30 flex items-center justify-center flex-shrink-0">
                <Car size={18} className="text-teal-500" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{c.vehicle_name}</div>
                <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full capitalize ${TYPE_BADGE[c.vehicle_type] || TYPE_BADGE.hatchback}`}>{c.vehicle_type}</span>
                  <span className="text-xs text-gray-500">{c.vendor}</span>
                </div>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 flex-wrap">
                  <span className="flex items-center gap-0.5"><Users size={10} />{c.seats}</span>
                  <span className="flex items-center gap-0.5"><Fuel size={10} />{c.fuel_type}</span>
                  <span className="flex items-center gap-0.5"><Settings2 size={10} />{c.transmission}</span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-base font-bold text-gray-900 dark:text-gray-100">{formatPrice(c.price_per_day, c.currency)}</div>
                <div className="text-[10px] text-gray-400">/day</div>
                {c.is_mock && <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1 rounded">sample</span>}
              </div>
              <div className="text-gray-400 flex-shrink-0">{isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</div>
            </div>
            {isOpen && (
              <div className="px-3 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-2">
                {c.features.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {c.features.map((f) => <span key={f} className="flex items-center gap-1 text-xs bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full"><Zap size={9} className="text-teal-400" />{f}</span>)}
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
