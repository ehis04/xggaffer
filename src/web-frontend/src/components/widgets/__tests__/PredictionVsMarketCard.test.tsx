import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import PredictionVsMarketCard from '../PredictionVsMarketCard';
import type { OddsConsensus } from '../../../types/prediction';
import type { WidgetFreshness } from '../../../services/api/widgetApi';

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: () => <span data-testid="freshness-badge" />,
}));

vi.mock('../NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => <div data-testid="null-placeholder">{message}</div>,
}));

const FRESH: WidgetFreshness = {
  source_fetched_at: null,
  snapshot_published_at: null,
  is_stale: false,
  is_degraded: false,
  stale_reason: null,
  sla_seconds: 86400,
  cascade_degraded: false,
  cascade_reason: null,
};

const MODEL_PROBS = { home: 0.55, draw: 0.25, away: 0.20 };

const MARKET_DATA: OddsConsensus = {
  devig_home: 0.40,
  devig_draw: 0.28,
  devig_away: 0.32,
  overround: 0.05,
  favourite: 'home',
  source_label: 'Consensus (5 books)',
};

describe('PredictionVsMarketCard', () => {
  it('renders NullStatePlaceholder when marketData is null', () => {
    render(
      <PredictionVsMarketCard
        modelProbs={MODEL_PROBS}
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        marketData={null}
        freshness={FRESH}
      />
    );
    expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
  });

  it('renders both model and market columns', () => {
    render(
      <PredictionVsMarketCard
        modelProbs={MODEL_PROBS}
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        marketData={MARKET_DATA}
        freshness={FRESH}
      />
    );
    expect(screen.getByText('xgGaffer Model')).toBeInTheDocument();
    expect(screen.getByText('Bookmaker Market')).toBeInTheDocument();
  });

  it('highlights divergent outcome when delta > ODDS_DIVERGENCE_THRESHOLD', () => {
    const { container } = render(
      <PredictionVsMarketCard
        modelProbs={MODEL_PROBS}
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        marketData={MARKET_DATA}
        freshness={FRESH}
      />
    );
    const divergentCells = container.querySelectorAll('[class*="cellDivergent"]');
    expect(divergentCells.length).toBeGreaterThan(0);
  });

  it('shows source_label attribution', () => {
    render(
      <PredictionVsMarketCard
        modelProbs={MODEL_PROBS}
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        marketData={MARKET_DATA}
        freshness={FRESH}
      />
    );
    expect(screen.getByText('Consensus (5 books)')).toBeInTheDocument();
  });

  it('shows FreshnessBadge', () => {
    render(
      <PredictionVsMarketCard
        modelProbs={MODEL_PROBS}
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        marketData={MARKET_DATA}
        freshness={FRESH}
      />
    );
    expect(screen.getByTestId('freshness-badge')).toBeInTheDocument();
  });
});