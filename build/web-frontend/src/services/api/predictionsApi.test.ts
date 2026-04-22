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
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('loads available teams', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(createJsonResponse(mockTeamsResponse));

    const result = await getTeams('EPL', '2024');

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('/teams/');
    expect(result).toEqual(mockTeamsResponse);
  });

  it('loads model info', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(createJsonResponse(mockModelInfoResponse));

    const result = await getModelInfo();

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('/model-info/');
    expect(result.metrics.accuracy).toBe(0.555);
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
    expect(JSON.parse(String(options?.body))).toEqual(mockPredictionRequest);
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