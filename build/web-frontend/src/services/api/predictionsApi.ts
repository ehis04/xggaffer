import apiClient from './client';
import type {
  ModelInfoResponse,
  PredictionRequest,
  PredictionResponse,
  TeamsResponse,
  ChatResponse,
} from '../../types/prediction';

const DEFAULT_PREDICTIONS_API_BASE = '/predictions';

const normalisePredictionsBase = (value: string): string => {
  const trimmed = value.trim().replace(/\/+$/, '');

  if (!trimmed) {
    return DEFAULT_PREDICTIONS_API_BASE;
  }

  if (/^https?:\/\//i.test(trimmed)) {
    return DEFAULT_PREDICTIONS_API_BASE;
  }

  if (trimmed === '/api') {
    return DEFAULT_PREDICTIONS_API_BASE;
  }

  if (trimmed.startsWith('/api/')) {
    return trimmed.replace(/^\/api/, '');
  }

  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
};

export const PREDICTIONS_API_BASE = normalisePredictionsBase(
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_PREDICTIONS_API_BASE) ||
    DEFAULT_PREDICTIONS_API_BASE
);

export class PredictionsApiError extends Error {
  public readonly status: number;
  public readonly data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'PredictionsApiError';
    this.status = status;
    this.data = data;
  }
}

type ApiClientError = Error & {
  status?: number;
  data?: unknown;
};

const buildPredictionsEndpoint = (path: string): string => {
  const base = PREDICTIONS_API_BASE.replace(/\/+$/, '');
  const normalisedPath = path.replace(/^\/+/, '');
  return `${base}/${normalisedPath}`;
};

const toPredictionsApiError = (error: unknown): PredictionsApiError => {
  if (error instanceof PredictionsApiError) {
    return error;
  }

  const apiError = error as ApiClientError;
  const status = typeof apiError?.status === 'number' ? apiError.status : 500;
  const data = apiError?.data;

  let message = apiError?.message || 'Prediction API request failed.';

  if (data && typeof data === 'object' && 'error' in data) {
    const errorValue = (data as { error?: unknown }).error;
    if (typeof errorValue === 'string' && errorValue.trim()) {
      message = errorValue;
    }
  }

  return new PredictionsApiError(message, status, data);
};

const withPredictionsErrorHandling = async <T>(request: () => Promise<T>): Promise<T> => {
  try {
    return await request();
  } catch (error) {
    throw toPredictionsApiError(error);
  }
};

export async function getTeams(
  league = 'EPL',
  season = '2024'
): Promise<TeamsResponse> {
  return withPredictionsErrorHandling(() =>
    apiClient.get<TeamsResponse>(
      buildPredictionsEndpoint('teams/'),
      { league, season }
    )
  );
}

export async function getModelInfo(): Promise<ModelInfoResponse> {
  return withPredictionsErrorHandling(() =>
    apiClient.get<ModelInfoResponse>(
      buildPredictionsEndpoint('model-info/')
    )
  );
}

export async function predictMatch(
  request: PredictionRequest
): Promise<PredictionResponse> {
  return withPredictionsErrorHandling(() =>
    apiClient.post<PredictionResponse>(
      buildPredictionsEndpoint('predict/'),
      {
        league: 'EPL',
        season: '2024',
        top_factors: 5,
        ...request,
      }
    )
  );
}

export async function chatQuery(query: string): Promise<ChatResponse> {
  return withPredictionsErrorHandling(() =>
    apiClient.post<ChatResponse>(
      buildPredictionsEndpoint('chat/'),
      { query }
    )
  );
}