import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(amount: number, currency = 'INR'): string {
  if (currency === 'INR') {
    return `₹${Math.round(amount).toLocaleString('en-IN')}`;
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Formats "2024-06-15T06:45:00" or "06:45" → "06:45" */
export function formatTime(raw?: string): string {
  if (!raw) return '--:--';

  if (raw.includes('T')) {
    const t = raw.split('T')[1];
    return t ? t.slice(0, 5) : raw;
  }

  return raw.slice(0, 5);
}

// Added from new version
let _counter = 0;

export function tempId(): string {
  return `tmp_${Date.now()}_${++_counter}`;
}