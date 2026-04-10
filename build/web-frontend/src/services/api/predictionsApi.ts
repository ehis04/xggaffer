import type {
  ModelInfoResponse,
  PredictionRequest,
  PredictionResponse,
  TeamsResponse,
} from '../../types/prediction';

const DEFAULT_API_BASE = '/api/predictions';
export const PREDICTIONS_API_BASE =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_PREDICTIONS_API_BASE) ||
  DEFAULT_API_BASE;

class PredictionsApiError extends Error {
  public readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'PredictionsApiError';
    this.status = status;
  }
}

function buildUrl(path: string, query?: Record<string, string | number | undefined>): string {
  const base = PREDICTIONS_API_BASE.replace(/\/$/, '');
  const url = new URL(`${base}/${path.replace(/^\//, '')}`, window.location.origin);

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return url.toString();
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      payload && typeof payload === 'object' && 'error' in payload
        ? String((payload as { error: unknown }).error)
        : `Prediction API request failed with status ${response.status}`;

    throw new PredictionsApiError(message, response.status);
  }

  return payload as T;
}

export async function getTeams(league = 'EPL', season = '2024'): Promise<TeamsResponse> {
  const response = await fetch(buildUrl('/teams/', { league, season }), {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  });

  return parseResponse<TeamsResponse>(response);
}

export async function getModelInfo(): Promise<ModelInfoResponse> {
  const response = await fetch(buildUrl('/model-info/'), {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  });

  return parseResponse<ModelInfoResponse>(response);
}

export async function predictMatch(request: PredictionRequest): Promise<PredictionResponse> {
  const response = await fetch(buildUrl('/predict/'), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      league: 'EPL',
      season: '2024',
      top_factors: 5,
      ...request,
    }),
  });

  return parseResponse<PredictionResponse>(response);
}

export { PredictionsApiError };
