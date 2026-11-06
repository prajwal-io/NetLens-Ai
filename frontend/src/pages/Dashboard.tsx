import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Box, CheckCircle2, FlaskConical } from 'lucide-react';
import { FlowTable } from '../components/FlowTable';
import { NetworkMap } from '../components/NetworkMap';
import { TrafficChart } from '../components/TrafficChart';
import { DefinitionList } from '../components/WorkspaceDetails';
import { Empty, Panel, Sample } from '../components/ui';
import { activity, totals } from '../fixtures/sample';
import { usePreference } from '../hooks/preferences';
import { useReceipts } from '../services/receipts';
import type { Health } from '../services/api';

type DashboardSource = 'sample' | 'latest-validation';
const isDashboardSource = (value: unknown): value is DashboardSource => value === 'sample' || value === 'latest-validation';
const isRange = (value: unknown): value is string => value === '3 hours' || value === 'Last hour';

export default function Dashboard({ health }: { health: Health | null }) {
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
  const modelAvailability = health?.model_loaded
    ? `Loaded / ${health.model_version ?? 'version unavailable'}`
    : 'Not loaded';
  const modelAvailabilityNote = health?.model_loaded
    ? 'Ready for uploaded analysis'
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

    <Panel title="Workspace readiness" className="readiness-panel">
      <div className="readiness">
        <div><span className={health ? 'status-dot' : 'status-dot offline'} /><span><strong>FastAPI backend</strong><small>{health ? 'Connected to local API' : 'Waiting for connection'}</small></span></div>
        <div><CheckCircle2 size={17} /><span><strong>CSV validation</strong><small>{latestReceipt ? `${latestReceipt.rows.toLocaleString()} rows in latest receipt` : 'Ready for a compatible flow CSV'}</small></span></div>
        <div><FlaskConical size={17} /><span><strong>ML pipeline</strong><small>{health?.model_loaded ? `Model ${health.model_version ?? 'loaded'}` : 'No trained model installed'}</small></span></div>
      </div>
      <Link className="text-action" to="/traffic-analyzer">Validate a dataset <ArrowRight size={15} /></Link>
    </Panel>

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

      <Panel className="records-panel" title={showingSample ? 'Recent sample flows' : 'Uploaded flow records'} aside={showingSample ? <Link to="/threat-investigation">Inspect samples <ArrowRight size={14} /></Link> : <span className="tag">Validation only</span>}>
        {showingSample
          ? <FlowTable />
          : <div className="dashboard-empty"><Empty title="No prediction records">The validation receipt stores only file metadata, not raw rows or classification results. Open Traffic Analyzer to review the current upload preview.</Empty><Link className="quiet-link" to="/traffic-analyzer">Open Traffic Analyzer <ArrowRight size={15} /></Link></div>}
      </Panel>

      <Panel title="Connection atlas" className="atlas-panel"><NetworkMap compact /></Panel>
    </div>
  </>;
}
