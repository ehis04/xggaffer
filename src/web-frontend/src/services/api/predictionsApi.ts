import apiClient from './client';
import type {
  ModelInfoResponse,
  OddsComparisonRequest,
  OddsComparisonResponse,
  OddsFixtureListResponse,
  OddsTeamsResponse,
  PredictionRequest,
  PredictionResponse,
  TeamsResponse,
  ChatResponse,
} from '../../types/prediction';
import type { ApiEnvelope } from '../../common/types/response';
import { isEnvelope } from '../../common/types/response';
import { getCurrentFootballSeason } from '../../utils/footballSeason';

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
  league: string,
  season: string
): Promise<ApiEnvelope<TeamsResponse>> {
  return withPredictionsErrorHandling(() =>
    apiClient.get<ApiEnvelope<TeamsResponse>>(
      buildPredictionsEndpoint('teams/'),
      { league, season }
    )
  );
}

export async function getModelInfo(): Promise<ApiEnvelope<ModelInfoResponse>> {
  return withPredictionsErrorHandling(() =>
    apiClient.get<ApiEnvelope<ModelInfoResponse>>(
      buildPredictionsEndpoint('model-info/')
    )
  );
}

export async function predictMatch(
  request: PredictionRequest
): Promise<PredictionResponse> {
  const raw = await withPredictionsErrorHandling(() =>
    apiClient.post<ApiEnvelope<PredictionResponse> | PredictionResponse>(
      buildPredictionsEndpoint('predict/'),
      {
        top_factors: 5,
        ...request,
      }
    )
  );

  if (isEnvelope<PredictionResponse>(raw)) {
    const data = raw.data;
    if (!data) {
      throw new PredictionsApiError('No prediction data returned.', 500);
    }
    return data;
  }

  return raw as PredictionResponse;
}

export async function getOddsComparison(
  request: OddsComparisonRequest
): Promise<OddsComparisonResponse> {
  const raw = await withPredictionsErrorHandling(() =>
    apiClient.post<ApiEnvelope<OddsComparisonResponse> | OddsComparisonResponse>(
      buildPredictionsEndpoint('odds/compare/'),
      {
        home_team: request.home_team,
        away_team: request.away_team,
        league: request.league,
        season: request.season,
        bookmakers: request.bookmakers,
        use_cached: request.use_cached,
      }
    )
  );

  if (isEnvelope<OddsComparisonResponse>(raw)) {
    const data = raw.data;
    if (!data) {
      throw new PredictionsApiError('No odds comparison data returned.', 500);
    }
    return data;
  }

  return raw as OddsComparisonResponse;
}

export async function getOddsFixtures(
  league: string,
  view: 'past' | 'future',
  teamA?: string,
  teamB?: string,
): Promise<ApiEnvelope<OddsFixtureListResponse>> {
  const params: Record<string, string> = { league, view };
  if (teamA) params.team_a = teamA;
  if (teamB) params.team_b = teamB;
  return withPredictionsErrorHandling(() =>
    apiClient.get<ApiEnvelope<OddsFixtureListResponse>>(
      buildPredictionsEndpoint('odds/fixtures/'),
      params
    )
  );
}

export async function getOddsTeams(league: string): Promise<ApiEnvelope<OddsTeamsResponse>> {
  return withPredictionsErrorHandling(() =>
    apiClient.get<ApiEnvelope<OddsTeamsResponse>>(
      buildPredictionsEndpoint('odds/teams/'),
      { league }
    )
  );
}

export interface OddsAccuracyResponse {
  league: string;
  season: string;
  model_wins: number;
  market_wins: number;
  ties: number;
  total_evaluated: number;
  computed_at: string;
}

export async function getOddsAccuracy(
  league: string,
  season: string = getCurrentFootballSeason(),
): Promise<ApiEnvelope<OddsAccuracyResponse | null>> {
  return withPredictionsErrorHandling(() =>
    apiClient.get<ApiEnvelope<OddsAccuracyResponse | null>>(
      buildPredictionsEndpoint('odds/accuracy/'),
      { league, season }
    )
  );
}

export async function chatQuery(
  query: string,
  imageB64?: string,
  imageMediaType?: string,
): Promise<ApiEnvelope<ChatResponse>> {
  return withPredictionsErrorHandling(() =>
    apiClient.post<ApiEnvelope<ChatResponse>>(
      buildPredictionsEndpoint('chat/'),
      {
        query,
        ...(imageB64 && { image_b64: imageB64, image_media_type: imageMediaType }),
      }
    )
  );
}
