export interface Health { status: string; service: string; model_loaded: boolean; model_version: string | null }
export interface FeatureSchema {
  schema_name: string;
  feature_count: number;
  features: string[];
  numeric_features: string[];
  categorical_features: string[];
  excluded_columns: string[];
}
export interface Validation {
  valid: boolean;
  filename: string;
  row_count: number;
  columns: string[];
  preview: Record<string, string>[];
  schema_name: string;
  message: string;
}
export interface Prediction {
  row_id: number;
  label: 'normal' | 'malicious';
  malicious_score: number;
  source?: string | null;
  destination?: string | null;
  timestamp?: string | null;
}
export interface PredictionPreview extends Prediction { features: Record<string, string | number | null> }
export interface Analysis {
  analysis_id: string;
  source_type: 'uploaded_csv' | 'historical_replay';
  created_at: string;
  replay_id?: string | null;
  model_context: { dataset?: string; threshold_policy?: { maximum_validation_false_positive_rate: number }; evaluation?: EvaluationMetrics & { false_positive_rate?: number }; limitations?: string[] };
  filename: string;
  model_version: string;
  threshold: number;
  total_flows: number;
  counts: { normal: number; malicious: number };
  predictions: Prediction[];
  preview: PredictionPreview[];
  score_definition: string;
  message: string;
}
export interface EvaluationMetrics {
  accuracy: number;
  balanced_accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  average_precision: number;
  roc_auc: number;
  false_positive_rate?: number;
  specificity?: number;
  support: { normal: number; malicious: number };
  confusion_matrix: { labels: string[]; rows_actual_columns_predicted: number[][] };
}
export interface ThresholdPolicy {
  objective: string;
  maximum_validation_false_positive_rate: number;
  selected_validation_false_positive_rate: number;
  selected_validation_recall: number;
}
export interface ModelInfo {
  model_name: string;
  model_version: string;
  algorithm: string;
  dataset: { name: string; source: string; mirror: string; mirror_commit: string; license: string; rows: number; training_rows: number; test_rows: number; training_file: string; test_file: string; training_sha256: string; test_sha256: string };
  target: { column: string; normal_value: number; malicious_value: number; meaning: string; context_column_excluded: string };
  features: string[];
  numeric_features: string[];
  categorical_features: string[];
  feature_count: number;
  feature_count_numeric: number;
  feature_count_categorical: number;
  excluded_columns: string[];
  decision_threshold: number;
  threshold_policy: ThresholdPolicy;
  score_definition: string;
  preprocessing: { numeric_missing_values: string; categorical_missing_values: string; categorical_encoding: string; missing_values_found: { training: number; test: number } };
  split: { strategy: string; random_state: number; train_rows: number; validation_rows: number; test_rows: number; fitted_rows: number; feature_signature_groups: { unique_feature_signatures: number; repeated_feature_signatures: number; conflicting_feature_signatures: number } };
  class_counts: Record<string, { normal: number; malicious: number }>;
  validation_candidates: Record<string, { threshold: number; metrics: Omit<EvaluationMetrics, 'support' | 'confusion_matrix'> }>;
  evaluation: { split: string; rows: number; threshold: number; metrics: EvaluationMetrics; repeated_feature_signature_rows: number; repeated_feature_signature_rate: number; novel_feature_signature_evaluation: { rows: number; metrics: EvaluationMetrics | null; definition: string } };
  evaluation_warning: string | null;
  limitations: string[];
}

