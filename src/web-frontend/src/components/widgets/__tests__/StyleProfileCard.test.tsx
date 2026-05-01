import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import StyleProfileCard from '../StyleProfileCard';
import type { StyleCluster } from '../../../services/api/widgetApi';

vi.mock('../NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => (
    <div data-testid="null-placeholder">{message}</div>
  ),
}));

const MAX_SIMILAR_TEAMS_DISPLAYED = 4;

function makeCluster(overrides: Partial<StyleCluster> = {}): StyleCluster {
  return {
    id: 0,
    label: 'elite_final_third_possession',
    similar_teams: ['Real Madrid', 'Manchester City', 'Bayern Munich', 'PSG', 'Liverpool'],
    ...overrides,
  };
}

describe('StyleProfileCard', () => {
  it('renders NullStatePlaceholder when styleCluster is null', () => {
    render(<StyleProfileCard styleCluster={null} />);
    expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
  });

  it('renders cluster label', () => {
    render(<StyleProfileCard styleCluster={makeCluster()} />);
    expect(screen.getByText(/elite final.third possession/i)).toBeInTheDocument();
  });

  it('renders up to MAX_SIMILAR_TEAMS_DISPLAYED similar teams', () => {
    render(<StyleProfileCard styleCluster={makeCluster()} />);
    const chips = screen.getAllByText(/Real Madrid|Manchester City|Bayern Munich|PSG/i);
    expect(chips.length).toBeLessThanOrEqual(MAX_SIMILAR_TEAMS_DISPLAYED);
  });

  it('does not render more than MAX_SIMILAR_TEAMS_DISPLAYED teams', () => {
    const cluster = makeCluster({
      similar_teams: ['A', 'B', 'C', 'D', 'E', 'F'],
    });
    render(<StyleProfileCard styleCluster={cluster} />);
    const chips = screen.queryAllByText(/^[A-F]$/);
    expect(chips.length).toBeLessThanOrEqual(MAX_SIMILAR_TEAMS_DISPLAYED);
  });
});