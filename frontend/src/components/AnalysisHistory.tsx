import { useCallback, useEffect, useState } from 'react';
import { api, type HistoryPage } from '../services/api';
import { restoreAnalysis, setAnalysis, useAnalysis } from '../services/analysis';

export function AnalysisHistory() {
  const analysis = useAnalysis();
  const [history, setHistory] = useState<HistoryPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const refresh = useCallback(async (signal?: AbortSignal) => {
    try { setHistory(await api.history(offset, signal)); }
    catch (reason) { if (!signal?.aborted) setError(reason instanceof Error ? reason.message : 'Could not load history.'); }
  }, [offset]);
  useEffect(() => { const controller = new AbortController(); void refresh(controller.signal); return () => controller.abort(); }, [refresh, analysis?.analysis_id]);
  useEffect(() => {
    const controller = new AbortController();
    void restoreAnalysis(controller.signal).catch(reason => { if (!controller.signal.aborted) setError(`Saved selection could not be restored: ${reason.message}. Open another saved analysis or retry.`); });
    return () => controller.abort();
  }, []);
  async function open(id: string) {
    setBusy(true); setError(''); setNotice('');
    try { setAnalysis(await api.analysis(id)); setNotice('Saved analysis opened across the workspace.'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not open analysis.'); }
    finally { setBusy(false); }
  }
  async function remove(id: string) {
    if (!window.confirm('Delete this saved analysis and its flow features from the local database? This cannot be undone.')) return;
    setBusy(true); setError('');
    try { await api.deleteAnalysis(id); if (analysis?.analysis_id === id) setAnalysis(null); setNotice('Analysis deleted.'); if (offset === 0) await refresh(); else setOffset(0); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not delete analysis.'); }
    finally { setBusy(false); }
  }
  return <details className="saved-history"><summary>Saved analyses <span>{history ? `(${history.total})` : '(loading)'}</span></summary>
    <p>Results and validated flow features are stored in SQLite on this computer. Only the selected analysis ID is stored in the browser. Delete an analysis below to remove its records.</p>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <button disabled={busy} onClick={() => { setError(''); void refresh(); }}>Refresh history</button>
    {history?.items.length === 0 && <p>No saved analyses. Upload a compatible CSV or analyze a historical replay.</p>}
    <ul>{history?.items.map(item => <li key={item.analysis_id}><div><strong>{item.filename}</strong><small>{new Date(item.created_at).toLocaleString()} &middot; {item.total_flows.toLocaleString()} flows ? {item.source_type === 'historical_replay' ? 'Historical replay' : 'Uploaded analysis'}</small></div><button disabled={busy} aria-pressed={analysis?.analysis_id === item.analysis_id} onClick={() => void open(item.analysis_id)}>Open<span className="sr-only"> {item.filename}</span></button><button disabled={busy} onClick={() => void remove(item.analysis_id)}>Delete<span className="sr-only"> {item.filename}</span></button></li>)}</ul>
    {history && history.total > 10 && <div className="analysis-result-actions"><button disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset - 10))}>Earlier page</button><span>Page {Math.floor(offset / 10) + 1}</span><button disabled={busy || offset + 10 >= history.total} onClick={() => setOffset(offset + 10)}>Later page</button></div>}
  </details>;
}
