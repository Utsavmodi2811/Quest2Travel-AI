'use client';

import { useState } from 'react';
import { Bus, Clock, Users, ChevronDown, ChevronUp, Zap } from 'lucide-react';
import { BusResult } from '@/types';
import { formatPrice } from '@/lib/utils';
export { BusCards } from '@/components/travel/AllCards';
interface Props { buses: BusResult[]; }

// export function BusCards({ buses }: Props) {
//   const [expanded, setExpanded] = useState<string | null>(null);
//   const [showAll, setShowAll] = useState(false);
//   const visible = showAll ? buses : buses.slice(0, 3);

//   if (!buses.length) return null;

//   return (
//     <div className="space-y-2 w-full">
//       <div className="flex items-center gap-2 px-1">
//         <Bus size={13} className="text-orange-500" />
//         <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
//           {buses.length} Bus{buses.length !== 1 ? 'es' : ''} Found
//         </span>
//       </div>

//       {visible.map((b) => {
//         const isOpen = expanded === b.result_id;
//         return (
//           <div key={b.result_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
//             <div
//               className="flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
//               onClick={() => setExpanded(isOpen ? null : b.result_id)}
//             >
//               <div className="w-11 h-11 rounded-lg bg-orange-50 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0">
//                 <Bus size={18} className="text-orange-500" />
//               </div>

//               <div className="flex-1 min-w-0">
//                 <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{b.operator}</div>
//                 <span className="inline-block text-[10px] font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 px-1.5 py-0.5 rounded-full mt-0.5">
//                   {b.bus_type}
//                 </span>
//                 <div className="flex items-center gap-2 mt-1 text-xs text-gray-600 dark:text-gray-400 flex-wrap">
//                   <span className="font-medium">{b.departure_time}</span>
//                   <span className="text-gray-300 dark:text-gray-600">→</span>
//                   <span className="font-medium">{b.arrival_time}</span>
//                   <span className="text-gray-400">·</span>
//                   <span className="flex items-center gap-0.5"><Clock size={10} />{b.duration}</span>
//                 </div>
//               </div>

//               <div className="text-right flex-shrink-0">
//                 <div className="text-base font-bold text-gray-900 dark:text-gray-100">
//                   {formatPrice(b.price, b.currency)}
//                 </div>
//                 <div className="flex items-center justify-end gap-0.5 text-[10px] text-gray-400 mt-0.5">
//                   <Users size={9} /><span>{b.available_seats} left</span>
//                 </div>
//                 {b.is_mock && (
//                   <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1 rounded">sample</span>
//                 )}
//               </div>

//               <div className="text-gray-400 flex-shrink-0">
//                 {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
//               </div>
//             </div>

//             {isOpen && (
//               <div className="px-3 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-3">
//                 {b.amenities.length > 0 && (
//                   <div>
//                     <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1.5">On-board</p>
//                     <div className="flex flex-wrap gap-1.5">
//                       {b.amenities.map((a) => (
//                         <span key={a} className="flex items-center gap-1 text-xs bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full">
//                           <Zap size={9} className="text-orange-400" />{a}
//                         </span>
//                       ))}
//                     </div>
//                   </div>
//                 )}
//                 {b.cancellation_policy && (
//                   <p className="text-xs text-gray-500">{b.cancellation_policy}</p>
//                 )}
//                 <button className="w-full py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold transition-colors">
//                   Book this bus →
//                 </button>
//               </div>
//             )}
//           </div>
//         );
//       })}

//       {buses.length > 3 && (
//         <button onClick={() => setShowAll(!showAll)} className="w-full text-xs text-orange-500 dark:text-orange-400 hover:underline py-1 font-medium">
//           {showAll ? '↑ Show fewer' : `↓ Show all ${buses.length} buses`}
//         </button>
//       )}
//     </div>
//   );
// }
