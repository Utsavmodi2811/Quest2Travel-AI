'use client';
import { JourneyPlan } from '@/types';
import { Plane, Car, Hotel, Train, Clock, IndianRupee } from 'lucide-react';
import { formatPrice } from '@/lib/utils';

const LEG_ICONS: Record<string, React.ReactNode> = {
  flight: <Plane size={14} className="text-blue-500" />,
  cab:    <Car size={14} className="text-orange-500" />,
  hotel:  <Hotel size={14} className="text-purple-500" />,
  train:  <Train size={14} className="text-green-500" />,
  bus:    <Train size={14} className="text-yellow-500" />,
};

const LEG_COLORS: Record<string, string> = {
  flight: 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20',
  cab:    'border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/20',
  hotel:  'border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20',
  train:  'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20',
  bus:    'border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20',
};

interface Props { journey: JourneyPlan; }

export function JourneyPlanCard({ journey }: Props) {
  if (!journey.legs.length) return null;

  return (
    <div className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 bg-gradient-to-r from-blue-600 to-blue-700">
        <h3 className="text-sm font-bold text-white">📋 Your Journey Plan</h3>
        {journey.total_estimated_cost > 0 && (
          <p className="text-xs text-blue-100 mt-0.5">
            Total estimated cost: {formatPrice(journey.total_estimated_cost)}
          </p>
        )}
      </div>

      {/* Meeting info */}
      {journey.meeting?.meeting_time && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-800 text-xs text-blue-700 dark:text-blue-300">
          <Clock size={11} className="inline mr-1" />
          Meeting at <strong>{journey.meeting.meeting_time}</strong>
          {journey.meeting.meeting_location && ` — ${journey.meeting.meeting_location}`}
        </div>
      )}

      {/* Legs */}
      <div className="p-3 space-y-2">
        {journey.legs.map((leg, i) => (
          <div key={i} className={`flex items-start gap-3 p-2.5 rounded-lg border ${LEG_COLORS[leg.leg_type] || 'border-gray-200 dark:border-gray-700'}`}>
            {/* Icon + connector */}
            <div className="flex flex-col items-center gap-1">
              <div className="w-7 h-7 rounded-full bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                {LEG_ICONS[leg.leg_type] || <Plane size={14} />}
              </div>
              {i < journey.legs.length - 1 && (
                <div className="w-px h-4 bg-gray-300 dark:bg-gray-600" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-gray-800 dark:text-gray-200 leading-snug">
                {leg.description}
              </p>
              <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500 dark:text-gray-400 flex-wrap">
                {leg.depart_time && <span>🕐 {leg.depart_time}</span>}
                {leg.arrive_time && <span>→ {leg.arrive_time}</span>}
                {leg.duration_minutes && <span>⏱ {Math.floor(leg.duration_minutes / 60)}h {leg.duration_minutes % 60}m</span>}
              </div>
            </div>

            {/* Price */}
            {leg.price != null && leg.price > 0 && (
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 flex-shrink-0">
                {formatPrice(leg.price)}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-100 dark:border-gray-700 text-[10px] text-gray-400 text-center">
        Prices are estimates. Book individual segments below.
      </div>
    </div>
  );
}
