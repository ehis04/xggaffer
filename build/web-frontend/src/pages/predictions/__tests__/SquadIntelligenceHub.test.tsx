import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import SquadIntelligenceHub from '../SquadIntelligenceHub';
import type { ApiEnvelope } from '../../../common/types/response';
import type { AvailabilityWidgetPayload, LineupWidgetPayload } from '../../../services/api/widgetApi';
import type { CompetitionFixturesResponse, CompetitionListItem } from '../../../types/livefootball';

vi.mock('../../../services/api/widgetApi', () => ({
  fetchAvailabilityWidget: vi.fn(),
  fetchLineupWidget: vi.fn(),
}));

vi.mock('../../../services/api/livefootballApi', () => ({
  default: {
    getCompetitions: vi.fn(),
    getCompetitionFixtures: vi.fn(),
  },
}));

vi.mock('../../../common/components/SectionSkeleton', () => ({
  SectionSkeleton: () => <div data-testid="section-skeleton" />,
}));

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: () => null,
}));

vi.mock('../../../components/widgets/NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => (
    <div data-testid="null-placeholder">{message}</div>
  ),
}));

vi.mock('../../../components/widgets/AvailabilityTimeline', () => ({
  default: () => <div data-testid="availability-timeline" />,
}));

vi.mock('../../../components/widgets/PredictedXIBoard', () => ({
  default: () => <div data-testid="predicted-xi-board" />,
}));

import liveFootballApi from '../../../services/api/livefootballApi';
import { fetchAvailabilityWidget, fetchLineupWidget } from '../../../services/api/widgetApi';

const COMPETITIONS: CompetitionListItem[] = [
  {
    id: 1,
    provider: 'football-data',
    external_id: 'PL',
    code: 'PL',
    name: 'Premier League',
    area_name: 'England',
    emblem_url: 'https://example.com/pl.svg',
    current_season_label: '2024/25',
  },
];

const MOCK_FIXTURES_RES: CompetitionFixturesResponse = {
  competition: COMPETITIONS[0],
  season_label: '2024/25',
  count: 2,
  items: [
    {
      id: 10,
      external_match_id: '10',
      season_label: '2024/25',
      status: 'SCHEDULED',
      kickoff_at: '2025-05-01T15:00:00Z',
      home_team: { name: 'Arsenal', short_name: 'Arsenal', tla: 'ARS', emblem_url: '' },
      away_team: { name: 'Chelsea', short_name: 'Chelsea', tla: 'CHE', emblem_url: '' },
    },
    {
      id: 11,
      external_match_id: '11',
      season_label: '2024/25',
      status: 'SCHEDULED',
      kickoff_at: '2025-05-03T15:00:00Z',
      home_team: { name: 'Liverpool', short_name: 'Liverpool', tla: 'LIV', emblem_url: '' },
      away_team: { name: 'Arsenal', short_name: 'Arsenal', tla: 'ARS', emblem_url: '' },
    },
  ],
};

const FRESH = {
  source_fetched_at: null, snapshot_published_at: null,
  is_stale: false, is_degraded: false, stale_reason: null,
  sla_seconds: 0, cascade_degraded: false, cascade_reason: null,
};

function makeAvailEnvelope(): ApiEnvelope<AvailabilityWidgetPayload> {
  return {
    data: {
      widget_type: 'availability',
      data: {
        team: 'Arsenal',
        fixture_date: '2025-05-01',
        players: [{ name: 'Saka', availability_prob: 0.9, risk_level: 'available', return_date_estimate: null }],
        summary: { available_count: 1, high_risk_count: 0, unavailable_count: 0 },
      },
      explanation: {}, confidence: { score: 0.7, band: 'medium' }, freshness: FRESH, summary: {},
    },
    freshness: FRESH, version: '1', warnings: [], generated_at: '',
  };
}

function makeLineupEnvelope(): ApiEnvelope<LineupWidgetPayload> {
  return {
    data: {
      widget_type: 'predicted_lineup',
      data: {
        team: 'Arsenal', fixture_date: '2025-05-01', formation: '4-3-3',
        predicted_xi: [], bench_candidates: [],
      },
      explanation: {}, confidence: { score: 0.8, band: 'high' }, freshness: FRESH, summary: {},
    },
    freshness: FRESH, version: '1', warnings: [], generated_at: '',
  };
}

function renderHub(teamSlug = 'Arsenal') {
  return render(
    <MemoryRouter initialEntries={[`/squad/${teamSlug}`]}>
      <Routes>
        <Route path="/squad/:teamSlug" element={<SquadIntelligenceHub />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('SquadIntelligenceHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchAvailabilityWidget).mockResolvedValue(makeAvailEnvelope());
    vi.mocked(fetchLineupWidget).mockResolvedValue(makeLineupEnvelope());
  });

  it('renders fixture selector when fixtures loaded', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValue(COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValue(MOCK_FIXTURES_RES);
    renderHub();
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });
  });

  it('renders NullStatePlaceholder when no fixtures found', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValue(COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValue({
      competition: COMPETITIONS[0],
      season_label: '2024/25',
      count: 0,
      items: [],
    });
    renderHub();
    await waitFor(() => {
      expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
      expect(screen.getByText(/no upcoming fixtures/i)).toBeInTheDocument();
    });
  });

  it('renders AvailabilityTimeline when fixture selected', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValue(COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValue(MOCK_FIXTURES_RES);
    renderHub();
    await waitFor(() => {
      expect(screen.getByTestId('availability-timeline')).toBeInTheDocument();
    });
  });

  it('renders PredictedXIBoard after show XI toggled', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValue(COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValue(MOCK_FIXTURES_RES);
    renderHub();
    await waitFor(() => screen.getByRole('button', { name: /show predicted xi/i }));
    fireEvent.click(screen.getByRole('button', { name: /show predicted xi/i }));
    await waitFor(() => {
      expect(screen.getByTestId('predicted-xi-board')).toBeInTheDocument();
    });
  });

  it('shows congestion label for fixtures within CONGESTION_THRESHOLD_DAYS', async () => {
    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValue(COMPETITIONS);
    vi.mocked(liveFootballApi.getCompetitionFixtures).mockResolvedValue(MOCK_FIXTURES_RES);
    renderHub();
    await waitFor(() => {
      expect(screen.getByText(/high congestion/i)).toBeInTheDocument();
    });
  });
});