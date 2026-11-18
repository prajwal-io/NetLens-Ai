import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, RefreshCw, Upload } from 'lucide-react';
import { useAnalysis, setAnalysis } from '../services/analysis';
import { AnalysisWorkspace } from '../components/AnalysisWorkspace';
import { Empty } from '../components/ui';
import { api, type Analysis, type Health, type HistoryPage, type ModelInfo } from '../services/api';

function TrafficMix({ normal, malicious, label }: { normal: number; malicious: number; label: string }) {
  const total = normal + malicious;
  const normalShare = total ? normal / total * 100 : 0;
  const maliciousShare = total ? malicious / total * 100 : 0;
  return <>
    <div className="traffic-mix-bar" role="img" aria-label={`${label}: ${normal.toLocaleString()} normal and ${malicious.toLocaleString()} malicious flows`}>
      <span className="traffic-mix-normal" style={{ width: `${normalShare}%` }}/>
      <span className="traffic-mix-malicious" style={{ width: `${maliciousShare}%` }}/>
    </div>
    <div className="traffic-mix-legend">
      <span><i className="traffic-key-normal"/>Normal <strong>{normal.toLocaleString()}</strong></span>
      <span><i className="traffic-key-malicious"/>Malicious <strong>{malicious.toLocaleString()}</strong></span>
      <span>Total <strong>{total.toLocaleString()}</strong></span>
    </div>
  </>;
}

function ReadinessStrip({ health, model, loading, error }: { health: Health | null; model: ModelInfo | null; loading: boolean; error: string }) {
  const apiLabel = health?.status === 'ok' ? 'Connected' : health ? 'Unavailable' : 'Checking';
  const modelLabel = !health?.model_loaded ? 'Not loaded' : model?.model_name ?? (loading ? 'Loading evidence' : error ? 'Metadata unavailable' : 'Unavailable');
  return <section className="dashboard-readiness" aria-label="Live backend and model configuration">
    <div><span>API</span><strong className={health?.status === 'ok' ? 'readiness-good' : 'readiness-warning'}>{apiLabel}</strong></div>
    <div><span>Classifier</span><strong>{model ? `${model.algorithm} · ${model.model_version}` : modelLabel}</strong></div>
    <div><span>Benchmark</span><strong>{model ? `${model.dataset.name} · ${model.dataset.rows.toLocaleString()} flows` : 'No model metadata'}</strong></div>
    <div><span>Input schema</span><strong>{model ? `${model.feature_count} flow features` : 'Unavailable'}</strong></div>
    <div><span>Decision cutoff</span><strong>{model ? `${(model.decision_threshold * 100).toFixed(1)}% score` : 'Unavailable'}</strong></div>
  </section>;
}

function MetricChart({ model, loading, error, retry }: { model: ModelInfo | null; loading: boolean; error: string; retry: () => void }) {
  if (error) return <p className="dashboard-chart-state" role="alert">{error} <button type="button" onClick={retry}>Retry</button></p>;
  if (loading) return <p className="dashboard-chart-state" role="status">Loading held-out benchmark results…</p>;
  if (!model) return <p className="dashboard-chart-state">Model evaluation appears here when a trained pipeline is available.</p>;

  const metrics: { label: string; value?: number; tone?: string }[] = [
    { label: 'Accuracy', value: model.evaluation.metrics.accuracy },
    { label: 'Precision', value: model.evaluation.metrics.precision },
    { label: 'Malicious recall', value: model.evaluation.metrics.recall },
    { label: 'F1 score', value: model.evaluation.metrics.f1 },
    { label: 'False-positive rate', value: model.evaluation.metrics.false_positive_rate, tone: 'risk' },
  ];
  const labels = model.evaluation.metrics.confusion_matrix.labels;
  const normalIndex = labels.indexOf('normal');
  const maliciousIndex = labels.indexOf('malicious');
  const falseAlerts = normalIndex >= 0 && maliciousIndex >= 0
    ? model.evaluation.metrics.confusion_matrix.rows_actual_columns_predicted[normalIndex]?.[maliciousIndex]
    : undefined;
  const policyLimit = model.threshold_policy.maximum_validation_false_positive_rate;

  return <>
    <p className="dashboard-chart-note">{model.dataset.name} official test partition · {model.evaluation.rows.toLocaleString()} flows</p>
    <div className="metric-chart" aria-label="Held-out model evaluation metrics">
      {metrics.map(({ label, value, tone }) => {
        const percentage = typeof value === 'number' && Number.isFinite(value) ? Math.max(0, Math.min(100, value * 100)) : null;
        return <div className="metric-chart-row" key={label}>
          <span>{label}</span>
          {percentage === null ? <span className="metric-not-reported">Not reported</span> : <div className="metric-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(percentage)}>
            <span className={tone === 'risk' ? 'metric-fill metric-fill-risk' : 'metric-fill'} style={{ width: `${percentage}%` }}/>
          </div>}
          <strong>{percentage === null ? '—' : `${percentage.toFixed(1)}%`}</strong>
        </div>;
      })}
    </div>
    <p className="dashboard-chart-foot">Validation target: ≤ {(policyLimit * 100).toFixed(1)}% false-positive rate. Held-out false alerts: {falseAlerts?.toLocaleString() ?? 'not reported'}. Review the unseen-signature result before interpreting performance.</p>
  </>;
}

