import { useEffect, useState } from 'react';
import { ExternalLink, RefreshCw } from 'lucide-react';
import { Panel, Empty } from '../components/ui';
import { ContextNote, DefinitionList, NextStep } from '../components/WorkspaceDetails';
import { ApiError, api, type EvaluationMetrics, type ModelInfo } from '../services/api';

function percent(value: number) { return `${(value * 100).toFixed(1)}%`; }

function MetricsTable({ metrics, title }: { metrics: EvaluationMetrics; title: string }) {
  const matrix = metrics.confusion_matrix.rows_actual_columns_predicted;
  return <div className="table-scroll" tabIndex={0} role="region" aria-label={`${title} confusion matrix`}>
    <table className="confusion-matrix"><caption>{title}: rows are actual classes; columns are predictions.</caption>
      <thead><tr><th scope="col">Actual / predicted</th>{metrics.confusion_matrix.labels.map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{matrix.map((row, index) => <tr key={metrics.confusion_matrix.labels[index]}><th scope="row">{metrics.confusion_matrix.labels[index]}</th>{row.map((value, col) => <td key={col}>{value.toLocaleString()}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}

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

  if (loading) return <><ContextNote>Loading model metadata and its held-out benchmark evaluation.</ContextNote><Panel title="Model Lab"><div className="page-skeleton" role="status" aria-busy="true">Loading model evaluation…<span/><span/></div></Panel></>;

  if (!info) return <>
    <ContextNote>The API exposes model details only when a trained pipeline and completed held-out evaluation are installed.</ContextNote>
    <Panel title="Model status"><Empty title="No evaluated model is available">{error || 'Run the documented dataset, training, and evaluation commands, then restart the FastAPI service.'}</Empty><button type="button" className="quiet-link" onClick={() => void load()}><RefreshCw size={15}/> Retry model status</button></Panel>
    <NextStep title="Prepare a compatible dataset" description="The analyzer checks the model's mixed numeric and categorical flow schema before inference." to="/traffic-analyzer" label="Open Traffic Analyzer"/>
  </>;

  const metrics = info.evaluation.metrics;
  const candidates = Object.entries(info.validation_candidates);
  const novel = info.evaluation.novel_feature_signature_evaluation;

  return <>
    <ContextNote>These are measured results on the official UNSW-NB15 test partition. The benchmark includes normal traffic and simulated attack categories; it is not live detection and does not establish performance on other networks.</ContextNote>
    {info.evaluation_warning && <div className="notice model-warning" role="status"><strong>Evaluation caveat:</strong> {info.evaluation_warning}</div>}
    <div className="two-col">
      <Panel title="The model, in context" aside={<span className="tag">Evaluated / {info.model_version}</span>}>
        <p className="description">A mixed-feature preprocessing pipeline is fitted with each candidate. Random Forest and Logistic Regression are compared on grouped validation data, then the selected candidate is refitted on the official training split.</p>
        <DefinitionList items={[
          ['Selected algorithm', info.algorithm],
          ['Comparison baseline', candidates.map(([name]) => name).find((name) => name !== info.algorithm) ?? 'Not evaluated'],
          ['Classification goal', 'Normal / malicious benchmark label'],
          ['Target column', `${info.target.column} (${info.target.normal_value} normal / ${info.target.malicious_value} attack)`],
          ['Dataset', `${info.dataset.name} / ${info.dataset.rows.toLocaleString()} records`],
          ['Training / test', `${info.dataset.training_rows.toLocaleString()} / ${info.dataset.test_rows.toLocaleString()}`],
          ['Decision threshold', `${(info.decision_threshold * 100).toFixed(1)}%`],
          ['Input schema', `${info.feature_count_numeric} numeric + ${info.feature_count_categorical} categorical`],
        ]}/>
        <a className="model-source-link" href={info.dataset.source} target="_blank" rel="noreferrer">Official dataset page <ExternalLink size={14}/></a>
        <p className="fine">Academic research use; original papers must be cited. {info.dataset.license}</p>
      </Panel>
      <Panel title="Evaluation protocol">
        <ol className="editorial-steps">
          <li><strong>Keep the official test set untouched</strong><p>{info.split.strategy}. Model and score threshold are chosen without the test labels.</p></li>
          <li><strong>Group repeated feature signatures</strong><p>Identical 42-feature rows stay within one validation partition to reduce memorization between fit and validation.</p></li>
          <li><strong>Check unseen signatures</strong><p>The separate sensitivity view measures test rows with no matching feature signature in training.</p></li>
        </ol>
      </Panel>
    </div>

    <Panel title="Official held-out test" aside={<span className="tag">{info.evaluation.rows.toLocaleString()} rows / benchmark</span>}>
      <div className="evaluation-grid model-metrics">
        {[
          ['Accuracy', metrics.accuracy, 'All labels'],
          ['Precision', metrics.precision, 'Malicious predictions'],
          ['Recall', metrics.recall, 'Malicious records detected'],
          ['F1-score', metrics.f1, 'Malicious class'],
        ].map(([label, value, detail]) => <div key={String(label)}><h3>{label}</h3><strong>{percent(Number(value))}</strong><p>{detail}</p></div>)}
      </div>
      <p className="fine">Average precision {percent(metrics.average_precision)} / ROC-AUC {percent(metrics.roc_auc)} / balanced accuracy {percent(metrics.balanced_accuracy)}. Review precision and false positives along with recall.</p>
      <div className="confusion-wrap"><h3>Confusion matrix</h3><MetricsTable metrics={metrics} title="Official test partition"/></div>
    </Panel>

    <div className="two-col">
      <Panel title="Unseen feature-signature check" aside={<span className="tag">{novel.rows.toLocaleString()} rows</span>}>
        {novel.metrics ? <>
          <p className="description">{novel.definition}. This removes repeated feature signatures from train-to-test comparisons and is shown as a sensitivity check.</p>
          <DefinitionList items={[
            ['Accuracy', percent(novel.metrics.accuracy)],
            ['Precision', percent(novel.metrics.precision)],
            ['Recall', percent(novel.metrics.recall)],
            ['F1-score', percent(novel.metrics.f1)],
            ['Average precision', percent(novel.metrics.average_precision)],
            ['Test support', `${novel.metrics.support.normal.toLocaleString()} normal / ${novel.metrics.support.malicious.toLocaleString()} malicious`],
          ]}/>
          <MetricsTable metrics={novel.metrics} title="Unseen-signature subset"/>
        </> : <Empty title="Not enough class coverage">The novelty-aware subset did not contain both labels, so these metrics are unavailable.</Empty>}
      </Panel>
      <Panel title="Validation candidates" aside={<span className="tag">Selection only</span>}>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Candidate validation metrics">
          <table><caption>Validation segment only; the official test results are separate.</caption><thead><tr><th scope="col">Candidate</th><th scope="col">Threshold</th><th scope="col">Precision</th><th scope="col">Recall</th><th scope="col">F1</th></tr></thead>
            <tbody>{candidates.map(([name, candidate]) => <tr key={name}><th scope="row">{name}{name === info.algorithm ? ' / selected' : ''}</th><td>{(candidate.threshold * 100).toFixed(1)}%</td><td>{percent(candidate.metrics.precision)}</td><td>{percent(candidate.metrics.recall)}</td><td>{percent(candidate.metrics.f1)}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="fine">The selected threshold maximizes malicious-class F1 on validation data. The displayed scores are not calibrated confidence values.</p>
      </Panel>
    </div>

    <div className="two-col">
      <Panel title="Model input features" aside={<span className="tag">{info.feature_count} features</span>}>
        <p className="description">The ID, target label, and attack category are excluded. Preprocessing is fitted only on training data.</p>
        <h3>Numeric / {info.numeric_features.length}</h3><ul className="model-feature-list">{info.numeric_features.map((feature) => <li key={feature}><code>{feature}</code></li>)}</ul>
        <h3>Categorical / {info.categorical_features.length}</h3><ul className="model-feature-list">{info.categorical_features.map((feature) => <li key={feature}><code>{feature}</code></li>)}</ul>
        <p className="fine">Score definition: {info.score_definition}.</p>
      </Panel>
      <Panel title="Preprocessing and labels">
        <DefinitionList items={[
          ['Numeric missing values', info.preprocessing.numeric_missing_values],
          ['Categorical missing values', info.preprocessing.categorical_missing_values],
          ['Category encoding', info.preprocessing.categorical_encoding],
          ['Training missing values', info.preprocessing.missing_values_found.training.toLocaleString()],
          ['Test missing values', info.preprocessing.missing_values_found.test.toLocaleString()],
          ['Ignored source columns', info.excluded_columns.join(', ')],
        ]}/>
        <p className="fine">The attack category is not a model input, so it cannot directly reveal the binary target during inference.</p>
      </Panel>
    </div>

    <Panel title="Known limitations" aside={<span className="tag">Interpret with care</span>}>
      <ul className="model-limitations">{info.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      <p className="fine">A benchmark label is an indication to review the supplied flow features. It does not prove malicious behavior or provide live network monitoring.</p>
    </Panel>
  </>;
}
