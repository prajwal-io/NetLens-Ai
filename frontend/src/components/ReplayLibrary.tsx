import { useEffect, useRef, useState } from 'react';
import { api, type ReplayScenario } from '../services/api';
import { setAnalysis } from '../services/analysis';
import { Panel } from './ui';

export function ReplayLibrary() {
  const [items, setItems] = useState<ReplayScenario[]>([]);
  const [selected, setSelected] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const request = new AbortController();
    void api.replays(request.signal)
      .then(value => { setItems(value); setSelected(value[0]?.id ?? ''); setError(''); })
      .catch(reason => { if (!request.signal.aborted) setError(reason.message); });
    return () => { request.abort(); controller.current?.abort(); };
  }, [retry]);

  async function analyze() {
    controller.current = new AbortController();
    setBusy(true);
    setError('');
    try {
      const analysis = await api.replay(selected, controller.current.signal);
      if (!controller.current.signal.aborted) setAnalysis(analysis);
    } catch (reason) {
      if (!controller.current.signal.aborted) setError(reason instanceof Error ? reason.message : 'Replay analysis failed.');
    } finally {
      setBusy(false);
    }
  }

  const scenario = items.find(item => item.id === selected);

  return <Panel title="Historical replay" className="historical-replay-panel" aside={<span className="tag">Real benchmark records / not live</span>}>
    <div className="historical-replay-body">
      <p className="historical-replay-copy">Run the active model on a bundled held-out UNSW-NB15 excerpt. Predictions are saved and linked across the workspace. Cancel stops waiting; server work already started may still finish and appear in history.</p>
      <div className="historical-replay-control">
        <label className="field-label" htmlFor="replay-scenario">Replay scenario</label>
        <select id="replay-scenario" disabled={busy || !items.length} value={selected} onChange={event => setSelected(event.target.value)}>
          {items.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
      </div>
      {scenario && <div className="historical-replay-meta"><p>{scenario.description}</p><span>{scenario.timing}</span></div>}
      <div className="historical-replay-actions analysis-result-actions">
        <button className="primary" disabled={busy || !selected} onClick={() => void analyze()}>{busy ? 'Analyzing replay...' : 'Analyze historical replay'}</button>
        {busy && <button onClick={() => controller.current?.abort()}>Cancel request</button>}
      </div>
      {error && <div className="historical-replay-error error" role="alert">{error}<button onClick={() => setRetry(value => value + 1)}>Retry replay list</button></div>}
    </div>
  </Panel>;
}
