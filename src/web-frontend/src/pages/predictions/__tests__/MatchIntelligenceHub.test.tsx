import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import MatchIntelligenceHub from '../MatchIntelligenceHub';
import type { ApiEnvelope } from '../../../common/types/response';
import type { MatchPredictionWidgetPayload } from '../../../services/api/widgetApi';

vi.mock('../../../services/api/widgetApi', () => ({
  fetchMatchPredictionWidget: vi.fn(),
  fetchScorelineWidget: vi.fn(),
  fetchAvailabilityWidget: vi.fn(),
  fetchLineupWidget: vi.fn(),
  fetchTacticalWidget: vi.fn(),
}));

vi.mock('../../../services/api/predictionsApi', () => ({
  getOddsFixtures: vi.fn(),
}));

vi.mock('../../../common/components/SectionSkeleton', () => ({
  SectionSkeleton: () => <div data-testid="section-skeleton" />,
}));

vi.mock('../../../common/components/InlineRetry', () => ({
  InlineRetry: ({ message }: { message: string }) => <div>{message}</div>,
}));

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: () => null,
}));

vi.mock('../../../common/ProbabilityBar', () => ({
  default: () => <div data-testid="probability-bar" />,
}));

vi.mock('../../../components/widgets/StrengthComparisonStrip', () => ({
  default: () => <div data-testid="strength-strip" />,
}));

vi.mock('../../../components/widgets/NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => <div data-testid="null-placeholder">{message}</div>,
}));

vi.mock('../../../components/widgets/AvailabilityTimeline', () => ({
  default: () => <div data-testid="availability-timeline" />,
}));

vi.mock('../../../components/widgets/PredictedXIBoard', () => ({
  default: () => <div data-testid="predicted-xi-board" />,
}));

vi.mock('../../../components/widgets/PredictionVsMarketCard', () => ({
  default: () => <div data-testid="prediction-vs-market" />,
}));

vi.mock('../../../components/widgets/DegradedBanner', () => ({
  default: () => <div data-testid="degraded-banner" />,
}));

vi.mock('../../../components/widgets/ConfidenceBadge', () => ({
  default: () => null,
}));

vi.mock('../../../components/widgets/StyleProfileCard', () => ({
  default: () => <div data-testid="style-profile-card" />,
}));

vi.mock('../../../components/widgets/ZoneHeatmap', () => ({
  default: () => <div data-testid="zone-heatmap" />,
}));

vi.mock('../../../components/widgets/ScorelineGrid', () => ({
  ScorelineGrid: () => <div data-testid="scoreline-grid" />,
  TopScoresCard: () => <div data-testid="top-scores-card" />,
}));

vi.mock('../../../components/Navigation/SideBar', () => ({
  Sidebar: () => null,
}));

vi.mock('../../../components/Social/SocialUserButtons', () => ({
  SocialUserButtons: () => null,
}));

import {
  fetchMatchPredictionWidget,
  fetchScorelineWidget,
  fetchAvailabilityWidget,
  fetchLineupWidget,
  fetchTacticalWidget,
} from '../../../services/api/widgetApi';
import { getOddsFixtures } from '../../../services/api/predictionsApi';

const FRESH = {
  source_fetched_at: null, snapshot_published_at: null,
  is_stale: false, is_degraded: false, stale_reason: null,
  sla_seconds: 21600, cascade_degraded: false, cascade_reason: null,
};

function makeMatchEnvelope(
  dataOverride = {}
): ApiEnvelope<MatchPredictionWidgetPayload> {
  return {
    data: {
      widget_type: 'match_prediction_card',
      data: {
        home_team: 'Arsenal', away_team: 'Chelsea',
        home_prob: 0.52, draw_prob: 0.27, away_prob: 0.21,
        prediction: 'Home', top_drivers: [], elo_home: null, elo_away: null,
        ...dataOverride,
      },
      explanation: { top_factors: [] },
      confidence: { score: 0.52, band: 'medium' },
      freshness: FRESH,
      summary: {},
    },
    freshness: FRESH, version: '1', warnings: [], generated_at: '',
  };
}

