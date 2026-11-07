import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownToLine, ArrowRight, CheckCircle2, Download, FileText, Upload, X } from 'lucide-react';
import { Panel, Empty } from '../components/ui';
import { ContextNote } from '../components/WorkspaceDetails';
import { api, type Analysis, type FeatureSchema, type Health, type Validation } from '../services/api';
import { useReceipts } from '../services/receipts';

const uploadLimit = 5 * 1024 * 1024;
function fileError(file: File) {
  if (!file.name.toLowerCase().endsWith('.csv')) return 'Choose a file with a .csv extension.';
  if (file.size === 0) return 'This file is empty. Choose a CSV containing network-flow records.';
  if (file.size > uploadLimit) return 'This file exceeds 5 MiB. Choose a smaller CSV.';
  return '';
}

function readableSize(size: number) {
  return size < 1024 ? `${size} bytes` : `${(size / 1024).toFixed(1)} KiB`;
}

function csvCell(value: string | number) {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function downloadAnalysis(analysis: Analysis) {
  const content = [
    ['row_id', 'label', 'malicious_score', 'decision_threshold', 'model_version', 'source_file'],
    ...analysis.predictions.map((prediction) => [prediction.row_id, prediction.label, prediction.malicious_score.toFixed(6), analysis.threshold.toFixed(4), analysis.model_version, analysis.filename]),
  ].map((row) => row.map(csvCell).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `netsight-${analysis.analysis_id.slice(0, 8)}-predictions.csv`;
  try { document.body.append(link); link.click(); } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
}

export default function Analyzer({ health }: { health: Health | null }) {
  const { addReceipt } = useReceipts();
  const [featureSchema, setFeatureSchema] = useState<FeatureSchema | null>(null);
  const [schemaError, setSchemaError] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Validation | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState('');
  const [action, setAction] = useState<'validate' | 'analyze' | null>(null);
  const [progress, setProgress] = useState(0);
  const [notice, setNotice] = useState('');
  const [downloadNotice, setDownloadNotice] = useState('');
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const controller = useRef<AbortController | null>(null);
  const busy = action !== null;

  useEffect(() => {
    const request = new AbortController();
    void api.featureSchema(request.signal).then(setFeatureSchema).catch((reason) => {
      if (!request.signal.aborted) setSchemaError((reason as Error).message || 'Could not load the model input schema.');
    });
    return () => request.abort();
  }, []);

  useEffect(() => () => controller.current?.abort(), []);

  function choose(next?: File) {
    if (controller.current) return;
    setResult(null);
    setAnalysis(null);
    setNotice('');
    setDownloadNotice('');
    setFile(next ?? null);
    setError(next ? fileError(next) : '');
    setProgress(0);
    setDragging(false);
  }

  function removeFile() {
    choose(undefined);
    if (input.current) input.current.value = '';
  }

  async function processRequest(kind: 'validate' | 'analyze') {
    if (!file || !featureSchema || fileError(file) || controller.current || (kind === 'analyze' && !result)) return;
    const request = new AbortController();
    controller.current = request;
    setAction(kind);
    setError('');
    setNotice('');
    setDownloadNotice('');
    setProgress(0);
    if (kind === 'validate') { setResult(null); setAnalysis(null); }
    try {
      if (kind === 'validate') {
        const validation = await api.validate(file, { signal: request.signal, onProgress: setProgress });
        if (!request.signal.aborted) {
          setResult(validation);
          addReceipt(validation);
        }
      } else {
        const next = await api.analyze(file, { signal: request.signal, onProgress: setProgress });
        if (!request.signal.aborted) setAnalysis(next);
      }
    } catch (reason) {
      if ((reason as Error).name === 'AbortError') setNotice(`${kind === 'validate' ? 'Validation' : 'Analysis'} cancelled. You can retry or choose another file.`);
      else setError((reason as Error).message || `${kind === 'validate' ? 'CSV validation' : 'Traffic analysis'} failed. Please retry.`);
    } finally {
      if (controller.current === request) {
        controller.current = null;
        setAction(null);
      }
    }
  }

  const currentStep = analysis ? 3 : result ? 2 : file && !fileError(file) ? 1 : 1;
  const requiredColumns = featureSchema?.features ?? [];
  const extraColumns = result?.columns.filter((column) => !requiredColumns.includes(column)) ?? [];

  return <>
    <ContextNote>Validate compatible network-flow features with FastAPI, then run the evaluated UNSW-NB15 classifier. A malicious label is a review signal, not proof of a live incident.</ContextNote>

    <div className="two-col analyzer-layout">
      <Panel title="Bring your traffic data">
        <p className="description">Use a UTF-8 CSV with the {requiredColumns.length || 'required'} network-flow feature columns shown here. Numeric and categorical fields are supported; blank values are imputed by the fitted pipeline.</p>
        {schemaError && <div className="error" role="alert">{schemaError}</div>}

        <ol className="validation-steps" aria-label="CSV analysis workflow">
          {[
            ['Select a CSV', file ? file.name : 'Choose one UTF-8 file up to 5 MiB'],
            ['Validate schema', action === 'validate' ? 'Checking input with FastAPI' : result ? 'Required flow features passed' : 'Check headers, row shape, and feature types'],
            ['Run the model', analysis ? `${analysis.total_flows.toLocaleString()} rows classified` : action === 'analyze' ? 'Running the evaluated pipeline' : health?.model_loaded ? 'Review benchmark classifications and scores' : 'No evaluated model is available'],
          ].map(([title, description], index) => <li key={title} className={currentStep === index + 1 ? 'step-current' : currentStep > index + 1 ? 'step-complete' : ''} aria-current={currentStep === index + 1 ? 'step' : undefined}>
            <span>{currentStep > index + 1 ? <CheckCircle2 size={17} /> : String(index + 1).padStart(2, '0')}</span>
            <div><strong>{title}</strong><small>{description}</small></div>
          </li>)}
        </ol>

        <div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); if (!busy) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => {
          event.preventDefault();
          if (event.dataTransfer.files.length > 1) {
            choose(undefined);
            setError('Choose one CSV at a time.');
            return;
          }
          choose(event.dataTransfer.files[0]);
        }}>
          <Upload size={28} aria-hidden="true" />
          <h3>{file ? 'Your dataset is selected' : 'Drop your flow CSV here'}</h3>
          <p>UTF-8 CSV / up to 5 MiB / up to 50,000 records</p>
          <input ref={input} type="file" accept=".csv,text/csv" aria-label="Traffic CSV file" disabled={busy} tabIndex={-1} onChange={(event) => choose(event.target.files?.[0])} />
          <button type="button" disabled={busy} onClick={() => input.current?.click()}>{file ? 'Replace file' : 'Browse files'}</button>
        </div>

        {file && <div className="selected-file"><FileText size={20} aria-hidden="true" /><div><strong>{file.name}</strong><span>{readableSize(file.size)} / CSV / modified {new Date(file.lastModified).toLocaleDateString()}</span></div><button type="button" aria-label="Remove selected file" disabled={busy} onClick={removeFile}><X size={18} /></button></div>}

        <div className="upload-actions"><a href="/sample-flows.csv" download><ArrowDownToLine size={17} /> Download sample CSV</a><button type="button" className="primary" disabled={!file || !featureSchema || busy || !!(file && fileError(file))} onClick={() => processRequest('validate')}>{action === 'validate' ? 'Validating…' : 'Validate CSV'}<ArrowRight size={16} /></button></div>

        {busy && <div className="upload-progress"><div role="status">{progress < 100 ? `Uploading CSV: ${progress}%` : action === 'analyze' ? 'Upload complete. Running model inference…' : 'Upload complete. Checking schema…'}</div><progress aria-label={progress < 100 ? 'CSV upload progress' : action === 'analyze' ? 'Running model inference' : 'Validating CSV structure'} max={100} value={progress < 100 ? progress : undefined} /><button type="button" onClick={() => controller.current?.abort()}>Cancel {action === 'analyze' ? 'analysis' : 'validation'}</button></div>}
        {notice && <p className="validation-notice" role="status">{notice}</p>}
        {error && <div className="error" role="alert"><span>{error}</span>{file && !fileError(file) && <button type="button" onClick={() => processRequest(result ? 'analyze' : 'validate')} disabled={busy}>Retry</button>}</div>}

        {result && <>
          <div className="success" role="status"><CheckCircle2 size={20} /><span><strong>{result.row_count.toLocaleString()} rows validated</strong><br />{result.message}</span></div>
          <section className="validation-audit" aria-label="Validation checks">
            <h3>Validation checks</h3>
            <ul>
              <li><CheckCircle2 size={16} /><span>All {requiredColumns.length} required flow features are present.</span></li>
              <li><CheckCircle2 size={16} /><span>{result.row_count.toLocaleString()} rows passed structure and feature-type checks.</span></li>
              <li><CheckCircle2 size={16} /><span>{extraColumns.length ? `${extraColumns.length} extra source ${extraColumns.length === 1 ? 'column is' : 'columns are'} excluded from model inputs.` : 'No extra source columns were found.'}</span></li>
            </ul>
            {extraColumns.length > 0 && <div className="schema-warning"><strong>Extra source fields are excluded from inference.</strong><span>IDs, attack-category labels, and other additional columns do not feed the classifier.</span><code>{extraColumns.join(' · ')}</code></div>}
            <div className="validation-next-links"><Link to="/command-center">View dashboard summary <ArrowRight size={15} /></Link><Link to="/reports">Open validation receipt <ArrowRight size={15} /></Link></div>
          </section>
          {health?.model_loaded
            ? <div className="analysis-action"><div><strong>Run evaluated model</strong><p>Model {health.model_version}. Scores are uncalibrated benchmark probabilities.</p></div><button type="button" className="primary" onClick={() => processRequest('analyze')} disabled={busy}>{action === 'analyze' ? 'Analyzing…' : 'Analyze flows'} <ArrowRight size={16} /></button></div>
            : <p className="inline-note" role="status">The CSV is validated. Model inference is unavailable until a trained and evaluated artifact is installed.</p>}
        </>}
      </Panel>

      <Panel title="Model input schema" aside={<span className="tag">{featureSchema?.schema_name ?? 'Loading schema'}</span>}>
        <p className="description">FastAPI defines the accepted schema: {featureSchema?.numeric_features.length ?? 0} numeric and {featureSchema?.categorical_features.length ?? 0} categorical flow features. IDs and labels are excluded.</p>
        {featureSchema && <>
          <h3>Numeric flow features</h3><ul className="model-feature-list">{featureSchema.numeric_features.map((column) => <li key={column}><code>{column}</code></li>)}</ul>
          <h3>Categorical flow features</h3><ul className="model-feature-list">{featureSchema.categorical_features.map((column) => <li key={column}><code>{column}</code></li>)}</ul>
        </>}
        <div className="inline-note"><h3>How to read a result</h3><p>Labels refer to the benchmark classification. A malicious result should be investigated and is not proof of an attack.</p></div>
      </Panel>
    </div>

    {analysis && <Panel title="Model analysis" aside={<span className="tag">Actual model output / {analysis.model_version}</span>}>
      <div className="analysis-summary" role="status"><div><span>Source file</span><strong>{analysis.filename}</strong></div><div><span>Analyzed records</span><strong>{analysis.total_flows.toLocaleString()}</strong></div><div><span>Decision threshold</span><strong>{(analysis.threshold * 100).toFixed(1)}%</strong></div><div><span>Malicious classifications</span><strong className="analysis-anomalous">{analysis.counts.malicious.toLocaleString()}</strong></div></div>
      <div className="analysis-disclaimer"><strong>UNSW-NB15 benchmark output</strong><span>{analysis.message} The score is {analysis.score_definition}.</span></div>
      <div className="analysis-result-actions"><button type="button" className="primary" onClick={() => { try { downloadAnalysis(analysis); setDownloadNotice('CSV export requested.'); } catch { setDownloadNotice('Could not prepare the prediction export.'); } }}><Download size={16} /> Export predictions CSV</button>{downloadNotice && <span role="status">{downloadNotice}</span>}</div>
      {analysis.preview.length
        ? <div className="table-scroll analysis-preview" tabIndex={0} role="region" aria-label="Model prediction preview"><table><caption>First {analysis.preview.length} predictions from {analysis.total_flows.toLocaleString()} records</caption><thead><tr><th scope="col">Row</th>{requiredColumns.map((column) => <th scope="col" key={column}>{column}</th>)}<th scope="col">Prediction</th><th scope="col">Malicious score</th></tr></thead><tbody>{analysis.preview.map((row) => <tr key={row.row_id}><th scope="row">{row.row_id}</th>{requiredColumns.map((column) => <td key={column}>{row.features[column] ?? '—'}</td>)}<td><span className={`label-pill ${row.label === 'malicious' ? 'label-red' : 'label-green'}`}>{row.label}</span></td><td>{(row.malicious_score * 100).toFixed(1)}%</td></tr>)}</tbody></table></div>
        : <Empty title="No preview rows returned">The backend returned a valid analysis summary without preview records.</Empty>}
      <p className="fine">The download contains model labels and scores for every row. It does not include raw source features, and it is not retained in analysis history.</p>
    </Panel>}

    <Panel title="Inside your dataset" aside={<span className="tag">{result ? 'Validated input' : 'Awaiting a file'}</span>}>
      {result
        ? <div className="table-scroll" tabIndex={0} role="region" aria-label="Validated dataset preview"><table><caption>First {result.preview.length} of {result.row_count} validated rows</caption><thead><tr>{result.columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead><tbody>{result.preview.map((row, index) => <tr key={index}>{result.columns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody></table></div>
        : <Empty title="A preview before analysis">Validate a compatible CSV to inspect its first five rows. Only the 42 supported flow features are sent to the model.</Empty>}
    </Panel>
  </>;
}