const base = ((import.meta as ImportMeta & { env: Record<string, string> }).env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
export class ApiError extends Error {
  constructor(message: string, public status = 0) { super(message); this.name = 'ApiError'; }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function decode(text: string, status: number): unknown {
  let body: unknown;
  try { body = JSON.parse(text) as unknown; }
  catch { throw new ApiError(status >= 400 ? 'Cannot reach NetSight API. Check that the backend is running on port 8000.' : 'The API returned an unreadable response. Please retry.', status); }
  if (status < 200 || status >= 300) {
    const error = isRecord(body) && isRecord(body.error) ? body.error.message : undefined;
    throw new ApiError(typeof error === 'string' ? error : 'The request could not be completed.', status);
  }
  return body;
}

function validationResponse(body: unknown): Validation {
  const result = body as Validation | null;
  const stringArray = (value: unknown): value is string[] => Array.isArray(value) && value.length > 0 && value.every((column) => typeof column === 'string' && column.trim().length > 0);
  if (!result || result.valid !== true || typeof result.filename !== 'string' || !result.filename.trim() || typeof result.message !== 'string' || typeof result.schema_name !== 'string' || !Number.isInteger(result.row_count) || result.row_count < 1 || !stringArray(result.columns) || new Set(result.columns).size !== result.columns.length || !Array.isArray(result.preview) || result.preview.length < 1 || result.preview.length > Math.min(5, result.row_count) || !result.preview.every((row) => row && typeof row === 'object' && !Array.isArray(row) && result.columns.every((column) => typeof row[column] === 'string'))) {
    throw new ApiError('The validation response was incomplete. Please retry.');
  }
  return result;
}

function analysisResponse(body: unknown): Analysis {
  const result = isRecord(body) ? body as unknown as Analysis : null;
  const validFeatureValue = (value: unknown) => value === null || typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value));
  if (!result || typeof result.analysis_id !== 'string' || !['uploaded_csv', 'historical_replay'].includes(result.source_type) || typeof result.filename !== 'string' || typeof result.model_version !== 'string' || !Number.isFinite(result.threshold) || result.threshold < 0 || result.threshold > 1 || !Number.isInteger(result.total_flows) || result.total_flows < 1 || !result.counts || !Number.isInteger(result.counts.normal) || !Number.isInteger(result.counts.malicious) || result.counts.normal + result.counts.malicious !== result.total_flows || !Array.isArray(result.predictions) || result.predictions.length !== result.total_flows || !result.predictions.every((prediction, index) => prediction && prediction.row_id === index + 1 && (prediction.label === 'normal' || prediction.label === 'malicious') && Number.isFinite(prediction.malicious_score) && prediction.malicious_score >= 0 && prediction.malicious_score <= 1) || !Array.isArray(result.preview) || result.preview.length > Math.min(5, result.total_flows) || !result.preview.every((row) => row && (row.label === 'normal' || row.label === 'malicious') && isRecord(row.features) && Object.values(row.features).every(validFeatureValue)) || typeof result.score_definition !== 'string' || typeof result.message !== 'string') {
    throw new ApiError('The analysis response was incomplete. Please retry.');
  }
  return result;
}

function upload<T>(path: string, file: File, validate: (body: unknown) => T, options: { signal?: AbortSignal; onProgress?: (percent: number) => void } = {}): Promise<T> {
  return getAccessToken().then(token => {
    if (!token) throw new ApiError('Sign in to validate or analyze traffic.', 401);
    return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    const clean = () => options.signal?.removeEventListener('abort', abort);
    xhr.open('POST', base + path);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.timeout = 90000;
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) options.onProgress?.(Math.min(100, Math.round(event.loaded / event.total * 100))); };
    xhr.upload.onload = () => options.onProgress?.(100);
    xhr.onload = () => { clean(); try { resolve(validate(decode(xhr.responseText, xhr.status))); } catch (error) { reject(error); } };
    xhr.onerror = () => { clean(); reject(new ApiError('Cannot reach NetSight API. Check that the backend is running on port 8000.')); };
    xhr.ontimeout = () => { clean(); reject(new ApiError('CSV processing timed out. Please retry.')); };
    xhr.onabort = () => { clean(); reject(new DOMException('Request cancelled.', 'AbortError')); };
    if (options.signal?.aborted) { reject(new DOMException('Request cancelled.', 'AbortError')); return; }
    options.signal?.addEventListener('abort', abort, { once: true });
    const data = new FormData(); data.append('file', file); xhr.send(data);
    });
  });
}

function isModelInfo(body: unknown): body is ModelInfo {
  if (!isRecord(body)) return false;
  const dataset = body.dataset;
  const evaluation = body.evaluation;
  const metrics = isRecord(evaluation) ? evaluation.metrics : undefined;
  const support = isRecord(metrics) ? metrics.support : undefined;
  const matrix = isRecord(metrics) ? metrics.confusion_matrix : undefined;
  const novelty = isRecord(evaluation) ? evaluation.novel_feature_signature_evaluation : undefined;
  const policy = body.threshold_policy;
  return typeof body.model_name === 'string' && typeof body.model_version === 'string' && typeof body.algorithm === 'string' && isRecord(dataset) && typeof dataset.name === 'string' && typeof dataset.source === 'string' && Array.isArray(body.features) && Number.isInteger(body.feature_count) && body.features.length === body.feature_count && Array.isArray(body.numeric_features) && Array.isArray(body.categorical_features) && isRecord(policy) && typeof policy.objective === 'string' && ['maximum_validation_false_positive_rate', 'selected_validation_false_positive_rate', 'selected_validation_recall'].every((key) => typeof policy[key] === 'number' && Number.isFinite(policy[key]) && Number(policy[key]) >= 0 && Number(policy[key]) <= 1) && typeof body.decision_threshold === 'number' && Number.isFinite(body.decision_threshold) && body.decision_threshold >= 0 && body.decision_threshold <= 1 && isRecord(metrics) && ['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1', 'average_precision', 'roc_auc'].every((key) => Number.isFinite(metrics[key])) && isRecord(support) && Number.isInteger(support.normal) && Number.isInteger(support.malicious) && isRecord(matrix) && Array.isArray(matrix.rows_actual_columns_predicted) && isRecord(novelty) && Number.isInteger(novelty.rows) && Array.isArray(body.limitations);
}

