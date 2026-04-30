import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import TacticalScoutingDashboard from '../TacticalScoutingDashboard';
import type { ApiEnvelope } from '../../../common/types/response';
import type { TacticalWidgetPayload } from '../../../services/api/widgetApi';

vi.mock('../../../services/api/widgetApi', () => ({
  fetchTacticalWidget: vi.fn(),
}));

vi.mock('../../../common/components/SectionSkeleton', () => ({
  SectionSkeleton: () => <div data-testid="section-skeleton" />,
}));

vi.mock('../../../common/components/InlineRetry', () => ({
  InlineRetry: ({ onRetry }: { onRetry: () => void }) => (
    <button onClick={onRetry}>Retry</button>
  ),
}));

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: ({ freshness }: { freshness: { staleness_status?: string } | null | undefined }) => (
    <span data-testid="freshness-badge" data-status={freshness?.staleness_status ?? ''} />
  ),
}));

vi.mock('../../../components/widgets/NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => (
    <div data-testid="null-placeholder">{message}</div>
  ),
}));

vi.mock('../../../components/widgets/ZoneHeatmap', () => ({
  default: () => <div data-testid="zone-heatmap" />,
}));

vi.mock('../../../components/widgets/StyleProfileCard', () => ({
  default: () => <div data-testid="style-profile-card" />,
}));

import { fetchTacticalWidget } from '../../../services/api/widgetApi';

const FRESH = {
  source_fetched_at: null, snapshot_published_at: null,
  is_stale: false, is_degraded: false, stale_reason: null,
  sla_seconds: 0, cascade_degraded: false, cascade_reason: null,
  staleness_status: 'static_dataset',
};

function makeEnvelope(data: TacticalWidgetPayload['data']): ApiEnvelope<TacticalWidgetPayload> {
  return {
    data: {
      widget_type: 'tactical_summary',
      data,
      explanation: {},
      confidence: { score: 0.75, band: 'medium' },
      freshness: FRESH as TacticalWidgetPayload['freshness'],
      summary: { coverage_note: 'La Liga coverage (StatsBomb Open Data)' },
    },
    freshness: FRESH as TacticalWidgetPayload['freshness'], version: '1', warnings: [], generated_at: '',
  };
}

const MOCK_DATA: NonNullable<TacticalWidgetPayload['data']> = {
  team: 'Barcelona',
  style_cluster: { id: 0, label: 'elite_final_third_possession', similar_teams: [] },
  zone_profiles: [{ zone_name: 'ATK-C', pass_success_rate: 0.72, pressure_rate: null, strength_flag: 'strength' }],
};

function renderPage(teamSlug = 'Barcelona') {
  return render(
    <MemoryRouter initialEntries={[`/tactics/${teamSlug}`]}>
      <Routes>
        <Route path="/tactics/:teamSlug" element={<TacticalScoutingDashboard />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('TacticalScoutingDashboard', () => {
  beforeEach(() => vi.clearAllMocks());

  it('does not render the old coverage notice banner', () => {
    vi.mocked(fetchTacticalWidget).mockReturnValueOnce(new Promise(() => {}));
    renderPage();
    expect(screen.queryByText(/tactical analysis powered by statsbomb open data/i)).not.toBeInTheDocument();
  });

  it('renders NullStatePlaceholder when data is null', async () => {
    vi.mocked(fetchTacticalWidget).mockResolvedValueOnce(makeEnvelope(null));
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
    });
  });

  it('renders ZoneHeatmap and StyleProfileCard when data present', async () => {
    vi.mocked(fetchTacticalWidget).mockResolvedValueOnce(makeEnvelope(MOCK_DATA));
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('zone-heatmap')).toBeInTheDocument();
      expect(screen.getByTestId('style-profile-card')).toBeInTheDocument();
    });
  });

  it('renders SectionSkeleton during load', () => {
    vi.mocked(fetchTacticalWidget).mockReturnValueOnce(new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId('section-skeleton')).toBeInTheDocument();
  });

  it('FreshnessBadge receives static_dataset staleness_status', async () => {
    vi.mocked(fetchTacticalWidget).mockResolvedValueOnce(makeEnvelope(MOCK_DATA));
    renderPage();
    await waitFor(() => {
      const badge = screen.getByTestId('freshness-badge');
      expect(badge.getAttribute('data-status')).toBe('static_dataset');
    });
  });
});