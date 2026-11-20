import { useAnalysis, setAnalysis } from '../services/analysis';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownToLine, ArrowRight, CheckCircle2, FileText, Upload, X } from 'lucide-react';
import { Panel } from '../components/ui';
import { ContextNote } from '../components/WorkspaceDetails';
import { CaptureUpload } from '../components/CaptureUpload';
import { api, type FeatureSchema, type Health, type Validation } from '../services/api';

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

export default function Analyzer({ health }: { health: Health | null }) {
  const [featureSchema, setFeatureSchema] = useState<FeatureSchema | null>(null);
  const [schemaError, setSchemaError] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Validation | null>(null);
  const analysis = useAnalysis();
  const [error, setError] = useState('');
  const [action, setAction] = useState<'validate' | 'analyze' | null>(null);
  const [progress, setProgress] = useState(0);
  const [notice, setNotice] = useState('');
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
    setProgress(0);
    if (kind === 'validate') { setResult(null); setAnalysis(null); }
    try {
      if (kind === 'validate') {
        const validation = await api.validate(file, { signal: request.signal, onProgress: setProgress });
        if (!request.signal.aborted) {
          setResult(validation);
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
        <p className="description">Use a UTF-8 CSV matching the UNSW-NB15 model contract: {requiredColumns.length || 42} required flow features with the same meanings and units. Numeric and categorical fields are supported; blank values are imputed by the fitted pipeline. Other schemas need a compatible trained model pipeline.</p>
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
          <p>UTF-8 CSV / up to 5 MiB / up to 10,000 records</p>
          <input ref={input} type="file" accept=".csv,text/csv" aria-label="Traffic CSV file" disabled={busy} tabIndex={-1} onChange={(event) => choose(event.target.files?.[0])} />
          <button type="button" disabled={busy} onClick={() => input.current?.click()}>{file ? 'Replace file' : 'Browse files'}</button>
        </div>

        {file && <div className="selected-file"><FileText size={20} aria-hidden="true" /><div><strong>{file.name}</strong><span>{readableSize(file.size)} / CSV / modified {new Date(file.lastModified).toLocaleDateString()}</span></div><button type="button" aria-label="Remove selected file" disabled={busy} onClick={removeFile}><X size={18} /></button></div>}

        <div className="upload-actions"><a href="/sample-flows.csv" download><ArrowDownToLine size={17} /> Download schema example</a><button type="button" className="primary" disabled={!file || !featureSchema || busy || !!(file && fileError(file))} onClick={() => processRequest('validate')}>{action === 'validate' ? 'Validating…' : 'Validate CSV'}<ArrowRight size={16} /></button></div>
        <p className="fine">The downloadable three-row file is synthetic test input. Use Historical replay for real benchmark traffic.</p>

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
          </section>
          {health?.model_loaded
            ? <div className="analysis-action"><div><strong>Run evaluated model</strong><p>Model {health.model_version}. Scores are uncalibrated benchmark probabilities.</p></div><button type="button" className="primary" onClick={() => processRequest('analyze')} disabled={busy}>{action === 'analyze' ? 'Analyzing…' : 'Analyze flows'} <ArrowRight size={16} /></button></div>
            : <p className="inline-note" role="status">The CSV is validated. Model inference is unavailable until a trained and evaluated artifact is installed.</p>}
        </>}
      </Panel>

      <Panel title="Model input schema" className="schema-panel" aside={<span className="tag">{featureSchema?.schema_name ?? 'Loading schema'}</span>}>
        <p className="description">The model accepts {featureSchema?.feature_count ?? 42} UNSW-NB15 flow features: {featureSchema?.numeric_features.length ?? 39} numeric and {featureSchema?.categorical_features.length ?? 3} categorical. IDs and labels are excluded.</p>
        {featureSchema && <details className="schema-details">
          <summary><span>Supported feature names</span><span className="schema-details-count">{featureSchema.feature_count} fields</span></summary>
          <div className="schema-feature-groups">
            <section className="schema-feature-group">
              <h3>Numeric <span>{featureSchema.numeric_features.length} features</span></h3>
              <ul className="schema-feature-list">{featureSchema.numeric_features.map((column) => <li key={column}><code>{column}</code></li>)}</ul>
            </section>
            <section className="schema-feature-group">
              <h3>Categorical <span>{featureSchema.categorical_features.length} features</span></h3>
              <ul className="schema-feature-list">{featureSchema.categorical_features.map((column) => <li key={column}><code>{column}</code></li>)}</ul>
            </section>
          </div>
        </details>}
      </Panel>
    </div>

    <CaptureUpload />

    {analysis && <Panel title="Model analysis" aside={<span className="tag">Actual model output / {analysis.model_version}</span>}>
      <p>{analysis.filename} · {analysis.source_type === 'historical_replay' ? 'Historical benchmark replay' : 'Uploaded CSV'} · {analysis.total_flows.toLocaleString()} flows</p>
      <div className="analysis-summary" role="status"><div><span>Normal</span><strong>{analysis.counts.normal.toLocaleString()}</strong></div><div><span>Malicious</span><strong className="analysis-anomalous">{analysis.counts.malicious.toLocaleString()}</strong></div><div><span>Decision threshold</span><strong>{(analysis.threshold * 100).toFixed(1)}%</strong></div><div><span>Model</span><strong>{analysis.model_version}</strong></div></div>
      <div className="analysis-disclaimer"><strong>Benchmark classification; analyst review required.</strong><span>{analysis.message} Scores are {analysis.score_definition}.</span></div>
      <div className="analysis-result-actions"><Link to="/network-pulse">Network Pulse <ArrowRight size={15}/></Link><Link to="/threat-investigation">Investigate flows <ArrowRight size={15}/></Link><Link to="/reports">Export reports <ArrowRight size={15}/></Link></div>
    </Panel>}

    {result && <Panel title="Validated input preview" aside={<span className="tag">{result.row_count.toLocaleString()} rows / metadata only</span>}>
      <details><summary>Inspect the first {result.preview.length} validated rows</summary>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Validated dataset preview"><table><caption>Preview only; raw traffic rows are not retained after validation.</caption><thead><tr>{result.columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead><tbody>{result.preview.map((row, index) => <tr key={index}>{result.columns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody></table></div>
      </details>
    </Panel>}
  </>;
}
