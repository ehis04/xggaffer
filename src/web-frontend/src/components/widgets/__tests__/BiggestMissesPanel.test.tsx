import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import BiggestMissesPanel from '../BiggestMissesPanel';
import type { BiggestMiss } from '../../../services/api/widgetApi';

vi.mock('../UncertaintyNote', () => ({
  default: ({ message }: { message: string }) => (
    <p data-testid="uncertainty-note">{message}</p>
  ),
}));

const MISSES: BiggestMiss[] = [
  {
    home_team: 'Arsenal',
    away_team: 'Chelsea',
    predicted_outcome: 'H',
    actual_result: 'A',
    confidence_band: 'high',
    predicted_at: '2025-04-10T15:00:00Z',
  },
  {
    home_team: 'Liverpool',
    away_team: 'Man City',
    predicted_outcome: 'H',
    actual_result: 'D',
    confidence_band: 'high',
    predicted_at: '2025-04-03T15:00:00Z',
  },
];

describe('BiggestMissesPanel', () => {
  it('renders UncertaintyNote when misses is empty', () => {
    render(<BiggestMissesPanel misses={[]} />);
    expect(screen.getByTestId('uncertainty-note')).toBeInTheDocument();
    expect(screen.getByText(/no high-confidence misses/i)).toBeInTheDocument();
  });

  it('renders one row per miss', () => {
    const { container } = render(<BiggestMissesPanel misses={MISSES} />);
    const rows = container.querySelectorAll('[class*="missRow"]');
    expect(rows).toHaveLength(2);
  });

  it('renders HIGH_CONFIDENCE_MISS_LABEL badge per row', () => {
    render(<BiggestMissesPanel misses={MISSES} />);
    const badges = screen.getAllByText('High confidence miss');
    expect(badges).toHaveLength(2);
  });

  it('shows home_team, away_team, predicted_outcome and actual_result per row', () => {
    render(<BiggestMissesPanel misses={MISSES} />);
    expect(screen.getByText(/Arsenal vs Chelsea/)).toBeInTheDocument();
    expect(screen.getAllByText('H').length).toBeGreaterThan(0);
    expect(screen.getAllByText('A').length).toBeGreaterThan(0);
  });
});