function HistoryChart({ history }: { history: HistoryPage | null }) {
  const items = history?.items.slice(0, 5) ?? [];
  const max = Math.max(1, ...items.map((item) => item.total_flows));
  if (!history || items.length === 0) return <p className="dashboard-chart-state">Saved classification totals will appear after the first analysis.</p>;
  return <>
    <p className="dashboard-chart-note">Last {items.length} saved {items.length === 1 ? 'analysis' : 'analyses'} · historical results, not live traffic</p>
    <ul className="history-chart">
      {items.map((item) => {
        const normal = item.counts.normal;
        const malicious = item.counts.malicious;
        const width = item.total_flows / max * 100;
        const normalShare = normal / item.total_flows * width;
        const maliciousShare = malicious / item.total_flows * width;
        return <li key={item.analysis_id}>
          <span className="history-chart-label" title={item.filename}>{item.filename}</span>
          <div className="history-chart-track" role="img" aria-label={`${item.filename}: ${normal.toLocaleString()} normal, ${malicious.toLocaleString()} malicious flows`}>
            <span className="traffic-mix-normal" style={{ width: `${normalShare}%` }}/><span className="traffic-mix-malicious" style={{ width: `${maliciousShare}%` }}/>
          </div>
          <strong>{item.total_flows.toLocaleString()}</strong>
        </li>;
      })}
    </ul>
    <div className="traffic-mix-legend history-chart-legend"><span><i className="traffic-key-normal"/>Normal</span><span><i className="traffic-key-malicious"/>Malicious</span></div>
  </>;
}

function CurrentAnalysisChart({ analysis }: { analysis: Analysis }) {
  return <section className="dashboard-current" aria-labelledby="current-analysis-heading">
    <div className="dashboard-section-heading">
      <div><p className="dashboard-eyebrow">SELECTED ANALYSIS</p><h2 id="current-analysis-heading">Traffic classification</h2><p>{analysis.filename} · {analysis.source_type === 'historical_replay' ? 'Historical replay' : 'Uploaded CSV'}</p></div>
      <span className="tag">Actual model output · {analysis.model_version}</span>
    </div>
    <TrafficMix normal={analysis.counts.normal} malicious={analysis.counts.malicious} label="Selected analysis"/>
    <p className="dashboard-chart-foot">Decision cutoff {(analysis.threshold * 100).toFixed(1)}% · {analysis.source_type === 'historical_replay' ? 'Replay data, not live monitoring' : 'Uploaded flow data'} · {analysis.score_definition}</p>
  </section>;
}

function RecentAnalyses({ history, loading, error, busy, onOpen, onRefresh }: { history: HistoryPage | null; loading: boolean; error: string; busy: string; onOpen: (id: string) => void; onRefresh: () => void }) {
  return <section className="recent-analyses" aria-labelledby="recent-analyses-heading">
    <div className="recent-analyses-heading">
      <div><h2 id="recent-analyses-heading">Recent analyses</h2><p>Saved results from this workspace.</p></div>
      <button type="button" className="quiet-button" aria-label="Refresh recent analyses" disabled={loading} onClick={onRefresh}><RefreshCw size={15} className={loading ? 'spin' : ''}/> Refresh</button>
    </div>
    {error && <p className="recent-analyses-error" role="alert">{error}</p>}
    {loading && !history && <p className="recent-analyses-state" role="status">Loading saved analyses…</p>}
    {!loading && !error && history?.items.length === 0 && <div className="recent-analyses-empty">
      <Empty title="No saved analyses yet">Upload a CSV or run a historical replay to create the first result.</Empty>
      <div><Link to="/traffic-analyzer">Analyze a CSV <ArrowRight size={14}/></Link><Link to="/network-pulse">Run historical replay <ArrowRight size={14}/></Link></div>
    </div>}
    {history?.items.length ? <ul className="recent-analyses-list">
      {history.items.slice(0, 4).map((item) => <li key={item.analysis_id}>
        <div className="recent-analysis-file"><strong title={item.filename}>{item.filename}</strong><span>{item.source_type === 'historical_replay' ? 'Historical replay' : 'Uploaded CSV'} · {new Date(item.created_at).toLocaleString()}</span></div>
        <div className="recent-analysis-total"><span>Flows</span><strong>{item.total_flows.toLocaleString()}</strong></div>
        <div className="recent-analysis-alerts"><span>Malicious</span><strong>{item.counts.malicious.toLocaleString()}</strong></div>
        <button type="button" disabled={!!busy} onClick={() => onOpen(item.analysis_id)}>{busy === item.analysis_id ? 'Opening…' : 'Open'} <ArrowRight size={14}/><span className="sr-only"> {item.filename}</span></button>
      </li>)}
    </ul> : null}
  </section>;
}

