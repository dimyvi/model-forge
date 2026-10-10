import api from './api';

export type ExperimentStatus = 'ready' | 'queued' | 'running' | 'completed' | 'failed';
export type ExperimentResult = {
  id: number;
  algorithm: string;
  metrics: Record<string, number>;
  model_file: string | null;
  is_best: boolean;
};
export type Experiment = {
  id: number;
  dataset: number;
  task: 'classification' | 'regression';
  target_column: string;
  algorithms: string[];
  status: ExperimentStatus;
  error_message: string;
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
  results: ExperimentResult[];
};
export type AvailableAlgorithm = { id: string; name: string };
export type AvailableAlgorithms = Record<Experiment['task'], AvailableAlgorithm[]>;

export function isExperimentActive(status: ExperimentStatus) {
  return status === 'queued' || status === 'running';
}

export function canEditExperiment(status: ExperimentStatus) {
  return status === 'ready' || status === 'failed';
}

export async function downloadExperimentModel(experimentId: number, result: ExperimentResult, signal: AbortSignal) {
  const path = `/api/experiments/${experimentId}/results/${result.id}/download/`;
  // Only the protected endpoint for this result may receive the user's token.
  if (result.model_file !== path) throw new Error('Invalid model download path');
  const response = await api.get<Blob>(path.slice('/api'.length), { responseType: 'blob', signal });
  if (signal.aborted) return;

  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `experiment_${experimentId}_${result.algorithm.replace(/[^a-zA-Z0-9_-]/g, '_')}_${result.id}.joblib`;
  try {
    document.body.appendChild(link);
    link.click();
  } finally {
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
