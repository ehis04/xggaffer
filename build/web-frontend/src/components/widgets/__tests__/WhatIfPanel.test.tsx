import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import WhatIfPanel from '../WhatIfPanel';
import type { TeamProjection } from '../../../services/api/widgetApi';

const TEAMS: TeamProjection[] = [
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
];

const FIXTURES = [
  { home_team: 'Arsenal', away_team: 'Chelsea', fixture_id: 'f1' },
  { home_team: 'Liverpool', away_team: 'Man City', fixture_id: 'f2' },
  { home_team: 'Spurs', away_team: 'Everton', fixture_id: 'f3' },
  { home_team: 'Newcastle', away_team: 'Wolves', fixture_id: 'f4' },
  { home_team: 'Villa', away_team: 'Brighton', fixture_id: 'f5' },
  { home_team: 'Brentford', away_team: 'Fulham', fixture_id: 'f6' },
];

describe('WhatIfPanel', () => {
  it('renders max WHATIF_MAX_FIXTURES fixture buttons', () => {
    const onAdjustment = vi.fn();
    render(<WhatIfPanel teams={TEAMS} fixtures={FIXTURES} onAdjustment={onAdjustment} />);
    const homeWinButtons = screen.getAllByRole('button', { name: /home win/i });
    expect(homeWinButtons).toHaveLength(5);
  });

  it('selecting home win calls onAdjustment with correct outcome', () => {
    const onAdjustment = vi.fn();
    render(<WhatIfPanel teams={TEAMS} fixtures={FIXTURES} onAdjustment={onAdjustment} />);
    fireEvent.click(screen.getAllByRole('button', { name: /home win/i })[0]);
    const call = onAdjustment.mock.calls[0][0];
    expect(call[0].selected_outcome).toBe('home');
    expect(call[0].fixture_id).toBe('f1');
  });

  it('reset button calls onAdjustment with all null outcomes', () => {
    const onAdjustment = vi.fn();
    render(<WhatIfPanel teams={TEAMS} fixtures={FIXTURES} onAdjustment={onAdjustment} />);
    fireEvent.click(screen.getAllByRole('button', { name: /home win/i })[0]);
    fireEvent.click(screen.getByRole('button', { name: /reset/i }));
    const lastCall = onAdjustment.mock.calls[onAdjustment.mock.calls.length - 1][0];
    expect(lastCall.every((a: { selected_outcome: null }) => a.selected_outcome === null)).toBe(true);
  });

  it('renders NullStatePlaceholder when fixtures is empty', () => {
    render(<WhatIfPanel teams={TEAMS} fixtures={[]} onAdjustment={vi.fn()} />);
    expect(screen.getByText(/no upcoming fixtures/i)).toBeInTheDocument();
  });

  it('shows scope label', () => {
    render(<WhatIfPanel teams={TEAMS} fixtures={FIXTURES} onAdjustment={vi.fn()} />);
    expect(screen.getByText(/not a full re-simulation/i)).toBeInTheDocument();
  });
});