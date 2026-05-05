import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import SimulatedLeagueTable from '../SimulatedLeagueTable';
import type { TeamProjection, WidgetFreshness } from '../../../services/api/widgetApi';

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: () => <span data-testid="freshness-badge" />,
}));

vi.mock('../DegradedBanner', () => ({
  default: ({ reason }: { reason: string }) => (
    <div data-testid="degraded-banner">{reason}</div>
  ),
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

function makeTeam(overrides: Partial<TeamProjection> = {}): TeamProjection {
  return {
    team_name: 'Arsenal',
    expected_position: 1,
    projected_points_median: 82.0,
    projected_points_p10: 74.0,
    projected_points_p90: 90.0,
    title_prob: 0.45,
    top4_prob: 0.92,
    relegation_prob: 0.0,
    position_distribution: { '1': 0.45, '2': 0.3 },
    ...overrides,
  };
}

const TEAMS: TeamProjection[] = [
  makeTeam({ team_name: 'Arsenal', expected_position: 1 }),
  makeTeam({ team_name: 'Chelsea', expected_position: 2, title_prob: 0.2 }),
  makeTeam({ team_name: 'Liverpool', expected_position: 3, title_prob: 0.15 }),
  makeTeam({ team_name: 'Man City', expected_position: 4, title_prob: 0.1 }),
  makeTeam({ team_name: 'Spurs', expected_position: 5, title_prob: 0.05, top4_prob: 0.4 }),
  ...Array.from({ length: 13 }, (_, i) =>
    makeTeam({
      team_name: `Team ${i + 6}`,
      expected_position: i + 6,
      title_prob: 0.0,
      top4_prob: 0.0,
      relegation_prob: i >= 10 ? 0.6 : 0.0,
    })
  ),
  makeTeam({ team_name: 'BottomA', expected_position: 18, relegation_prob: 0.8, title_prob: 0.0, top4_prob: 0.0 }),
  makeTeam({ team_name: 'BottomB', expected_position: 19, relegation_prob: 0.85, title_prob: 0.0, top4_prob: 0.0 }),
  makeTeam({ team_name: 'BottomC', expected_position: 20, relegation_prob: 0.9, title_prob: 0.0, top4_prob: 0.0 }),
];

describe('SimulatedLeagueTable', () => {
  it('renders all teams in ascending position order', () => {
    render(<SimulatedLeagueTable teams={TEAMS} leagueCode="PL" freshness={FRESH} />);
    const rows = screen.getAllByRole('row').slice(1);
    expect(rows[0]).toHaveTextContent('Arsenal');
    expect(rows[1]).toHaveTextContent('Chelsea');
  });

  it('applies top 4 class to first 4 rows', () => {
    const { container } = render(
      <SimulatedLeagueTable teams={TEAMS} leagueCode="PL" freshness={FRESH} />
    );
    const rows = container.querySelectorAll('tbody tr');
    for (let i = 0; i < 4; i++) {
      expect(rows[i].className).toMatch(/rowTop4/);
    }
    expect(rows[4].className).not.toMatch(/rowTop4/);
  });

  it('applies relegation class to rows 18-20 for PL', () => {
    const { container } = render(
      <SimulatedLeagueTable teams={TEAMS} leagueCode="PL" freshness={FRESH} />
    );
    const rows = container.querySelectorAll('tbody tr');
    expect(rows[17].className).toMatch(/rowRelegation/);
    expect(rows[16].className).not.toMatch(/rowRelegation/);
  });

  it('renders FreshnessBadge in header', () => {
    render(<SimulatedLeagueTable teams={TEAMS} leagueCode="PL" freshness={FRESH} />);
    expect(screen.getByTestId('freshness-badge')).toBeInTheDocument();
  });

  it('shows DegradedBanner when cascade_degraded is true', () => {
    const staleFreshness = { ...FRESH, cascade_degraded: true, cascade_reason: 'elo' };
    render(<SimulatedLeagueTable teams={TEAMS} leagueCode="PL" freshness={staleFreshness} />);
    expect(screen.getByTestId('degraded-banner')).toBeInTheDocument();
  });

  it('hides range column on mobile via CSS class', () => {
    const { container } = render(
      <SimulatedLeagueTable teams={TEAMS} leagueCode="PL" freshness={FRESH} />
    );
    const rangeCells = container.querySelectorAll('[class*="rangeCol"]');
    expect(rangeCells.length).toBeGreaterThan(0);
  });

  it('shows asterisk for team with manual adjustment', () => {
    const adjusted = new Set(['Arsenal']);
    render(
      <SimulatedLeagueTable
        teams={TEAMS}
        leagueCode="PL"
        freshness={FRESH}
        adjustedTeamNames={adjusted}
      />
    );
    expect(screen.getAllByText('*').length).toBeGreaterThan(0);
  });
});