import { useSyncExternalStore } from 'react';
import type { Analysis } from './api';

// Traffic stays in this browser tab's memory and is cleared on reload.
let current: Analysis | null = null;
const listeners = new Set<() => void>();
export function setAnalysis(value: Analysis | null) {
  current = value;
  listeners.forEach((listener) => listener());
}
export function useAnalysis() {
  return useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, () => current, () => null);
}