export default function Dashboard({ health }: { health: Health | null }) {
  const analysis = useAnalysis();
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [modelError, setModelError] = useState('');
  const [modelAttempt, setModelAttempt] = useState(0);
  const [history, setHistory] = useState<HistoryPage | null>(null);
  const [historyError, setHistoryError] = useState('');
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyAttempt, setHistoryAttempt] = useState(0);
  const [busy, setBusy] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setHistoryLoading(true);
    void api.history(0, controller.signal).then((result) => { setHistory(result); setHistoryError(''); })
      .catch((reason) => { if (!controller.signal.aborted) setHistoryError(reason instanceof Error ? reason.message : 'Saved analyses are unavailable.'); })
      .finally(() => { if (!controller.signal.aborted) setHistoryLoading(false); });
    return () => controller.abort();
  }, [historyAttempt]);

  useEffect(() => {
    if (!health?.model_loaded) { setModel(null); setModelError(''); return; }
    const controller = new AbortController();
    void api.modelInfo(controller.signal).then((result) => { setModel(result); setModelError(''); })
      .catch((reason) => { if (!controller.signal.aborted) setModelError(reason instanceof Error ? reason.message : 'Model results are unavailable.'); });
    return () => controller.abort();
  }, [health?.model_loaded, health?.model_version, modelAttempt]);

  async function open(id: string) {
    setBusy(id); setHistoryError('');
    try { setAnalysis(await api.analysis(id)); }
    catch (reason) { setHistoryError(reason instanceof Error ? reason.message : 'Could not open this analysis.'); }
    finally { setBusy(''); }
  }

  const loadingModel = !!health?.model_loaded && !model && !modelError;

  return <>
    <section className="dashboard-actions" aria-label="Analysis actions">
      <div><p className="dashboard-eyebrow">COMMAND CENTER</p><h2>Start with the traffic.</h2><p>Validate flow data, run the evaluated model, then follow the results.</p></div>
      <div className="dashboard-action-links"><Link className="primary" to="/traffic-analyzer"><Upload size={16}/> Analyze a CSV</Link><Link to="/network-pulse">Run historical replay <ArrowRight size={15}/></Link></div>
    </section>
    <ReadinessStrip health={health} model={model} loading={loadingModel} error={modelError}/>
    {analysis && <CurrentAnalysisChart analysis={analysis}/>}
    {analysis && <AnalysisWorkspace analysis={analysis} mode="Command Center"/>}
    <div className="dashboard-chart-grid">
      <section className="dashboard-chart-panel" aria-labelledby="benchmark-chart-heading">
        <div className="dashboard-section-heading"><div><p className="dashboard-eyebrow">MODEL EVIDENCE</p><h2 id="benchmark-chart-heading">Held-out test results</h2></div><span className={`tag ${health?.model_loaded ? 'green' : 'red'}`}>{health?.model_loaded ? 'Pipeline ready' : 'Model unavailable'}</span></div>
        <MetricChart model={model} loading={loadingModel} error={modelError} retry={() => { setModelError(''); setModelAttempt((value) => value + 1); }}/>
        <Link className="dashboard-detail-link" to="/model-lab">Review evaluation details <ArrowRight size={14}/></Link>
      </section>
      <section className="dashboard-chart-panel" aria-labelledby="history-chart-heading">
        <div className="dashboard-section-heading"><div><p className="dashboard-eyebrow">WORKSPACE HISTORY</p><h2 id="history-chart-heading">Recent traffic mix</h2></div></div>
        {historyLoading && !history ? <p className="dashboard-chart-state" role="status">Loading saved traffic…</p> : historyError ? <p className="dashboard-chart-state" role="alert">{historyError}</p> : <HistoryChart history={history}/>}
      </section>
    </div>
    <RecentAnalyses history={history} loading={historyLoading} error={historyError} busy={busy} onOpen={(id) => void open(id)} onRefresh={() => setHistoryAttempt((value) => value + 1)}/>
  </>;
}