function renderHub(search = '?home=Arsenal&away=Chelsea&league=EPL&date=2025-05-01') {
  return render(
    <MemoryRouter initialEntries={[`/match/lookup${search}`]}>
      <Routes>
        <Route path="/match/lookup" element={<MatchIntelligenceHub />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('MatchIntelligenceHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchMatchPredictionWidget).mockResolvedValue(makeMatchEnvelope());
    vi.mocked(fetchScorelineWidget).mockResolvedValue({
      data: { widget_type: 'scoreline', data: { matrix: [], top_3_scorelines: [], over_under_probs: { over_2_5: 0.5, under_2_5: 0.5 }, btts_prob: 0.5 }, explanation: {}, confidence: { score: 0.5, band: 'medium' }, freshness: FRESH, summary: {} },
      freshness: FRESH, version: '1', warnings: [], generated_at: '',
    });
    vi.mocked(fetchAvailabilityWidget).mockResolvedValue({
      data: { widget_type: 'availability', data: null, explanation: {}, confidence: { score: 0.5, band: 'medium' }, freshness: FRESH, summary: {} },
      freshness: FRESH, version: '1', warnings: [], generated_at: '',
    });
    vi.mocked(fetchLineupWidget).mockResolvedValue({
      data: { widget_type: 'predicted_lineup', data: null, explanation: {}, confidence: { score: 0.5, band: 'medium' }, freshness: FRESH, summary: {} },
      freshness: FRESH, version: '1', warnings: [], generated_at: '',
    });
    vi.mocked(fetchTacticalWidget).mockResolvedValue({
      data: {
        widget_type: 'tactical_profile',
        data: {
          team: 'Arsenal',
          style_cluster: { id: 0, label: 'balanced_control', similar_teams: [] },
          zone_profiles: [],
        },
        explanation: {},
        confidence: { score: 0.5, band: 'medium' },
        freshness: FRESH,
        summary: {},
      },
      freshness: FRESH,
      version: '1',
      warnings: [],
      generated_at: '',
    });
    vi.mocked(getOddsFixtures).mockResolvedValue({
      data: { league: 'EPL', season: '2024', view: 'future', count: 0, fixtures: [] },
      freshness: FRESH, version: '1', warnings: [], generated_at: '',
    });
  });

  it('renders SectionSkeleton during fixture resolution', () => {
    vi.mocked(fetchMatchPredictionWidget).mockReturnValueOnce(new Promise(() => {}));
    renderHub();
    expect(screen.getAllByTestId('section-skeleton').length).toBeGreaterThan(0);
  });

  it('renders NullStatePlaceholder for missing home/away params', () => {
    renderHub('?league=EPL');
    expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
    expect(screen.getByText(/fixture not found/i)).toBeInTheDocument();
  });

  it('renders page title once fixture resolved', async () => {
    renderHub();
    expect(screen.getByText('Arsenal vs Chelsea')).toBeInTheDocument();
  });

  it('renders tactical unavailable message for non-La Liga league', async () => {
    renderHub('?home=Arsenal&away=Chelsea&league=EPL');
    await waitFor(() => {
      expect(screen.getByText(/tactical data not available for this league/i)).toBeInTheDocument();
    });
  });

  it('renders tactical components for La Liga', async () => {
    renderHub('?home=Real+Madrid&away=Barcelona&league=PD');
    await waitFor(() => {
      expect(screen.getAllByTestId('zone-heatmap').length).toBeGreaterThan(0);
    });
  });

    it('Block 6 renders tactical components for La Liga fixture (leagueCode=PD)', async () => {
    vi.mocked(fetchMatchPredictionWidget).mockResolvedValueOnce(makeMatchEnvelope());
    renderHub('?home=Barcelona&away=Real+Madrid&league=PD&date=2025-05-01');
    await waitFor(() => {
      expect(screen.getAllByTestId('zone-heatmap').length).toBeGreaterThan(0);
    });
  });
 
  it('Block 6 renders NullStatePlaceholder for non-La Liga fixture (leagueCode=PL)', async () => {
    vi.mocked(fetchMatchPredictionWidget).mockResolvedValueOnce(makeMatchEnvelope());
    renderHub('?home=Arsenal&away=Chelsea&league=PL&date=2025-05-01');
    await waitFor(() => {
      expect(screen.getByText(/tactical data not available for this league/i)).toBeInTheDocument();
    });
  });
});
