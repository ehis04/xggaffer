import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import type { ApiEnvelope } from '../../../common/types/response';
import SeasonProjectionCentre from '../../../pages/predictions/SeasonProjectionCentre';

vi.mock('../../../services/api/widgetApi', () => ({
  fetchProjectedTableWidget: vi.fn(),
}));

vi.mock('../../../services/api/livefootballApi', () => ({
  default: {
    getCompetitions: vi.fn().mockResolvedValue([]),
    getCompetitionFixtures: vi.fn().mockResolvedValue({ fixtures: [] }),
  },
}));

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: () => null,
}));

vi.mock('../../../common/components/SectionSkeleton', () => ({
  SectionSkeleton: () => <div data-testid="section-skeleton" />,
}));

vi.mock('../../../common/components/InlineRetry', () => ({
  InlineRetry: ({ onRetry }: { onRetry: () => void }) => (
    <button onClick={onRetry}>Retry</button>
  ),
}));

vi.mock('../../../components/widgets/SimulatedLeagueTable', () => ({
  default: () => <div data-testid="simulated-league-table" />,
}));

vi.mock('../../../components/widgets/PositionProbabilityMatrix', () => ({
  default: () => <div data-testid="position-probability-matrix" />,
}));

vi.mock('../../../components/widgets/ProjectedPointsBandChart', () => ({
  default: () => <div data-testid="projected-points-band-chart" />,
}));

vi.mock('../../../components/widgets/WhatIfPanel', () => ({
  default: () => <div data-testid="what-if-panel" />,
  WHATIF_WIN_POINTS: 3,
  WHATIF_DRAW_POINTS: 1,
  WHATIF_LOSS_POINTS: 0,
}));

vi.mock('../../../components/widgets/DegradedBanner', () => ({
  default: ({ reason }: { reason: string }) => (
    <div data-testid="degraded-banner">{reason}</div>
  ),
}));

vi.mock('../../Navigation/SideBar', () => ({
  Sidebar: () => null,
}));

vi.mock('../../Social/SocialUserButtons', () => ({
  SocialUserButtons: () => null,
}));

import { fetchProjectedTableWidget } from '../../../services/api/widgetApi';
import type {
  ProjectedTableData,
  ProjectedTableWidgetPayload,
  WidgetFreshness,
} from '../../../services/api/widgetApi';

const FRESH_FRESHNESS: WidgetFreshness = {
  source_fetched_at: null,
  snapshot_published_at: null,
  is_stale: false,
  is_degraded: false,
  stale_reason: null,
  sla_seconds: 21600,
  cascade_degraded: false,
  cascade_reason: null,
};

function makeEnvelope(data: ProjectedTableData | null): ApiEnvelope<ProjectedTableWidgetPayload> {
  return {
    data: {
      widget_type: 'projected_table',
      data,
      explanation: {},
      confidence: { score: 0.8, band: 'high' as const },
      freshness: FRESH_FRESHNESS,
      summary: { season_label: '2024/2025', team_count: 2 },
    },
    freshness: FRESH_FRESHNESS,
    version: '1',
    warnings: [],
    generated_at: '2026-01-01T00:00:00Z',
  };
}

const MOCK_DATA = {
  league_code: 'PL',
  season: '2024',
  teams: [
    {
      team_name: 'Arsenal',
      expected_position: 1,
      projected_points_median: 82,
      projected_points_p10: null,
      projected_points_p90: null,
      title_prob: 0.5,
      top4_prob: 0.95,
      relegation_prob: 0.0,
      position_distribution: {},
    },
  ],
};

function renderCentre(leagueCode = 'PL') {
  return render(
    <MemoryRouter initialEntries={[`/season/${leagueCode}`]}>
      <Routes>
        <Route path="/season/:leagueCode" element={<SeasonProjectionCentre />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('SeasonProjectionCentre', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders league selector tabs', async () => {
    vi.mocked(fetchProjectedTableWidget).mockResolvedValueOnce(makeEnvelope(MOCK_DATA));
    renderCentre();
    expect(screen.getByRole('button', { name: /premier league/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /la liga/i })).toBeInTheDocument();
    expect(await screen.findByTestId('simulated-league-table')).toBeInTheDocument();
  });

  it('renders SectionSkeleton during load', () => {
    vi.mocked(fetchProjectedTableWidget).mockReturnValueOnce(new Promise(() => {}));
    renderCentre();
    expect(screen.getByTestId('section-skeleton')).toBeInTheDocument();
  });

  it('renders NullStatePlaceholder when data is null', async () => {
    vi.mocked(fetchProjectedTableWidget).mockResolvedValueOnce(makeEnvelope(null));
    renderCentre();
    await waitFor(() => {
      expect(screen.getByText(/season projection not yet available/i)).toBeInTheDocument();
    });
  });

  it('renders SimulatedLeagueTable for table view by default', async () => {
    vi.mocked(fetchProjectedTableWidget).mockResolvedValueOnce(makeEnvelope(MOCK_DATA));
    renderCentre();
    await waitFor(() => {
      expect(screen.getByTestId('simulated-league-table')).toBeInTheDocument();
    });
  });

  it('clicking Matrix tab switches to PositionProbabilityMatrix', async () => {
    vi.mocked(fetchProjectedTableWidget).mockResolvedValueOnce(makeEnvelope(MOCK_DATA));
    renderCentre();
    await waitFor(() => screen.getByTestId('simulated-league-table'));
    fireEvent.click(screen.getByRole('button', { name: /matrix/i }));
    expect(screen.getByTestId('position-probability-matrix')).toBeInTheDocument();
    expect(screen.queryByTestId('simulated-league-table')).not.toBeInTheDocument();
  });

  it('clicking Chart tab switches to ProjectedPointsBandChart', async () => {
    vi.mocked(fetchProjectedTableWidget).mockResolvedValueOnce(makeEnvelope(MOCK_DATA));
    renderCentre();
    await waitFor(() => screen.getByTestId('simulated-league-table'));
    fireEvent.click(screen.getByRole('button', { name: /chart/i }));
    expect(screen.getByTestId('projected-points-band-chart')).toBeInTheDocument();
  });

  it('shows DegradedBanner when cascade_degraded is true', async () => {
    const staleFreshness = { ...FRESH_FRESHNESS, cascade_degraded: true, cascade_reason: 'elo' };
    const basePayload: ProjectedTableWidgetPayload = {
      widget_type: 'projected_table',
      data: MOCK_DATA,
      explanation: {},
      confidence: { score: 0.8, band: 'high' },
      freshness: FRESH_FRESHNESS,
      summary: { season_label: '2024/2025', team_count: 2 },
    };
    vi.mocked(fetchProjectedTableWidget).mockResolvedValueOnce({
      ...makeEnvelope(MOCK_DATA),
      data: { ...basePayload, freshness: staleFreshness },
    });
    renderCentre();
    await waitFor(() => {
      expect(screen.getByTestId('degraded-banner')).toBeInTheDocument();
    });
  });

  it('season scope notice always visible when data present', async () => {
    vi.mocked(fetchProjectedTableWidget).mockResolvedValueOnce(makeEnvelope(MOCK_DATA));
    renderCentre();
    await waitFor(() => {
      expect(screen.getByText(/projections based on season/i)).toBeInTheDocument();
    });
  });
});
