import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, downloadReport, type Analysis, type PredictionPreview } from '../services/api';
import { FlowExperience } from './FlowExperience';
import { Panel } from './ui';

export function AnalysisWorkspace({ analysis, mode }: { analysis: Analysis; mode: string }) {
  const [label, setLabel] = useState('all');
  const [page, setPage] = useState(0);
  const rows = analysis.predictions.filter((row) => label === 'all' || row.label === label);
  const pageCount = Math.max(1, Math.ceil(rows.length / 50));
  const safePage = Math.min(page, pageCount - 1);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  async function download(format: 'csv' | 'pdf') {
    setExporting(true); setError('');
    try { await downloadReport(analysis.analysis_id, format); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Export failed. Please retry.'); }
    finally { setExporting(false); }
  }
  return <>
    <Panel title={`${mode}: ${analysis.source_type === 'historical_replay' ? 'historical replay' : 'uploaded analysis'}`} aside={<span className="tag">Actual ML prediction</span>}>
      <p style={{ overflowWrap: 'anywhere' }}>{analysis.filename} · {analysis.model_version} · Analysis {analysis.analysis_id}</p>
      <div className="analysis-summary" role="status">
        <div><span>Total flows</span><strong>{analysis.total_flows.toLocaleString()}</strong></div>
        <div><span>Normal</span><strong>{analysis.counts.normal.toLocaleString()}</strong></div>
        <div><span>Malicious</span><strong>{analysis.counts.malicious.toLocaleString()}</strong></div>
        <div><span>Threshold</span><strong>{analysis.threshold.toFixed(4)}</strong></div>
      </div>
      <p>{analysis.message}</p>
      <p className="fine">Saved {new Date(analysis.created_at).toLocaleString()} &middot; {analysis.source_type === 'historical_replay' ? 'Historical replay, not live traffic' : 'Uploaded analysis'}</p>
      {analysis.model_context?.evaluation && <details className="model-reliability"><summary>Model reliability and alert tradeoff</summary><p>Held-out precision: {(analysis.model_context.evaluation.precision * 100).toFixed(2)}%. Malicious recall: {(analysis.model_context.evaluation.recall * 100).toFixed(2)}%. False-positive rate: {((analysis.model_context.evaluation.false_positive_rate ?? (analysis.model_context.evaluation.confusion_matrix.rows_actual_columns_predicted[0][1] / analysis.model_context.evaluation.support.normal)) * 100).toFixed(2)}%.</p><p>The threshold maximizes recall within a 5% validation false-positive budget. Held-out performance differs; this is not a guarantee for uploaded traffic. Scores are model estimates, not proof of an attack.</p></details>}
      {error && <p role="alert">{error}</p>}
      {mode === 'Reports' && <div className="analysis-result-actions"><button className="primary" disabled={exporting} onClick={() => void download('csv')}>Export classification CSV</button><button disabled={exporting} onClick={() => void download('pdf')}>Download PDF report</button>{exporting && <span role="status">Preparing report...</span>}</div>}
      {mode === 'Network Pulse' && <FlowExperience key={analysis.analysis_id} analysis={analysis}/>}
      <nav className="analysis-result-actions" aria-label="Analysis workflow">
        <Link to="/command-center">Command Center</Link> · <Link to="/network-pulse">Network Pulse</Link> · <Link to="/traffic-analyzer">Traffic Analyzer</Link> · <Link to="/threat-investigation">Threat Investigation</Link> · <Link to="/reports">Reports</Link>
      </nav>
    </Panel>
    <Panel title="Classified flow records">
      <label>Classification <select aria-label="Classification" value={label} onChange={(event) => { setLabel(event.target.value); setPage(0); }}><option value="all">All</option><option value="normal">Normal</option><option value="malicious">Malicious</option></select></label>
      <div className="table-scroll analysis-table-scroll" tabIndex={0} role="region" aria-label="Uploaded predictions">
        <table><caption>{rows.length.toLocaleString()} matching flows; page {safePage + 1} of {pageCount}</caption><thead><tr><th scope="col">Row</th><th scope="col">Classification</th><th scope="col">Malicious score</th><th scope="col">Available features</th></tr></thead>
          <tbody>{rows.slice(safePage * 50, (safePage + 1) * 50).map((row) => <tr key={row.row_id}><th scope="row">{row.row_id}</th><td>{row.label}</td><td>{row.malicious_score.toFixed(4)}</td><td>{<FlowDetails analysisId={analysis.analysis_id} rowId={row.row_id}/>}</td></tr>)}</tbody></table>
      </div>
      {!rows.length && <p role="status">No classifications match this filter.</p>}
      <div className="analysis-result-actions"><button disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>Previous</button><button disabled={safePage + 1 >= pageCount} onClick={() => setPage(safePage + 1)}>Next</button></div>
      <p className="fine">{analysis.score_definition}. Results are saved locally. Open or delete them in Saved analyses.</p>
    </Panel>
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
  return <details onToggle={event => setOpen(event.currentTarget.open)}><summary>Inspect features<span className="sr-only"> for row {rowId}</span></summary>{error ? <><p role="alert">{error}</p><button onClick={() => setRetry(value => value + 1)}>Retry features</button></> : result ? <><p>{result.source ?? 'Source not provided'} &rarr; {result.destination ?? 'Destination not provided'} &middot; {result.timestamp ?? 'Time not provided'}</p><dl>{Object.entries(result.features).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value ?? 'Missing / imputed')}</dd></div>)}</dl></> : <p role="status">Loading flow features...</p>}</details>;
}
