'use client';
import { AlertTriangle } from 'lucide-react';

export function MockDisclaimer({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-xs text-amber-700 dark:text-amber-400">
      <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  );
}
