import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import PredictedXIBoard from '../PredictedXIBoard';
import type { LineupData } from '../../../services/api/widgetApi';

vi.mock('../NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => <div data-testid="null-placeholder">{message}</div>,
}));

const PLAYERS = [
  { name: 'Raya', position: 'GK', start_prob: 0.97, stable_id: '1' },
  { name: 'White', position: 'RB', start_prob: 0.88, stable_id: '2' },
  { name: 'Saliba', position: 'CB', start_prob: 0.95, stable_id: '3' },
  { name: 'Gabriel', position: 'CB', start_prob: 0.93, stable_id: '4' },
  { name: 'Timber', position: 'LB', start_prob: 0.85, stable_id: '5' },
  { name: 'Partey', position: 'CM', start_prob: 0.72, stable_id: '6' },
  { name: 'Rice', position: 'CM', start_prob: 0.98, stable_id: '7' },
  { name: 'Odegaard', position: 'CAM', start_prob: 0.96, stable_id: '8' },
  { name: 'Saka', position: 'RW', start_prob: 0.99, stable_id: '9' },
  { name: 'Martinelli', position: 'LW', start_prob: 0.87, stable_id: '10' },
  { name: 'Havertz', position: 'ST', start_prob: 0.83, stable_id: '11' },
];

function makeLineup(overrides: Partial<LineupData> = {}): LineupData {
  return {
    team: 'Arsenal',
    fixture_date: '2025-05-01',
    formation: '4-3-3',
    predicted_xi: PLAYERS,
    bench_candidates: [],
    ...overrides,
  };
}

describe('PredictedXIBoard', () => {
  it('renders all 11 player names', () => {
    render(<PredictedXIBoard lineup={makeLineup()} />);
    for (const p of PLAYERS) {
      expect(screen.getAllByText(p.name).length).toBeGreaterThan(0);
    }
  });

  it('renders NullStatePlaceholder when predicted_xi is empty', () => {
    render(<PredictedXIBoard lineup={makeLineup({ predicted_xi: [] })} />);
    expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
  });

  it('applies green class to player with start_prob >= 0.8', () => {
    const { container } = render(<PredictedXIBoard lineup={makeLineup()} />);
    const markers = container.querySelectorAll('[class*="playerGreen"]');
    expect(markers.length).toBeGreaterThan(0);
  });

  it('applies red class to player with start_prob < 0.6', () => {
    const lowConfPlayer = [{ ...PLAYERS[0], start_prob: 0.45, name: 'LowConf' }];
    const { container } = render(
      <PredictedXIBoard lineup={makeLineup({ predicted_xi: lowConfPlayer })} />
    );
    const markers = container.querySelectorAll('[class*="playerRed"]');
    expect(markers.length).toBeGreaterThan(0);
  });

  it('renders mobileView element for mobile list', () => {
    const { container } = render(<PredictedXIBoard lineup={makeLineup()} />);
    expect(container.querySelector('[class*="mobileView"]')).toBeInTheDocument();
  });
});