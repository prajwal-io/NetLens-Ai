import { useAnalysis } from '../services/analysis';
import { AnalysisWorkspace } from '../components/AnalysisWorkspace';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Box, RefreshCw } from 'lucide-react';
import { TrafficChart } from '../components/TrafficChart';
import { DefinitionList } from '../components/WorkspaceDetails';
import { Empty, Panel, Sample } from '../components/ui';
import { activity, totals } from '../fixtures/sample';
import { usePreference } from '../hooks/preferences';
import { useReceipts } from '../services/receipts';
import { api, type Health, type HistoryPage, type ModelInfo } from '../services/api';
import { setAnalysis } from '../services/analysis';

type DashboardSource = 'sample' | 'latest-validation';
const isDashboardSource = (value: unknown): value is DashboardSource => value === 'sample' || value === 'latest-validation';
const isRange = (value: unknown): value is string => value === '3 hours' || value === 'Last hour';

function BenchmarkEvidence({ health }: { health: Health | null }) {
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!health?.model_loaded) { setModel(null); setError(''); return; }
    const controller = new AbortController();
    void api.modelInfo(controller.signal).then(setModel).catch((reason) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Model evaluation is unavailable.');
    });
    return () => controller.abort();
  }, [health?.model_loaded, health?.model_version, attempt]);

  if (!health?.model_loaded) return null;
  if (error) return <section className="benchmark-evidence benchmark-evidence-error" aria-label="Model evaluation status">
    <p>{error}</p><button type="button" onClick={() => { setError(''); setAttempt((value) => value + 1); }}><RefreshCw size={14} /> Retry</button>
  </section>;
  if (!model?.evaluation?.metrics) return null;

  const metrics = model.evaluation.metrics;
  const percent = (value: number | undefined) => typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'Unavailable';
  return <section className="benchmark-evidence" aria-labelledby="benchmark-heading">
    <div className="benchmark-copy">
      <p>{model.dataset.name} · held-out test</p>
      <h2 id="benchmark-heading">A benchmark result, not a live-network guarantee.</h2>
      <span>{model.evaluation.rows.toLocaleString()} labeled flows · threshold {model.evaluation.threshold.toFixed(3)}</span>
    </div>
    <dl className="benchmark-metrics">
      <div><dt>Malicious recall</dt><dd>{percent(metrics.recall)}</dd></div>
      <div><dt>Precision</dt><dd>{percent(metrics.precision)}</dd></div>
      <div><dt>False-positive rate</dt><dd className="benchmark-false-positive">{percent(metrics.false_positive_rate)}</dd></div>
    </dl>
    <Link to="/model-lab">Review evaluation <ArrowRight size={14} /></Link>
  </section>;
}

