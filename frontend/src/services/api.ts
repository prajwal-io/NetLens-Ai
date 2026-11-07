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
}
export interface PredictionPreview extends Prediction { features: Record<string, string | number | null> }
export interface Analysis {
  analysis_id: string;
  source_type: 'uploaded_csv';
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
  support: { normal: number; malicious: number };
  confusion_matrix: { labels: string[]; rows_actual_columns_predicted: number[][] };
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

function decode(text: string, status: number) {
  let body: any;
  try { body = JSON.parse(text); }
  catch { throw new ApiError(status >= 400 ? 'Cannot reach NetSight API. Check that the backend is running on port 8000.' : 'The API returned an unreadable response. Please retry.', status); }
  if (status < 200 || status >= 300) throw new ApiError(typeof body?.error?.message === 'string' ? body.error.message : 'The request could not be completed.', status);
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
  const result = body as Analysis | null;
  const validFeatureValue = (value: unknown) => value === null || typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value));
  if (!result || typeof result.analysis_id !== 'string' || result.source_type !== 'uploaded_csv' || typeof result.filename !== 'string' || typeof result.model_version !== 'string' || !Number.isFinite(result.threshold) || result.threshold < 0 || result.threshold > 1 || !Number.isInteger(result.total_flows) || result.total_flows < 1 || !result.counts || !Number.isInteger(result.counts.normal) || !Number.isInteger(result.counts.malicious) || result.counts.normal + result.counts.malicious !== result.total_flows || !Array.isArray(result.predictions) || result.predictions.length !== result.total_flows || !result.predictions.every((prediction, index) => prediction && prediction.row_id === index + 1 && (prediction.label === 'normal' || prediction.label === 'malicious') && Number.isFinite(prediction.malicious_score) && prediction.malicious_score >= 0 && prediction.malicious_score <= 1) || !Array.isArray(result.preview) || result.preview.length > Math.min(5, result.total_flows) || !result.preview.every((row) => row && (row.label === 'normal' || row.label === 'malicious') && typeof row.features === 'object' && Object.values(row.features).every(validFeatureValue)) || typeof result.score_definition !== 'string' || typeof result.message !== 'string') {
    throw new ApiError('The analysis response was incomplete. Please retry.');
  }
  return result;
}

function upload<T>(path: string, file: File, validate: (body: unknown) => T, options: { signal?: AbortSignal; onProgress?: (percent: number) => void } = {}): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    const clean = () => options.signal?.removeEventListener('abort', abort);
    xhr.open('POST', base + path);
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
}

function isModelInfo(body: any): body is ModelInfo {
  const metrics = body?.evaluation?.metrics;
  return !!body && typeof body.model_name === 'string' && typeof body.model_version === 'string' && typeof body.algorithm === 'string' && typeof body.dataset?.name === 'string' && typeof body.dataset?.source === 'string' && Array.isArray(body.features) && Number.isInteger(body.feature_count) && body.features.length === body.feature_count && Array.isArray(body.numeric_features) && Array.isArray(body.categorical_features) && !!metrics && ['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1', 'average_precision', 'roc_auc'].every((key) => Number.isFinite(metrics[key])) && !!metrics.support && Number.isInteger(metrics.support.normal) && Number.isInteger(metrics.support.malicious) && !!metrics.confusion_matrix && Array.isArray(metrics.confusion_matrix.rows_actual_columns_predicted) && Number.isInteger(body.evaluation?.novel_feature_signature_evaluation?.rows) && Array.isArray(body.limitations);
}

export const api = {
  async health(signal?: AbortSignal): Promise<Health> {
    try {
      const response = await fetch(base + '/health', { signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000) });
      const body = decode(await response.text(), response.status) as Health;
      if (!body || body.status !== 'ok' || typeof body.service !== 'string' || typeof body.model_loaded !== 'boolean' || (body.model_version !== null && typeof body.model_version !== 'string')) throw new ApiError('The backend returned an invalid health response.');
      return body;
    } catch (error) {
      if (error instanceof TypeError) throw new ApiError('Cannot reach NetSight API. Check that the backend is running on port 8000.');
      if (error instanceof DOMException && error.name === 'TimeoutError') throw new ApiError('The API request timed out. Please retry.');
      throw error;
    }
  },
  async featureSchema(signal?: AbortSignal): Promise<FeatureSchema> {
    const response = await fetch(base + '/model/schema', { signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000) });
    const body = decode(await response.text(), response.status) as FeatureSchema;
    if (!body || typeof body.schema_name !== 'string' || !Number.isInteger(body.feature_count) || body.feature_count < 1 || !Array.isArray(body.features) || body.features.length !== body.feature_count || !Array.isArray(body.numeric_features) || !Array.isArray(body.categorical_features) || !Array.isArray(body.excluded_columns) || !body.features.every((feature) => typeof feature === 'string')) {
      throw new ApiError('The model input schema response was incomplete. Please retry.');
    }
    return body;
  },
  async modelInfo(signal?: AbortSignal): Promise<ModelInfo> {
    const response = await fetch(base + '/model/info', { signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000) });
    const body = decode(await response.text(), response.status);
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
