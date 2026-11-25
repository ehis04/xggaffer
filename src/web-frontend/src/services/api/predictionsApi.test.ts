import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  getModelInfo,
  getOddsComparison,
  getTeams,
  predictMatch,
  PredictionsApiError,
} from './predictionsApi';
import {
  mockModelInfoResponse,
  mockOddsComparisonRequest,
  mockOddsComparisonResponse,
  mockPredictionRequest,
  mockPredictionResponse,
  mockTeamsResponse,
} from '../../pages/predictions/__mocks__/predictionFixtures';
import type { ApiEnvelope } from '../../common/types/response';

function makeEnvelope<T>(data: T): ApiEnvelope<T> {
  return {
    data,
    freshness: {
      source_fetched_at: null,
      snapshot_published_at: null,
      is_stale: false,
      is_degraded: false,
      stale_reason: null,
      sla_seconds: 21600,
    },
    version: '1',
    warnings: [],
    generated_at: '2026-01-01T00:00:00Z',
  };
}

function createJsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

describe('predictionsApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    document.cookie = 'csrftoken=test-token; path=/';
  });

  afterEach(() => {
    document.cookie = 'csrftoken=; Max-Age=0; path=/';
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('loads available teams', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(createJsonResponse(makeEnvelope(mockTeamsResponse)));

    const result = await getTeams('EPL', '2025');

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('/teams/');
    expect(result.data).toEqual(mockTeamsResponse);
  });

  it('loads model info', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(createJsonResponse(makeEnvelope(mockModelInfoResponse)));

    const result = await getModelInfo();

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('/model-info/');
    expect(result.data?.metrics.accuracy).toBe(0.555);
  });

  it('posts a match prediction request', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(createJsonResponse(mockPredictionResponse));

    const result = await predictMatch(mockPredictionRequest);

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = vi.mocked(fetch).mock.calls[0];

    expect(String(url)).toContain('/predict/');
    expect(options).toMatchObject({
      method: 'POST',
      credentials: 'include',
    });
    expect(JSON.parse(String(options?.body))).toEqual({ top_factors: 5, ...mockPredictionRequest });
    expect(result.prediction).toBe('Home');
    expect(result.probabilities.home).toBe(0.61);
  });

  it('posts an odds comparison request', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(createJsonResponse(mockOddsComparisonResponse));

    const result = await getOddsComparison(mockOddsComparisonRequest);

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = vi.mocked(fetch).mock.calls[0];

    expect(String(url)).toContain('/odds/compare/');
    expect(options).toMatchObject({
      method: 'POST',
      credentials: 'include',
    });
    expect(JSON.parse(String(options?.body))).toEqual(mockOddsComparisonRequest);
    expect(result.market.favourite).toBe('Home');
    expect(result.bookmakers).toHaveLength(2);
    expect(result.support.resources[0].region).toBe('Ireland');
  });

  it('throws a typed API error when the odds comparison endpoint returns an error payload', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      createJsonResponse({ error: 'Odds comparison unavailable for this fixture.' }, 404)
    );

    let error: PredictionsApiError | undefined;
    try {
      await getOddsComparison(mockOddsComparisonRequest);
    } catch (err) {
      error = err as PredictionsApiError;
    }

    expect(error).toBeInstanceOf(PredictionsApiError);
    expect(error!.name).toBe('PredictionsApiError');
    expect(error!.status).toBe(404);
    expect(error!.message).toContain('HTTP 404');
  });

  it('throws a typed API error when the backend returns an error payload', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(createJsonResponse({ error: 'Model not available.' }, 503));

    let error: PredictionsApiError | undefined;
    try {
      await getModelInfo();
    } catch (err) {
      error = err as PredictionsApiError;
    }

    expect(error).toBeInstanceOf(PredictionsApiError);
    expect(error!.name).toBe('PredictionsApiError');
    expect(error!.status).toBe(503);
    expect(error!.message).toContain('HTTP 503');
  });
});
