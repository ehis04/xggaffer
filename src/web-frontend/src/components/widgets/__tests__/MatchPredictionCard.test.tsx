import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import MatchPredictionCard from '../MatchPredictionCard';

vi.mock('../../../services/api/widgetApi', () => ({
  fetchMatchPredictionWidget: vi.fn(),
}));

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: () => null,
}));

vi.mock('../../../common/ProbabilityBar', () => ({
  default: () => <div data-testid="probability-bar" />,
}));

import { fetchMatchPredictionWidget } from '../../../services/api/widgetApi';

const FRESH_FRESHNESS = {
  source_fetched_at: null,
  snapshot_published_at: null,
  is_stale: false,
  is_degraded: false,
  stale_reason: null,
  sla_seconds: 21600,
  cascade_degraded: false,
  cascade_reason: null,
};

function makeEnvelope(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      widget_type: 'match_prediction_card',
      data: {
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        home_prob: 0.52,
        draw_prob: 0.27,
        away_prob: 0.21,
        prediction: 'Home',
        top_drivers: [],
        elo_home: null,
        elo_away: null,
      },
      explanation: {},
      confidence: { score: 0.52, band: 'medium' as const },
      freshness: FRESH_FRESHNESS,
      summary: {},
      ...overrides,
    },
    freshness: FRESH_FRESHNESS,
    version: '1',
    warnings: [],
    generated_at: '2026-01-01T00:00:00Z',
  };
}

function renderCard(props = {}) {
  return render(
    <MemoryRouter>
      <MatchPredictionCard
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        kickoff="2026-05-10T15:00:00Z"
        leagueCode="EPL"
        fixtureId={1}
        {...props}
      />
    </MemoryRouter>
  );
}

describe('MatchPredictionCard', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders team names', async () => {
    vi.mocked(fetchMatchPredictionWidget).mockResolvedValueOnce(makeEnvelope());
    renderCard();
    expect(screen.getByText('Arsenal')).toBeInTheDocument();
    expect(screen.getByText('Chelsea')).toBeInTheDocument();
    expect(await screen.findByTestId('probability-bar')).toBeInTheDocument();
  });

  it('shows skeleton while loading', () => {
    vi.mocked(fetchMatchPredictionWidget).mockReturnValueOnce(new Promise(() => {}));
    const { container } = renderCard();
    expect(container.querySelector('[class*="skeleton"]')).toBeInTheDocument();
  });

  it('renders ProbabilityBar after successful load', async () => {
    vi.mocked(fetchMatchPredictionWidget).mockResolvedValueOnce(makeEnvelope());
    renderCard();
    await waitFor(() => {
      expect(screen.getByTestId('probability-bar')).toBeInTheDocument();
    });
  });

  it('shows uncertainty note on API failure', async () => {
    vi.mocked(fetchMatchPredictionWidget).mockRejectedValueOnce(new Error('fail'));
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('Prediction unavailable')).toBeInTheDocument();
    });
  });

  it('renders full analysis link after load', async () => {
    vi.mocked(fetchMatchPredictionWidget).mockResolvedValueOnce(makeEnvelope());
    renderCard();
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /full analysis/i })).toBeInTheDocument();
    });
  });

  it('shows DegradedBanner when cascade_degraded is true', async () => {
    vi.mocked(fetchMatchPredictionWidget).mockResolvedValueOnce(
      makeEnvelope({
        freshness: {
          ...FRESH_FRESHNESS,
          cascade_degraded: true,
          cascade_reason: 'elo',
        },
      })
    );
    renderCard();
    await waitFor(() => {
      expect(screen.getByText(/upstream data issue/i)).toBeInTheDocument();
    });
  });
});
