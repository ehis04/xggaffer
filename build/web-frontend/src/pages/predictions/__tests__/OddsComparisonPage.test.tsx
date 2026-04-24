import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import OddsComparisonPage from '../OddsComparisonPage';
import type { OddsFixtureItem, PredictionResponse } from '../../../types/prediction';

const mockGetOddsFixtures = vi.fn();
const mockGetOddsTeams = vi.fn();
const mockPredictMatch = vi.fn();

vi.mock('../../../services/api/predictionsApi', () => ({
  getOddsFixtures: (...args: unknown[]) => mockGetOddsFixtures(...args),
  getOddsTeams: (...args: unknown[]) => mockGetOddsTeams(...args),
  predictMatch: (...args: unknown[]) => mockPredictMatch(...args),
}));

const renderPage = () => {
  return render(
    <MemoryRouter initialEntries={['/coaching/predictions/odds']}>
      <Routes>
        <Route path="/coaching/predictions/odds" element={<OddsComparisonPage />} />
      </Routes>
    </MemoryRouter>
  );
};

const buildFixture = (): OddsFixtureItem => ({
  home_team: 'Arsenal',
  away_team: 'Chelsea',
  league: 'EPL',
  season: '2025',
  commence_time: '2026-04-20T15:00:00Z',
  fetched_at: '2026-04-20T12:00:00Z',
  bookmakers: [],
  consensus: {
    devig_home: 0.51,
    devig_draw: 0.26,
    devig_away: 0.23,
    overround: 1.08,
    favourite: 'home',
    source_label: 'market',
  },
  result: null,
});

const buildPrediction = (): PredictionResponse => ({
  home_team: 'Arsenal',
  away_team: 'Chelsea',
  league: 'EPL',
  season: '2025',
  prediction: 'Home',
  probabilities: {
    home: 0.61,
    draw: 0.24,
    away: 0.15,
  },
  top_factors: [],
  metrics: {
    accuracy: 0.555,
    brier_score: null,
  },
  model_type: 'logistic_regression',
  version: 'v1',
});

describe('OddsComparisonPage', () => {
  beforeEach(() => {
    mockGetOddsFixtures.mockReset();
    mockGetOddsTeams.mockReset();
    mockPredictMatch.mockReset();

    mockGetOddsTeams.mockResolvedValue({ league: 'EPL', teams: ['Arsenal', 'Chelsea'] });
    mockGetOddsFixtures.mockResolvedValue({
      league: 'EPL',
      season: '2025',
      view: 'future',
      count: 0,
      fixtures: [],
    });
  });

  it('renders the initial empty state', async () => {
    renderPage();

    expect(screen.getByRole('heading', { name: /odds & market comparison/i })).toBeInTheDocument();
    expect(await screen.findByText(/No fixtures with odds data found/i)).toBeInTheDocument();
  });

  it('reloads fixtures when team filters are changed', async () => {
    renderPage();

    await screen.findAllByRole('option', { name: 'Arsenal' });

    fireEvent.change(screen.getByLabelText(/Team A/i), {
      target: { value: 'Arsenal' },
    });
    fireEvent.change(screen.getByLabelText(/Team B/i), {
      target: { value: 'Chelsea' },
    });

    await waitFor(() => {
      expect(mockGetOddsFixtures).toHaveBeenLastCalledWith(
        'EPL',
        'future',
        'Arsenal',
        'Chelsea'
      );
    });
  });

  it('renders fixtures and loads prediction for a row', async () => {
    mockGetOddsFixtures.mockResolvedValue({
      league: 'EPL',
      season: '2025',
      view: 'future',
      count: 1,
      fixtures: [buildFixture()],
    });
    mockPredictMatch.mockResolvedValue(buildPrediction());

    renderPage();

    const predictButton = await screen.findByRole('button', { name: /Get prediction/i });
    fireEvent.click(predictButton);

    await waitFor(() => {
      expect(mockPredictMatch).toHaveBeenCalledWith({
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        league: 'EPL',
        season: '2025',
      });
    });

    expect(await screen.findByText('Home')).toBeInTheDocument();
    expect(screen.getByText('61.0% / 24.0% / 15.0%')).toBeInTheDocument();
  });

  it('shows a loading state while the request is in flight', async () => {
    let resolveRequest: ((value: {
      league: string;
      season: string;
      view: 'future' | 'past';
      count: number;
      fixtures: OddsFixtureItem[];
    }) => void) = () => {};

    mockGetOddsFixtures.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        })
    );

    renderPage();

    expect(await screen.findByText(/Loading fixtures/i)).toBeInTheDocument();

    resolveRequest({
      league: 'EPL',
      season: '2025',
      view: 'future',
      count: 0,
      fixtures: [],
    });

    expect(await screen.findByText(/No fixtures with odds data found/i)).toBeInTheDocument();
  });

  it('shows a safe error message when the request fails', async () => {
    mockGetOddsFixtures.mockRejectedValue(new Error('No live odds are available.'));

    renderPage();

    expect(await screen.findByText(/no live odds are available/i)).toBeInTheDocument();
  });
});