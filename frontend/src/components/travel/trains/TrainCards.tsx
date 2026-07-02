'use client';

import { useState } from 'react';
import { Train, Clock, ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';
import { TrainResult } from '@/types';
import { formatPrice } from '@/lib/utils';
export { TrainCards } from '@/components/travel/AllCards';

const CLASS_LABELS: Record<string, string> = {
  SL: 'Sleeper', '3A': '3rd AC', '2A': '2nd AC', '1A': '1st AC', CC: 'Chair Car',
};

interface Props { trains: TrainResult[]; }

// export function TrainCards({ trains }: Props) {
//   const [expanded, setExpanded] = useState<string | null>(null);
//   const [showAll, setShowAll] = useState(false);
//   const visible = showAll ? trains : trains.slice(0, 3);

//   if (!trains.length) return null;

//   return (
//     <div className="space-y-2 w-full">
//       <div className="flex items-center gap-2 px-1">
//         <Train size={13} className="text-green-500" />
//         <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
//           {trains.length} Train{trains.length !== 1 ? 's' : ''} Found
//         </span>
//       </div>

//       {visible.map((t) => {
//         const isOpen   = expanded === t.result_id;
//         const cheapest = t.classes.length > 0
//           ? t.classes.reduce((a, b) => a.price < b.price ? a : b)
//           : null;

//         return (
//           <div key={t.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
//             <div
//               className="flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
//               onClick={() => setExpanded(isOpen ? null : t.result_id)}
//             >
//               <div className="w-11 h-11 rounded-lg bg-green-50 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0">
//                 <Train size={18} className="text-green-600 dark:text-green-400" />
//               </div>

//               <div className="flex-1 min-w-0">
//                 <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
//                   {t.train_name}
//                   <span className="ml-2 text-xs font-normal text-gray-400">#{t.train_number}</span>
//                 </div>
//                 <div className="flex items-center gap-1.5 mt-1 text-xs text-gray-600 dark:text-gray-400 flex-wrap">
//                   <span className="font-medium">{t.departure_time}</span>
//                   <span className="text-gray-400 text-[10px]">({t.origin_code})</span>
//                   <ArrowRight size={10} className="text-gray-400" />
//                   <span className="font-medium">{t.arrival_time}</span>
//                   <span className="text-gray-400 text-[10px]">({t.destination_code})</span>
//                   <span className="text-gray-400">·</span>
//                   <span className="flex items-center gap-0.5"><Clock size={10} />{t.duration}</span>
//                 </div>
//               </div>

//               <div className="text-right flex-shrink-0">
//                 {cheapest && (
//                   <>
//                     <div className="text-sm font-bold text-gray-900 dark:text-gray-100">
//                       from {formatPrice(cheapest.price)}
//                     </div>
//                     <div className="text-[10px] text-gray-400">
//                       {CLASS_LABELS[cheapest.class_code] || cheapest.class_code}
//                     </div>
//                   </>
//                 )}
//                 {t.is_mock && (
//                   <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1 rounded">sample</span>
//                 )}
//               </div>

//               <div className="text-gray-400 flex-shrink-0">
//                 {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
//               </div>
//             </div>

//             {isOpen && (
//               <div className="px-3 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-3">
//                 <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Available Classes</p>
//                 <div className="grid grid-cols-2 gap-2">
//                   {t.classes.map((cls) => (
//                     <div key={cls.class_code} className="flex items-center justify-between p-2.5 rounded-lg bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600">
//                       <div>
//                         <div className="text-xs font-semibold text-gray-800 dark:text-gray-200">{cls.class_code}</div>
//                         <div className="text-[10px] text-gray-500">{CLASS_LABELS[cls.class_code] || cls.class_name}</div>
//                         <div className="text-[10px] text-gray-400">{cls.available_seats} seats</div>
//                       </div>
//                       <div className="text-sm font-bold text-green-600 dark:text-green-400">
//                         {formatPrice(cls.price)}
//                       </div>
//                     </div>
//                   ))}
//                 </div>
//                 {t.runs_on.length > 0 && (
//                   <div className="flex items-center gap-1 flex-wrap">
//                     <span className="text-[10px] text-gray-400">Runs:</span>
//                     {t.runs_on.map((d) => (
//                       <span key={d} className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-500 px-1.5 py-0.5 rounded">{d}</span>
//                     ))}
//                   </div>
//                 )}
//                 <button className="w-full py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-semibold transition-colors">
//                   Book on IRCTC →
//                 </button>
//               </div>
//             )}
//           </div>
//         );
//       })}

//       {trains.length > 3 && (
//         <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-green-600 dark:text-green-400 hover:underline py-1 font-medium">
//           {showAll ? '↑ Show fewer' : `↓ Show all ${trains.length} trains`}
//         </button>
//       )}
//     </div>
//   );
// }
