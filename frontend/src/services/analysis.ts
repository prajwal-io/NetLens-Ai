import { useSyncExternalStore } from 'react';
import { api, type Analysis } from './api';

// Only the selected ID is stored in this browser. Traffic is restored from the local API.
let current: Analysis | null = null;
const listeners = new Set<() => void>();
export function setAnalysis(value: Analysis | null) {
  current = value;
  try { if (value) localStorage.setItem('netsight-analysis-id', value.analysis_id); else localStorage.removeItem('netsight-analysis-id'); } catch { /* Storage can be disabled; API history still works. */ }
  listeners.forEach((listener) => listener());
}
export function useAnalysis() {
  return useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, () => current, () => null);
}

export async function restoreAnalysis(signal: AbortSignal) {
  let id: string | null = null;
  try { id = localStorage.getItem('netsight-analysis-id'); } catch { return; }
  if (!id || current) return;
  const value = await api.analysis(id, signal);
  let selected: string | null = null;
  try { selected = localStorage.getItem('netsight-analysis-id'); } catch { return; }
  if (!signal.aborted && !current && selected === id) setAnalysis(value);
}
