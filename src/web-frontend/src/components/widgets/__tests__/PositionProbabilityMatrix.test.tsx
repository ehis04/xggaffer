import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import PositionProbabilityMatrix from '../PositionProbabilityMatrix';
import type { TeamProjection } from '../../../services/api/widgetApi';

function makeTeam(name: string, pos: number, dist: Record<string, number> = {}): TeamProjection {
  return {
    team_name: name,
    expected_position: pos,
    projected_points_median: 50,
    projected_points_p10: null,
    projected_points_p90: null,
    title_prob: 0.1,
    top4_prob: 0.4,
    relegation_prob: 0.1,
    position_distribution: dist,
  };
}

const THREE_TEAMS: TeamProjection[] = [
  makeTeam('Arsenal', 1, { '1': 0.6, '2': 0.3, '3': 0.1 }),
  makeTeam('Chelsea', 2, { '1': 0.2, '2': 0.5, '3': 0.3 }),
  makeTeam('Liverpool', 3, { '1': 0.1, '2': 0.3, '3': 0.6 }),
];

describe('PositionProbabilityMatrix', () => {
  it('renders N×N grid for N teams', () => {
    const { container } = render(<PositionProbabilityMatrix teams={THREE_TEAMS} />);
    const bodyRows = container.querySelectorAll('tbody tr');
    expect(bodyRows).toHaveLength(3);
    const firstRowCells = bodyRows[0].querySelectorAll('td');
    expect(firstRowCells).toHaveLength(3);
  });

  it('highlights peak probability cell per row with cellPeak class', () => {
    const { container } = render(<PositionProbabilityMatrix teams={THREE_TEAMS} />);
    const bodyRows = container.querySelectorAll('tbody tr');
    const firstRowCells = bodyRows[0].querySelectorAll('td');
    expect(firstRowCells[0].className).toMatch(/cellPeak/);
  });

  it('renders dash for team with empty position_distribution', () => {
    const teams = [makeTeam('Arsenal', 1, {})];
    render(<PositionProbabilityMatrix teams={teams} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('wraps in scrollable container', () => {
    const { container } = render(<PositionProbabilityMatrix teams={THREE_TEAMS} />);
    const wrapper = container.querySelector('[class*="scrollWrapper"]');
    expect(wrapper).toBeInTheDocument();
  });
});