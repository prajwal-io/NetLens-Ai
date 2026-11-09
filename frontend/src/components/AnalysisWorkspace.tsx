import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Analysis } from '../services/api';
import { Panel } from './ui';

export function AnalysisWorkspace({ analysis, mode }: { analysis: Analysis; mode: string }) {
  const [label, setLabel] = useState('all');
  const [page, setPage] = useState(0);
  const rows = analysis.predictions.filter((row) => label === 'all' || row.label === label);
  const pageCount = Math.max(1, Math.ceil(rows.length / 50));
  const safePage = Math.min(page, pageCount - 1);
  function download() {
    const csv = ['row_id,label,malicious_score', ...analysis.predictions.map((row) => `${row.row_id},${row.label},${row.malicious_score}`)].join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url; link.download = `netsight-${analysis.analysis_id}.csv`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <>
    <Panel title={`${mode}: uploaded analysis`} aside={<span className="tag">Actual ML prediction</span>}>
      <p style={{ overflowWrap: 'anywhere' }}>{analysis.filename} · {analysis.model_version} · Analysis {analysis.analysis_id}</p>
      <div className="analysis-summary" role="status">
        <div><span>Total flows</span><strong>{analysis.total_flows.toLocaleString()}</strong></div>
        <div><span>Normal</span><strong>{analysis.counts.normal.toLocaleString()}</strong></div>
        <div><span>Malicious</span><strong>{analysis.counts.malicious.toLocaleString()}</strong></div>
        <div><span>Threshold</span><strong>{analysis.threshold.toFixed(4)}</strong></div>
      </div>
      <p>{analysis.message}</p>
      {mode === 'Reports' && <button className="primary" onClick={download}>Export classification CSV</button>}
      {mode === 'Network Pulse' && <p>No device relationships or time series can be drawn from this model schema: source/destination addresses and timestamps are not provided. These are uploaded flow classifications, not live monitoring.</p>}
      <nav className="analysis-result-actions" aria-label="Analysis workflow">
        <Link to="/command-center">Command Center</Link> · <Link to="/network-pulse">Network Pulse</Link> · <Link to="/traffic-analyzer">Traffic Analyzer</Link> · <Link to="/threat-investigation">Threat Investigation</Link> · <Link to="/reports">Reports</Link>
      </nav>
    </Panel>
    <Panel title="Classified flow records">
      <label>Classification <select aria-label="Classification" value={label} onChange={(event) => { setLabel(event.target.value); setPage(0); }}><option value="all">All</option><option value="normal">Normal</option><option value="malicious">Malicious</option></select></label>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Uploaded predictions">
        <table><caption>{rows.length.toLocaleString()} matching flows; page {safePage + 1} of {pageCount}</caption><thead><tr><th scope="col">Row</th><th scope="col">Classification</th><th scope="col">Malicious score</th><th scope="col">Available features</th></tr></thead>
          <tbody>{rows.slice(safePage * 50, (safePage + 1) * 50).map((row) => <tr key={row.row_id}><th scope="row">{row.row_id}</th><td>{row.label}</td><td>{row.malicious_score.toFixed(4)}</td><td>{analysis.preview.find((preview) => preview.row_id === row.row_id) ? <details><summary>Inspect features</summary><dl>{Object.entries(analysis.preview.find((preview) => preview.row_id === row.row_id)!.features).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value ?? 'Missing / imputed')}</dd></div>)}</dl></details> : 'Feature preview not returned for this row'}</td></tr>)}</tbody></table>
      </div>
      {!rows.length && <p role="status">No classifications match this filter.</p>}
      <div className="analysis-result-actions"><button disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>Previous</button><button disabled={safePage + 1 >= pageCount} onClick={() => setPage(safePage + 1)}>Next</button></div>
      <p className="fine">{analysis.score_definition}. Results stay in this tab until reload or replacement by another upload.</p>
    </Panel>
  </>;
}