function isResponseDecision(value: unknown): value is ResponseDecision {
  const item = value as ResponseDecision | null;
  return !!item && typeof item.analysis_id === 'string' && Number.isInteger(item.row_id) && item.row_id > 0
    && (item.decision === 'simulated_block' || item.decision === 'dismissed')
    && typeof item.decided_at === 'string' && Number.isFinite(Date.parse(item.decided_at));
}

function isPredictionPreview(value: unknown): value is PredictionPreview {
  return isRecord(value) && Number.isInteger(value.row_id) && Number(value.row_id) > 0
    && (value.label === 'normal' || value.label === 'malicious')
    && Number.isFinite(value.malicious_score) && Number(value.malicious_score) >= 0 && Number(value.malicious_score) <= 1
    && isRecord(value.features) && Object.values(value.features).every((feature) => feature === null || typeof feature === 'string' || (typeof feature === 'number' && Number.isFinite(feature)))
    && ['source', 'destination', 'timestamp'].every((key) => value[key] === undefined || value[key] === null || typeof value[key] === 'string');
}


export interface AnalysisSummary {
  analysis_id: string; filename: string; created_at: string; source_type: Analysis['source_type'];
  model_version: string; total_flows: number; counts: Analysis['counts'];
}
export interface ResponseDecision { analysis_id: string; row_id: number; decision: 'simulated_block' | 'dismissed'; decided_at: string }
export interface ReplayScenario { id: string; title: string; description: string; rows: number; dataset: string; timing: string }
export interface HistoryPage { items: AnalysisSummary[]; total: number; limit: number; offset: number }

async function request(path: string, options: RequestInit = {}, timeoutMs = 90000): Promise<unknown> {
  try {
    const headers = new Headers(options.headers);
    const token = await getAccessToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const response = await fetch(base + path, { ...options, headers, signal: options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(timeoutMs)]) : AbortSignal.timeout(timeoutMs) });
    if (response.status === 204) return null;
    return decode(await response.text(), response.status);
  } catch (error) {
    if (error instanceof TypeError) throw new ApiError('Cannot reach NetSight API. Check the backend connection and retry.');
    if (error instanceof DOMException && error.name === 'TimeoutError') throw new ApiError('The request timed out. Please retry.');
    throw error;
  }
}

export async function downloadReport(id: string, format: 'csv' | 'pdf') {
  try {
    const token = await getAccessToken();
    if (!token) throw new ApiError('Sign in to download analysis reports.', 401);
    const response = await fetch(`${base}/analyses/${encodeURIComponent(id)}/${format === 'csv' ? 'export.csv' : 'report.pdf'}`, { headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(90000) });
    if (!response.ok) { decode(await response.text(), response.status); return; }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a'); link.href = url; link.download = `netsight-${id}.${format}`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    if (error instanceof TypeError) throw new ApiError('Cannot reach NetSight API. Check the backend connection and retry.');
    if (error instanceof DOMException && error.name === 'TimeoutError') throw new ApiError('The report download timed out. Please retry.');
    throw error;
  }
}

