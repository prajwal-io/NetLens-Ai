import { useEffect, useState } from 'react';
import { ExternalLink, RefreshCw } from 'lucide-react';
import { Panel, Empty } from '../components/ui';
import { ContextNote, DefinitionList, NextStep } from '../components/WorkspaceDetails';
import { ApiError, api, type ModelInfo } from '../services/api';

function percent(value: number) { return `${(value * 100).toFixed(1)}%`; }

export default function ModelLab() {
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function load(signal?: AbortSignal) {
    setLoading(true);
    setError('');
    try { setInfo(await api.modelInfo(signal)); }
    catch (reason) {
      setInfo(null);
      setError(reason instanceof ApiError ? reason.message : 'Could not load model information. Check the backend and retry.');
    } finally { if (!signal?.aborted) setLoading(false); }
  }

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, []);

  if (loading) return <><ContextNote>Loading the local model metadata and held-out evaluation report.</ContextNote><Panel title="Model Lab"><div className="page-skeleton" role="status" aria-busy="true">Loading model evaluation…<span/><span/></div></Panel></>;

  if (!info) return <>
    <ContextNote>The API exposes model details only when a trained pipeline and completed held-out evaluation are available.</ContextNote>
    <Panel title="Model status"><Empty title="No evaluated model is available">{error || 'Run the documented training and evaluation commands, then restart the FastAPI service.'}</Empty><button type="button" className="quiet-link" onClick={() => void load()}><RefreshCw size={15}/> Retry model status</button></Panel>
    <NextStep title="Prepare a compatible dataset" description="The analyzer checks the model's numeric feature contract before inference." to="/traffic-analyzer" label="Open Traffic Analyzer"/>
  </>;

  const metrics = info.evaluation.metrics;
  const matrix = metrics.confusion_matrix.rows_actual_columns_predicted;
  const candidates = Object.entries(info.validation_candidates);

  return <>
    <ContextNote>Evaluation values come from the saved pipeline and its untouched chronological test segment. This dataset labels network performance anomalies; it is not an intrusion or malware dataset.</ContextNote>
    {info.evaluation_warning && <div className="notice model-warning" role="status"><strong>Experimental result:</strong> {info.evaluation_warning} Low anomaly recall means many anomalous records were missed in this holdout.</div>}
    <div className="two-col">
      <Panel title="The model, in context" aside={<span className="tag">Evaluated / {info.model_version}</span>}>
        <p className="description">The selected pipeline was chosen using validation data and then evaluated on a later time segment.</p>
        <DefinitionList items={[
          ['Selected algorithm', info.algorithm],
          ['Comparison baseline', candidates.map(([name]) => name).find((name) => name !== info.algorithm) ?? 'Not evaluated'],
          ['Classification goal', 'Normal / network performance anomaly'],
          ['Target column', `${info.target.column} (${info.target.normal_value} / ${info.target.anomalous_value})`],
          ['Model version', info.model_version],
          ['Dataset', `${info.dataset.name} / ${info.dataset.rows.toLocaleString()} records`],
          ['Test period', `${new Date(info.evaluation.start).toLocaleString()} – ${new Date(info.evaluation.end).toLocaleString()}`],
          ['Decision threshold', `${(info.decision_threshold * 100).toFixed(0)}%`],
        ]}/>
        <a className="model-source-link" href={info.dataset.source} target="_blank" rel="noreferrer">Dataset source <ExternalLink size={14}/></a>
      </Panel>
      <Panel title="Evaluation protocol">
        <ol className="editorial-steps">
          <li><strong>Keep time order</strong><p>{info.split.strategy}. The final segment stays out of candidate and threshold selection.</p></li>
          <li><strong>Compare on validation</strong><p>{candidates.map(([name]) => name).join(' and ')} were compared by positive-class F1, then recall.</p></li>
          <li><strong>Report the holdout</strong><p>Metrics below use {info.evaluation.rows.toLocaleString()} later records, including {metrics.support.anomalous.toLocaleString()} anomalous examples.</p></li>
        </ol>
      </Panel>
    </div>

    <Panel title="Held-out evaluation" aside={<span className="tag">{info.evaluation.split}</span>}>
      <div className="evaluation-grid model-metrics">
        {[
          ['Accuracy', metrics.accuracy, 'All labels'],
          ['Precision', metrics.precision, 'Anomaly predictions'],
          ['Recall', metrics.recall, 'Anomalies detected'],
          ['F1-score', metrics.f1, 'Anomaly class'],
        ].map(([label, value, detail]) => <div key={String(label)}><h3>{label}</h3><strong>{percent(Number(value))}</strong><p>{detail}</p></div>)}
      </div>
      <p className="fine">Accuracy is not enough for an imbalanced dataset. Review anomaly precision, recall, and support together.</p>
      <div className="confusion-wrap">
        <h3>Confusion matrix</h3>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Held-out confusion matrix">
          <table className="confusion-matrix"><caption>Rows are actual labels; columns are model predictions.</caption><thead><tr><th scope="col">Actual / predicted</th>{metrics.confusion_matrix.labels.map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{matrix.map((row, index) => <tr key={metrics.confusion_matrix.labels[index]}><th scope="row">{metrics.confusion_matrix.labels[index]}</th>{row.map((value, col) => <td key={col}>{value.toLocaleString()}</td>)}</tr>)}</tbody></table>
        </div>
      </div>
    </Panel>

    <div className="two-col">
      <Panel title="Validation candidates" aside={<span className="tag">Model selection data</span>}>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Candidate validation metrics">
          <table><caption>Validation segment only; the final test segment is reported separately.</caption><thead><tr><th scope="col">Candidate</th><th scope="col">Threshold</th><th scope="col">Precision</th><th scope="col">Recall</th><th scope="col">F1</th></tr></thead><tbody>{candidates.map(([name, candidate]) => <tr key={name}><th scope="row">{name}{name === info.algorithm ? ' / selected' : ''}</th><td>{(candidate.threshold * 100).toFixed(0)}%</td><td>{percent(candidate.metrics.precision)}</td><td>{percent(candidate.metrics.recall)}</td><td>{percent(candidate.metrics.f1)}</td></tr>)}</tbody></table>
        </div>
      </Panel>
      <Panel title="Model input features" aside={<span className="tag">{info.feature_count} numeric features</span>}>
        <p className="description">The model uses only the measurements below. Timestamp, categorical fields, and all supplied anomaly labels are excluded.</p>
        <ul className="model-feature-list">{info.features.map((feature) => <li key={feature}><code>{feature}</code></li>)}</ul>
        <p className="fine">Score: {info.score_definition}.</p>
      </Panel>
    </div>

    <Panel title="Known limitations" aside={<span className="tag">Read before interpreting output</span>}>
      <ul className="model-limitations">{info.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      <p className="fine">A model anomaly is an indication to review the input. It does not prove malicious behavior.</p>
    </Panel>
  </>;
}
