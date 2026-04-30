import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import StrengthComparisonStrip from '../StrengthComparisonStrip';
import type { WidgetFreshness } from '../../../services/api/widgetApi';

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: () => <span data-testid="freshness-badge" />,
}));

vi.mock('../NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => <div data-testid="null-placeholder">{message}</div>,
}));

vi.mock('../UncertaintyNote', () => ({
  default: ({ message }: { message: string }) => <p data-testid="uncertainty-note">{message}</p>,
}));

const FRESH: WidgetFreshness = {
  source_fetched_at: null,
  snapshot_published_at: null,
  is_stale: false,
  is_degraded: false,
  stale_reason: null,
  sla_seconds: 21600,
  cascade_degraded: false,
  cascade_reason: null,
};

describe('StrengthComparisonStrip', () => {
  it('renders NullStatePlaceholder when both elo values are null', () => {
    render(
      <StrengthComparisonStrip
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        homeElo={null}
        awayElo={null}
        freshness={FRESH}
      />
    );
    expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
    expect(screen.getByText(/elo strength ratings not available/i)).toBeInTheDocument();
  });

  it('renders delta text when both elo values are present', () => {
    render(
      <StrengthComparisonStrip
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        homeElo={1650}
        awayElo={1600}
        freshness={FRESH}
      />
    );
    expect(screen.getByText(/Arsenal rated 50 points higher/i)).toBeInTheDocument();
  });

  it('renders FreshnessBadge when elo values present', () => {
    render(
      <StrengthComparisonStrip
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        homeElo={1650}
        awayElo={1600}
        freshness={FRESH}
      />
    );
    expect(screen.getByTestId('freshness-badge')).toBeInTheDocument();
  });

  it('renders UncertaintyNote when one elo value is null', () => {
    render(
      <StrengthComparisonStrip
        homeTeam="Arsenal"
        awayTeam="Chelsea"
        homeElo={1650}
        awayElo={null}
        freshness={FRESH}
      />
    );
    expect(screen.getByTestId('uncertainty-note')).toBeInTheDocument();
  });
});