export const api = {
  async history(offset = 0, signal?: AbortSignal): Promise<HistoryPage> {
    const body = await request(`/analyses?limit=10&offset=${offset}`, { signal });
    if (!isRecord(body) || !Array.isArray(body.items) || !Number.isInteger(body.total) || !Number.isInteger(body.limit) || !Number.isInteger(body.offset)
      || !body.items.every((item) => isRecord(item) && typeof item.analysis_id === 'string' && typeof item.filename === 'string' && typeof item.created_at === 'string' && (item.source_type === 'uploaded_csv' || item.source_type === 'historical_replay') && typeof item.model_version === 'string' && Number.isInteger(item.total_flows) && isRecord(item.counts) && Number.isInteger(item.counts.normal) && Number.isInteger(item.counts.malicious))) {
      throw new ApiError('Analysis history was incomplete.');
    }
    return body as unknown as HistoryPage;
  },
  async analysis(id: string, signal?: AbortSignal): Promise<Analysis> {
    return analysisResponse(await request(`/analyses/${encodeURIComponent(id)}`, { signal }));
  },
  async deleteAnalysis(id: string): Promise<void> { await request(`/analyses/${encodeURIComponent(id)}`, { method: 'DELETE' }); },
  async replays(signal?: AbortSignal): Promise<ReplayScenario[]> {
    const body = await request('/replays', { signal });
    if (!isRecord(body) || !Array.isArray(body.items) || !body.items.every((item) => isRecord(item) && typeof item.id === 'string' && typeof item.title === 'string' && typeof item.description === 'string' && Number.isInteger(item.rows) && typeof item.dataset === 'string' && typeof item.timing === 'string')) {
      throw new ApiError('The replay scenario list was incomplete. Please retry.');
    }
    return body.items as ReplayScenario[];
  },
  async replay(id: string, signal?: AbortSignal): Promise<Analysis> {
    return analysisResponse(await request(`/replays/${encodeURIComponent(id)}/analyze`, { method: 'POST', signal }));
  },
  async flow(id: string, row: number, signal?: AbortSignal): Promise<PredictionPreview> {
    const body = await request(`/analyses/${encodeURIComponent(id)}/flows/${row}`, { signal });
    if (!isPredictionPreview(body)) throw new ApiError('The flow details were incomplete. Please retry.');
    return body;
  },
  async responseDecisions(id: string, signal?: AbortSignal): Promise<ResponseDecision[]> {
    const body = await request(`/analyses/${encodeURIComponent(id)}/response-decisions`, { signal }) as { analysis_id?: unknown; items?: unknown } | null;
    if (!body || body.analysis_id !== id || !Array.isArray(body.items) || !body.items.every((item) => isResponseDecision(item) && item.analysis_id === id)) {
      throw new ApiError('The analyst response list was incomplete. Please retry.');
    }
    return body.items;
  },
  async setResponseDecision(id: string, row: number, decision: ResponseDecision['decision']): Promise<ResponseDecision> {
    const body = await request(`/analyses/${encodeURIComponent(id)}/flows/${row}/response`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision }) });
    if (!isResponseDecision(body) || body.analysis_id !== id || body.row_id !== row || body.decision !== decision) throw new ApiError('The analyst response could not be saved. Please retry.');
    return body;
  },
  async clearResponseDecision(id: string, row: number): Promise<void> {
    await request(`/analyses/${encodeURIComponent(id)}/flows/${row}/response`, { method: 'DELETE' });
  },
  async health(signal?: AbortSignal): Promise<Health> {
    const body = await request('/health', { signal }, 15000);
    if (!isRecord(body) || body.status !== 'ok' || typeof body.service !== 'string' || typeof body.model_loaded !== 'boolean' || (body.model_version !== null && typeof body.model_version !== 'string')) throw new ApiError('The backend returned an invalid health response.');
    return body as unknown as Health;
  },
  async featureSchema(signal?: AbortSignal): Promise<FeatureSchema> {
    const body = await request('/model/schema', { signal }, 15000);
    if (!isRecord(body) || typeof body.schema_name !== 'string' || !Number.isInteger(body.feature_count) || Number(body.feature_count) < 1 || !Array.isArray(body.features) || body.features.length !== body.feature_count || !Array.isArray(body.numeric_features) || !Array.isArray(body.categorical_features) || !Array.isArray(body.excluded_columns) || !body.features.every((feature) => typeof feature === 'string')) {
      throw new ApiError('The model input schema response was incomplete. Please retry.');
    }
    return body as unknown as FeatureSchema;
  },
  async modelInfo(signal?: AbortSignal): Promise<ModelInfo> {
    const body = await request('/model/info', { signal }, 15000);
    if (!isModelInfo(body)) throw new ApiError('The model information response was incomplete. Please retry.');
    return body;
  },
  validate(file: File, options: { signal?: AbortSignal; onProgress?: (percent: number) => void } = {}): Promise<Validation> {
    return upload('/traffic/validate', file, validationResponse, options);
  },
  analyze(file: File, options: { signal?: AbortSignal; onProgress?: (percent: number) => void } = {}): Promise<Analysis> {
    return upload('/traffic/analyze', file, analysisResponse, options);
  },
};
import { getAccessToken } from '../auth/AuthContext';