function RecentAnalyses() {
  const [history, setHistory] = useState<HistoryPage | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    void api.history(0, controller.signal).then((result) => {
      setHistory(result); setError('');
    }).catch((reason) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Saved analyses are unavailable.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [attempt]);

  async function open(id: string) {
    setBusy(id); setError('');
    try { setAnalysis(await api.analysis(id)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not open this analysis.'); }
    finally { setBusy(''); }
  }

  return <section className="recent-analyses" aria-labelledby="recent-analyses-heading">
    <div className="recent-analyses-heading">
      <div><h2 id="recent-analyses-heading">Recent analyses</h2><p>Saved results from this local workspace.</p></div>
      <button type="button" className="quiet-button" aria-label="Refresh recent analyses" disabled={loading} onClick={() => setAttempt((value) => value + 1)}><RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh</button>
    </div>
    {error && <p className="recent-analyses-error" role="alert">{error}</p>}
    {loading && !history && <p className="recent-analyses-state" role="status">Loading saved analyses…</p>}
    {!loading && !error && history?.items.length === 0 && <div className="recent-analyses-empty">
      <Empty title="No saved analyses yet">Upload a compatible flow CSV or run a labeled historical replay. Results will appear here and stay linked across the workspace.</Empty>
      <div><Link to="/traffic-analyzer">Upload traffic data <ArrowRight size={14} /></Link><Link to="/network-pulse">Explore historical replay <ArrowRight size={14} /></Link></div>
    </div>}
    {history?.items.length ? <ul className="recent-analyses-list">
      {history.items.slice(0, 4).map((item) => <li key={item.analysis_id}>
        <div className="recent-analysis-file"><strong title={item.filename}>{item.filename}</strong><span>{item.source_type === 'historical_replay' ? 'Historical replay' : 'Uploaded CSV'} · {new Date(item.created_at).toLocaleString()}</span></div>
        <div className="recent-analysis-total"><span>Flows</span><strong>{item.total_flows.toLocaleString()}</strong></div>
        <div className="recent-analysis-alerts"><span>Malicious</span><strong>{item.counts.malicious.toLocaleString()}</strong></div>
        <button type="button" disabled={!!busy} onClick={() => void open(item.analysis_id)}>{busy === item.analysis_id ? 'Opening…' : 'Open'} <ArrowRight size={14} /><span className="sr-only"> {item.filename}</span></button>
      </li>)}
    </ul> : null}
  </section>;
}

function SampleDashboard({ health }: { health: Health | null }) {
  const { receipts } = useReceipts();
  const latestReceipt = receipts[0] ?? null;
  const [source, setSource] = usePreference('dashboard-source', 'sample' as DashboardSource, isDashboardSource);
  const [window, setWindow] = usePreference('chart-range', '3 hours', isRange);
  const showingSample = source === 'sample' || !latestReceipt;

  useEffect(() => {
    if (!latestReceipt && source !== 'sample') setSource('sample');
  }, [latestReceipt, setSource, source]);

  const chart = window === 'Last hour' ? activity.slice(-4) : activity;
  const samplePercent = totals.normal / (totals.normal + totals.suspicious) * 100;
  const modelAvailability = health?.model_loaded ? 'Loaded' : 'Not loaded';
  const modelAvailabilityNote = health?.model_loaded
    ? `${health.model_version ?? 'Version unavailable'} · Ready for uploaded analysis`
    : 'No evaluated model available';
  const metrics: [string, string, string][] = showingSample
    ? [
      ['Total traffic flows', (totals.normal + totals.suspicious).toLocaleString(), 'Three-hour sample'],
      ['Normal traffic', totals.normal.toLocaleString(), 'Illustrative sample labels'],
      ['Suspicious traffic', totals.suspicious.toLocaleString(), 'Illustrative sample labels'],
      ['Model availability', modelAvailability, modelAvailabilityNote],
    ]
    : [
      ['Validated traffic flows', latestReceipt!.rows.toLocaleString(), 'From the latest CSV validation'],
      ['Normal classifications', 'Unavailable', 'No model inference was run'],
      ['Suspicious classifications', 'Unavailable', 'No model inference was run'],
      ['Model availability', modelAvailability, modelAvailabilityNote],
    ];

  return <>
    <div className="dashboard-source-row">
      <div>
        <h2>Dashboard source</h2>
        <p>Choose between clearly labeled sample UI data and your latest validation receipt.</p>
      </div>
      <div className="dashboard-source-switch" role="group" aria-label="Dashboard data source">
        <button type="button" aria-pressed={showingSample} className={showingSample ? 'source-active' : ''} onClick={() => setSource('sample')}>
          Sample overview <span>Illustrative</span>
        </button>
        <button type="button" aria-pressed={!showingSample} className={!showingSample ? 'source-active' : ''} disabled={!latestReceipt} title={latestReceipt ? `Show ${latestReceipt.filename}` : 'Validate a CSV to enable this source'} onClick={() => setSource('latest-validation')}>
          Latest validation <span>{latestReceipt ? latestReceipt.filename : 'No upload yet'}</span>
        </button>
      </div>
    </div>

    <div className="notice dashboard-source-note">
      <Box size={17} aria-hidden="true" />
      {showingSample
        ? <span><strong>Sample UI data.</strong> Counts and charts below are illustrative fixtures, not live traffic or ML predictions.</span>
        : <span><strong>Validation only.</strong> {latestReceipt!.filename} passed CSV checks with {latestReceipt!.rows.toLocaleString()} rows. No classification predictions were generated.</span>}
      {showingSample ? <Sample /> : <span className="tag">CSV validated</span>}
    </div>

    <BenchmarkEvidence health={health} />

    <div className="metrics">
      {metrics.map(([label, value, note]) => <div key={label}>
        <p>{label}</p><strong className={value === 'Unavailable' ? 'metric-unavailable' : undefined}>{value}</strong><small>{note}</small>
      </div>)}
    </div>

    {!showingSample && latestReceipt && <Panel title="Latest validated dataset" className="dataset-summary" aside={<span className="tag">Metadata only</span>}>
      <DefinitionList items={[
        ['File name', latestReceipt.filename],
        ['Validated rows', latestReceipt.rows.toLocaleString()],
        ['Input columns', String(latestReceipt.columns.length)],
        ['Validated at', new Date(latestReceipt.received_at).toLocaleString()],
        ['ML predictions', 'Not generated'],
      ]} />
      <div className="dataset-column-list">
        <strong>Validated column names</strong>
        <ul>{latestReceipt.columns.map((column) => <li key={column}><code>{column}</code></li>)}</ul>
      </div>
      <p className="fine">The receipt stores metadata only; raw traffic rows are not retained in this browser session.</p>
      <Link className="text-action" to="/traffic-analyzer">Validate another dataset <ArrowRight size={15} /></Link>
    </Panel>}

    <div className="dashboard-grid">
      <Panel title="Traffic activity" aside={showingSample
        ? <select aria-label="Chart time window" value={window} onChange={(event) => setWindow(event.target.value)}><option>3 hours</option><option>Last hour</option></select>
        : <span className="tag">Awaiting model inference</span>}>
        {showingSample
          ? <>
            <div className="chart-caption"><span>Flow volume over time</span><div><i className="dot blue" />Normal <i className="dot red-dot" />Suspicious</div></div>
            <div className="chart"><TrafficChart data={chart} /></div>
            <details className="chart-data"><summary>Read chart data</summary><table><caption>Sample UI traffic activity</caption><thead><tr><th scope="col">Time</th><th scope="col">Normal</th><th scope="col">Suspicious</th></tr></thead><tbody>{chart.map((row) => <tr key={row.time}><th scope="row">{row.time}</th><td>{row.normal}</td><td>{row.suspicious}</td></tr>)}</tbody></table></details>
            <div className="chart-foot">Sample snapshot | {chart[0].time}–{chart[chart.length - 1].time}<span>No live packet capture</span></div>
          </>
          : <div className="dashboard-empty"><Empty title="No classification timeline yet">CSV validation confirms the file structure and values. A trained model is required before this dashboard can show classification activity.</Empty></div>}
      </Panel>

      <Panel title="Traffic distribution" aside={!showingSample ? <span className="tag">No predictions</span> : undefined}>
        {showingSample
          ? <>
            <div className="distribution"><div className="traffic-ring"><svg className="ring-svg" viewBox="0 0 160 160" aria-hidden="true"><circle cx="80" cy="80" r="70" fill="none" stroke="var(--signal-red)" strokeWidth="10" /><circle cx="80" cy="80" r="70" fill="none" stroke="var(--signal-blue)" strokeWidth="10" pathLength="100" strokeDasharray={`${samplePercent} 100`} transform="rotate(-90 80 80)" /></svg><div><strong>{samplePercent.toFixed(1)}%</strong><small>Normal sample traffic</small></div></div></div>
            <div className="legend-row"><span><i className="dot blue" />Normal</span><strong>{totals.normal.toLocaleString()}</strong></div>
            <div className="legend-row"><span><i className="dot red-dot" />Suspicious</span><strong>{totals.suspicious.toLocaleString()}</strong></div>
            <p className="fine">Illustrative sample labels, not model output.</p>
          </>
          : <div className="dashboard-empty"><Empty title="No traffic classes to compare">The uploaded file is validated, but no normal or suspicious labels have been generated.</Empty></div>}
      </Panel>

    </div>
    <RecentAnalyses />
  </>;
}

export default function Dashboard({ health }: { health: Health | null }) {
 const analysis = useAnalysis();
 return analysis ? <AnalysisWorkspace analysis={analysis} mode="Command Center" /> : <SampleDashboard health={health} />;
}
