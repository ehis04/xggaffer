import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import OddsComparisonPage from '../OddsComparisonPage';
import type { OddsComparisonResponse } from '../../../types/prediction';

const mockGetOddsComparison = vi.fn();
const mockGetTeams = vi.fn();

vi.mock('../../../services/api/predictionsApi', () => ({
  getOddsComparison: (...args: unknown[]) => mockGetOddsComparison(...args),
  getTeams: (...args: unknown[]) => mockGetTeams(...args),
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

const buildResponse = (): OddsComparisonResponse => ({
  home_team: 'Arsenal',
  away_team: 'Chelsea',
  league: 'EPL',
  season: '2024',
  kickoff: '2026-04-20T15:00:00Z',
  source: 'the_odds_api',
  model: {
    probabilities: {
      home: 0.51,
      draw: 0.26,
      away: 0.23,
    },
    prediction: 'Home',
    version: 'v1',
    model_type: 'logistic_regression',
  },
  market: {
    devig_home: 0.4445,
    devig_draw: 0.285,
    devig_away: 0.2705,
    favourite: 'home',
    overround: 1.08,
    source_label: 'the_odds_api',
  },
  bookmakers: [
    {
      bookmaker: 'Bet365',
      home_odds: 2.1,
      draw_odds: 3.4,
      away_odds: 3.6,
      devig_home: 0.455,
      devig_draw: 0.281,
      devig_away: 0.264,
      last_seen_at: '2026-04-18T10:00:00Z',
    },
  ],
  comparison: {
    model_favourite: 'home',
    market_favourite: 'home',
    biggest_edge_side: 'home',
    biggest_edge_points: 6.6,
    agreement: true,
    summary: 'xgGaffer is 6.6 percentage points higher on Arsenal than the market.',
  },
  benchmark: {
    sample_size: 360,
    model_accuracy: 0.555,
    market_favourite_accuracy: null,
    model_brier_score: null,
    market_brier_score: null,
    evaluation_scope: 'engine4_season_simulation_backtest',
    source_label: 'engine4_backtest',
  },
  support: {
    warning:
      'This comparison is analytical only and not financial advice. If betting stops feeling like entertainment, pause and seek support.',
    resources: [
      {
        label: 'Problem Gambling Ireland',
        region: 'Ireland',
        support_type: 'support',
      },
    ],
  },
});

describe('OddsComparisonPage', () => {
  beforeEach(() => {
    mockGetOddsComparison.mockReset();
    mockGetTeams.mockReset();
    mockGetTeams.mockResolvedValue({ teams: ['Arsenal', 'Chelsea'] });
  });

  it('renders the initial empty state', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: /odds & market comparison/i })).toBeInTheDocument();
    expect(screen.getByText(/ready to compare/i)).toBeInTheDocument();
    expect(
      screen.getByText(/select a league, season, and fixture/i)
    ).toBeInTheDocument();
  });

  it('blocks submission when teams are the same', async () => {
    renderPage();

    await screen.findAllByRole('option', { name: 'Arsenal' });

    fireEvent.change(screen.getByLabelText(/home team/i), {
      target: { value: 'Arsenal' },
    });
    fireEvent.change(screen.getByLabelText(/away team/i), {
      target: { value: 'Arsenal' },
    });

    fireEvent.click(screen.getByRole('button', { name: /compare fixture/i }));

    expect(mockGetOddsComparison).not.toHaveBeenCalled();
    expect(
      await screen.findByText(/home team and away team must be different/i)
    ).toBeInTheDocument();
  });

  it('submits a valid request and renders the result', async () => {
    mockGetOddsComparison.mockResolvedValue(buildResponse());

    renderPage();

    await screen.findAllByRole('option', { name: 'Arsenal' });

    fireEvent.change(screen.getByLabelText(/home team/i), {
      target: { value: 'Arsenal' },
    });
    fireEvent.change(screen.getByLabelText(/away team/i), {
      target: { value: 'Chelsea' },
    });

    fireEvent.click(screen.getByRole('button', { name: /compare fixture/i }));

    await waitFor(() => {
      expect(mockGetOddsComparison).toHaveBeenCalledWith({
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        league: 'EPL',
        season: '2025',
      });
    });

    expect(await screen.findByText(/arsenal vs chelsea/i)).toBeInTheDocument();
    expect(screen.getByText(/xggaffer model/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /market consensus/i })).toBeInTheDocument();
    expect(screen.getByText(/problem gambling ireland/i)).toBeInTheDocument();
  });

  it('shows a loading state while the request is in flight', async () => {
    let resolveRequest: ((value: OddsComparisonResponse) => void) = () => {};

    mockGetOddsComparison.mockImplementation(
      () =>
        new Promise<OddsComparisonResponse>((resolve) => {
          resolveRequest = resolve;
        })
    );

    renderPage();

    await screen.findAllByRole('option', { name: 'Arsenal' });

    fireEvent.change(screen.getByLabelText(/home team/i), {
      target: { value: 'Arsenal' },
    });
    fireEvent.change(screen.getByLabelText(/away team/i), {
      target: { value: 'Chelsea' },
    });

    fireEvent.click(screen.getByRole('button', { name: /compare fixture/i }));

    expect(await screen.findByText(/loading comparison/i)).toBeInTheDocument();

    resolveRequest(buildResponse());

    expect(await screen.findByText(/arsenal vs chelsea/i)).toBeInTheDocument();
  });

  it('shows a safe error message when the request fails', async () => {
    mockGetOddsComparison.mockRejectedValue(new Error('No live odds are available.'));

    renderPage();

    await screen.findAllByRole('option', { name: 'Arsenal' });

    fireEvent.change(screen.getByLabelText(/home team/i), {
      target: { value: 'Arsenal' },
    });
    fireEvent.change(screen.getByLabelText(/away team/i), {
      target: { value: 'Chelsea' },
    });

    fireEvent.click(screen.getByRole('button', { name: /compare fixture/i }));

    expect(await screen.findByText(/comparison unavailable/i)).toBeInTheDocument();
    expect(await screen.findByText(/no live odds are available/i)).toBeInTheDocument();
  });
});