import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import PredictionsHub from '../../../pages/predictions/PredictionsHub';

vi.mock('../../../services/api/livefootballApi', () => ({
  default: {
    getCompetitions: vi.fn(),
    getCompetitionFixtures: vi.fn(),
  },
}));

vi.mock('../../widgets/MatchPredictionCard', () => ({
  default: ({ homeTeam, awayTeam }: { homeTeam: string; awayTeam: string }) => (
    <div data-testid="prediction-card">{homeTeam} vs {awayTeam}</div>
  ),
}));

import liveFootballApi from '../../../services/api/livefootballApi';

const BASE_COMPETITION_FIELDS = {
  provider: 'football-data',
  external_id: 'pd-1',
  area_name: 'England',
  emblem_url: '',
  current_season_label: '2025/26',
};

const MOCK_COMPETITIONS = [
  { id: 1, code: 'PL', name: 'Premier League', ...BASE_COMPETITION_FIELDS },
  {
    id: 2,
    code: 'PD',
    name: 'La Liga',
    ...BASE_COMPETITION_FIELDS,
    external_id: 'pd-2',
    area_name: 'Spain',
  },
];

const MOCK_FIXTURES = {
  competition: { id: 1, code: 'PL', name: 'Premier League', ...BASE_COMPETITION_FIELDS },
  season_label: '2025/26',
  count: 2,
  items: [
    {
      id: 101,
      external_match_id: 'fixture-101',
      season_label: '2025/26',
      status: 'SCHEDULED',
      home_team: { name: 'Arsenal', short_name: 'Arsenal', tla: 'ARS', emblem_url: '' },
      away_team: { name: 'Chelsea', short_name: 'Chelsea', tla: 'CHE', emblem_url: '' },
      kickoff_at: '2026-05-10T15:00:00Z',
    },
    {
      id: 102,
      external_match_id: 'fixture-102',
      season_label: '2025/26',
      status: 'SCHEDULED',
      home_team: { name: 'Liverpool', short_name: 'Liverpool', tla: 'LIV', emblem_url: '' },
      away_team: { name: 'Man City', short_name: 'Man City', tla: 'MCI', emblem_url: '' },
      kickoff_at: '2026-05-11T15:00:00Z',
    },
  ],
};

function renderHub() {
  return render(
    <MemoryRouter>
      <PredictionsHub />
    </MemoryRouter>
  );
}

describe('PredictionsHub', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders page heading', () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValueOnce(MOCK_COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValueOnce(MOCK_FIXTURES);
    renderHub();
    expect(screen.getByRole('heading', { name: /predictions hub/i })).toBeInTheDocument();
  });

  it('renders all 5 league tabs', () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValueOnce(MOCK_COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValueOnce(MOCK_FIXTURES);
    renderHub();
    expect(screen.getByRole('button', { name: /premier league/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /la liga/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /bundesliga/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /serie a/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ligue 1/i })).toBeInTheDocument();
  });

  it('renders fixture cards after load', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValueOnce(MOCK_COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValueOnce(MOCK_FIXTURES);
    renderHub();
    await waitFor(() => {
      expect(screen.getAllByTestId('prediction-card').length).toBeGreaterThan(0);
    });
  });

  it('shows null state when no fixtures returned', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValueOnce(MOCK_COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValueOnce({
      competition: { id: 1, code: 'PL', name: 'Premier League', ...BASE_COMPETITION_FIELDS },
      season_label: '2025/26',
      count: 0,
      items: [],
    });
    renderHub();
    await waitFor(() => {
      expect(screen.getByText(/no fixtures match/i)).toBeInTheDocument();
    });
  });

  it('shows error state when API fails', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockRejectedValueOnce(new Error('fail'));
    renderHub();
    await waitFor(() => {
      expect(screen.getByText(/failed to load fixtures/i)).toBeInTheDocument();
    });
  });

  it('switches league on tab click and re-fetches', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValue(MOCK_COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValue(MOCK_FIXTURES);
    renderHub();
    await waitFor(() => screen.getAllByTestId('prediction-card'));
    fireEvent.click(screen.getByRole('button', { name: /la liga/i }));
    await waitFor(() => {
      expect(liveFootballApi.getCompetitions).toHaveBeenCalledTimes(2);
    });
  });
});