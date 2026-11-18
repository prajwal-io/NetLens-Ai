import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, downloadReport, type Analysis, type PredictionPreview, type ResponseDecision } from '../services/api';
import { FlowExperience } from './FlowExperience';
import { Panel } from './ui';

type WorkspaceMode = 'Command Center' | 'Network Pulse' | 'Threat Investigation' | 'Reports';

export function AnalysisWorkspace({ analysis, mode }: { analysis: Analysis; mode: WorkspaceMode }) {
  const [label, setLabel] = useState<'all' | 'normal' | 'malicious'>('all');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<'row' | 'score'>('row');
  const [page, setPage] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [decisions, setDecisions] = useState<ResponseDecision[]>([]);
  const [decisionLoading, setDecisionLoading] = useState(mode === 'Command Center' || mode === 'Threat Investigation');
  const [decisionError, setDecisionError] = useState('');
  const [decisionBusy, setDecisionBusy] = useState<number | null>(null);
  const [decisionAttempt, setDecisionAttempt] = useState(0);
  const normalizedQuery = query.trim().toLowerCase();
  const rows = analysis.predictions
    .filter((row) => (label === 'all' || row.label === label)
      && (!normalizedQuery || [row.row_id, row.label, row.source, row.destination, row.timestamp].join(' ').toLowerCase().includes(normalizedQuery)))
    .sort((first, second) => sort === 'score' ? second.malicious_score - first.malicious_score : first.row_id - second.row_id);
  const pageCount = Math.max(1, Math.ceil(rows.length / 50));
  const safePage = Math.min(page, pageCount - 1);
  const decisionByRow = new Map(decisions.map((decision) => [decision.row_id, decision]));
  const reviewQueue = analysis.predictions.filter((row) => row.label === 'malicious')
    .sort((first, second) => second.malicious_score - first.malicious_score).slice(0, 3);
  const validationBudget = analysis.model_context?.threshold_policy?.maximum_validation_false_positive_rate;

  useEffect(() => {
    if (mode !== 'Threat Investigation' && mode !== 'Command Center') return;
    const controller = new AbortController();
    setDecisions([]); setDecisionError(''); setDecisionLoading(true);
    void api.responseDecisions(analysis.analysis_id, controller.signal)
      .then(setDecisions)
      .catch((reason) => { if (!controller.signal.aborted) setDecisionError(reason instanceof Error ? reason.message : 'Could not load analyst decisions.'); })
      .finally(() => { if (!controller.signal.aborted) setDecisionLoading(false); });
    return () => controller.abort();
  }, [mode, analysis.analysis_id, decisionAttempt]);

  async function download(format: 'csv' | 'pdf') {
    setExporting(true); setError('');
    try { await downloadReport(analysis.analysis_id, format); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Export failed. Please retry.'); }
    finally { setExporting(false); }
  }

  async function decide(rowId: number, decision?: ResponseDecision['decision']) {
    setDecisionBusy(rowId); setDecisionError('');
    try {
      if (decision) {
        const saved = await api.setResponseDecision(analysis.analysis_id, rowId, decision);
        setDecisions((current) => [...current.filter((item) => item.row_id !== rowId), saved].sort((a, b) => a.row_id - b.row_id));
      } else {
        await api.clearResponseDecision(analysis.analysis_id, rowId);
        setDecisions((current) => current.filter((item) => item.row_id !== rowId));
      }
    } catch (reason) {
      setDecisionError(reason instanceof Error ? reason.message : 'Could not save the analyst decision.');
    } finally { setDecisionBusy(null); }
  }

  return <>
    <Panel title={mode === 'Command Center' ? 'Continue this analysis' : `${mode}: ${analysis.source_type === 'historical_replay' ? 'historical replay' : 'uploaded analysis'}`} aside={<span className="tag">Actual ML prediction</span>}>
      <p style={{ overflowWrap: 'anywhere' }}>{mode === 'Command Center' ? `Analysis ${analysis.analysis_id}` : `${analysis.filename} · ${analysis.model_version} · Analysis ${analysis.analysis_id}`}</p>
      {mode !== 'Command Center' && <div className="analysis-summary" role="status">
        <div><span>Total flows</span><strong>{analysis.total_flows.toLocaleString()}</strong></div>
        <div><span>Normal</span><strong>{analysis.counts.normal.toLocaleString()}</strong></div>
        <div><span>Malicious</span><strong>{analysis.counts.malicious.toLocaleString()}</strong></div>
        <div><span>Threshold</span><strong>{analysis.threshold.toFixed(4)}</strong></div>
      </div>}
      <p>{analysis.message}</p>
      <p className="fine">Saved {new Date(analysis.created_at).toLocaleString()} · {analysis.source_type === 'historical_replay' ? 'Historical replay, not live traffic' : 'Uploaded analysis'}</p>
      {mode === 'Command Center' && <div className="analysis-result-actions" aria-label="Continue this analysis">
        <Link to="/network-pulse">Explore traffic flows</Link><Link to="/threat-investigation">Investigate classifications</Link><Link to="/reports">Export this analysis</Link>
      </div>}
      {mode === 'Reports' && <div className="analysis-result-actions"><button className="primary" disabled={exporting} onClick={() => void download('csv')}>Export classification CSV</button><button disabled={exporting} onClick={() => void download('pdf')}>Download PDF report</button>{exporting && <span role="status">Preparing report...</span>}</div>}
      {error && <p role="alert">{error}</p>}
      {mode === 'Network Pulse' && <FlowExperience key={analysis.analysis_id} analysis={analysis}/>}
    </Panel>

    {mode === 'Command Center' && <section className="command-review-queue" aria-labelledby="command-review-heading">
      <div className="command-review-heading"><div><p className="dashboard-eyebrow">IDS REVIEW QUEUE</p><h3 id="command-review-heading">Model-flagged flows</h3><p>{analysis.counts.malicious.toLocaleString()} classified as malicious · highest scores first</p></div><Link to="/threat-investigation">Open investigation <span aria-hidden="true">→</span></Link></div>
      {decisionLoading && <p className="command-review-state" role="status">Loading saved analyst responses…</p>}
      {decisionError && <p className="command-review-error" role="alert">{decisionError} <button type="button" onClick={() => setDecisionAttempt((attempt) => attempt + 1)}>Retry</button></p>}
      {reviewQueue.length ? <ul className="command-review-list">{reviewQueue.map((row) => {
        const decision = decisionByRow.get(row.row_id);
        return <li key={row.row_id}>
          <div className="command-review-flow"><span className="command-review-row">FLOW {row.row_id}</span><strong>{row.source && row.destination ? `${row.source} → ${row.destination}` : row.timestamp ?? 'Flow record'}</strong></div>
          <span className="command-review-score">Score {row.malicious_score.toFixed(4)}</span>
          <span className={`review-status ${decision ? 'recorded' : decisionLoading || decisionError ? 'unavailable' : 'pending'}`}>{decision?.decision === 'simulated_block' ? 'Simulated response saved' : decision?.decision === 'dismissed' ? 'Alert dismissed' : decisionLoading ? 'Loading response' : decisionError ? 'Response status unavailable' : 'Needs analyst review'}</span>
        </li>;
      })}</ul> : !decisionLoading && <p className="command-review-state">No flows were classified as malicious in this analysis.</p>}
      <p className="command-review-disclaimer">Scores are model estimates, not proof of an attack. Simulated response decisions do not block live traffic.</p>
    </section>}

    {mode === 'Command Center' && analysis.model_context?.evaluation && <details className="model-reliability"><summary>Held-out model tradeoff</summary><p>Precision: {(analysis.model_context.evaluation.precision * 100).toFixed(2)}% · malicious recall: {(analysis.model_context.evaluation.recall * 100).toFixed(2)}% · false-positive rate: {((analysis.model_context.evaluation.false_positive_rate ?? (analysis.model_context.evaluation.confusion_matrix.rows_actual_columns_predicted[0][1] / analysis.model_context.evaluation.support.normal)) * 100).toFixed(2)}%.</p><p>The saved model threshold maximizes malicious recall{typeof validationBudget === 'number' && Number.isFinite(validationBudget) ? ` within a ${(validationBudget * 100).toFixed(1)}% validation false-positive target` : ' under its validation policy'}. Held-out performance can differ on uploaded traffic. Scores are not proof of an attack.</p></details>}

    {mode === 'Threat Investigation' && <Panel title="Classified flow records">
      <p className="ips-simulation-note">Simulated IPS actions are saved with this analysis. They do not block live traffic or change firewall settings.</p>
      {decisionLoading && <p role="status">Loading saved analyst decisions…</p>}
      {decisionError && <p role="alert">{decisionError} <button type="button" onClick={() => setDecisionAttempt((attempt) => attempt + 1)}>Retry decisions</button></p>}
      <div className="investigation-filters">
        <label>Search flows <input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); }} placeholder="Row, address, or time" /></label>
        <label>Classification <select value={label} onChange={(event) => { setLabel(event.target.value as typeof label); setPage(0); }}><option value="all">All</option><option value="normal">Normal</option><option value="malicious">Malicious</option></select></label>
        <label>Order by <select value={sort} onChange={(event) => { setSort(event.target.value as typeof sort); setPage(0); }}><option value="row">Source row</option><option value="score">Highest score</option></select></label>
      </div>
      <div className="table-scroll analysis-table-scroll" tabIndex={0} role="region" aria-label="Actual classified flow records">
        <table><caption>{rows.length.toLocaleString()} matching flows; page {safePage + 1} of {pageCount}</caption><thead><tr><th scope="col">Row</th><th scope="col">Classification</th><th scope="col">Malicious score</th><th scope="col">Available features</th><th scope="col">Analyst response</th></tr></thead>
          <tbody>{rows.slice(safePage * 50, (safePage + 1) * 50).map((row) => {
            const decision = decisionByRow.get(row.row_id);
            return <tr key={row.row_id}><th scope="row">{row.row_id}</th><td>{row.label}</td><td>{row.malicious_score.toFixed(4)}</td><td><FlowDetails analysisId={analysis.analysis_id} rowId={row.row_id}/></td><td>{row.label !== 'malicious' ? '—' : decision ? <div className="ips-decision"><strong>{decision.decision === 'simulated_block' ? 'Simulated block approved' : 'Alert dismissed'}</strong><small>{new Date(decision.decided_at).toLocaleString()}</small><button type="button" disabled={decisionBusy !== null || decisionLoading || !!decisionError} onClick={() => void decide(row.row_id)} aria-label={`Undo IPS decision for row ${row.row_id}`}>Undo</button></div> : <div className="ips-decision-actions"><button type="button" disabled={decisionBusy !== null || decisionLoading || !!decisionError} onClick={() => void decide(row.row_id, 'simulated_block')} aria-label={`Approve simulated block for row ${row.row_id}`}>{decisionBusy === row.row_id ? 'Saving…' : 'Approve simulated block'}</button><button type="button" disabled={decisionBusy !== null || decisionLoading || !!decisionError} onClick={() => void decide(row.row_id, 'dismissed')} aria-label={`Dismiss alert for row ${row.row_id}`}>Dismiss alert</button></div>}</td></tr>;
          })}</tbody></table>
      </div>
      {!rows.length && <p role="status">No classifications match this filter.</p>}
      <div className="analysis-result-actions"><button disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>Previous</button><button disabled={safePage + 1 >= pageCount} onClick={() => setPage(safePage + 1)}>Next</button></div>
      <p className="fine">{analysis.score_definition}. Model classifications are review signals, not proof of an attack.</p>
    </Panel>}
  </>;
}

function FlowDetails({ analysisId, rowId }: { analysisId: string; rowId: number }) {
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<PredictionPreview | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController(); setError(''); setResult(null);
    void api.flow(analysisId, rowId, controller.signal).then(setResult).catch(reason => { if (!controller.signal.aborted) setError(reason.message); });
    return () => controller.abort();
  }, [open, analysisId, rowId, retry]);
  return <details onToggle={event => setOpen(event.currentTarget.open)}><summary>Inspect features<span className="sr-only"> for row {rowId}</span></summary>{error ? <><p role="alert">{error}</p><button onClick={() => setRetry(value => value + 1)}>Retry features</button></> : result ? <><p>{result.source ?? 'Source not provided'} → {result.destination ?? 'Destination not provided'} · {result.timestamp ?? 'Time not provided'}</p><dl>{Object.entries(result.features).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value ?? 'Missing / imputed')}</dd></div>)}</dl></> : <p role="status">Loading flow features...</p>}</details>;
}
