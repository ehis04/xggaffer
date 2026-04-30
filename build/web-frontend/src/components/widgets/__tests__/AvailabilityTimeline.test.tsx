import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import AvailabilityTimeline from '../AvailabilityTimeline';
import type { AvailabilityData } from '../../../services/api/widgetApi';

vi.mock('../../../components/predictions/AvailabilityBadge', () => ({
  default: ({ riskLabel }: { riskLabel: string }) => (
    <span data-testid={`badge-${riskLabel}`}>{riskLabel}</span>
  ),
}));

vi.mock('../UncertaintyNote', () => ({
  default: ({ message }: { message: string }) => <p data-testid="uncertainty-note">{message}</p>,
}));

function makeAvailability(overrides: Partial<AvailabilityData> = {}): AvailabilityData {
  return {
    team: 'Arsenal',
    fixture_date: '2025-05-01',
    players: [
      { name: 'Saka', availability_prob: 0.92, risk_level: 'available', return_date_estimate: null },
      { name: 'Partey', availability_prob: 0.3, risk_level: 'unavailable', return_date_estimate: '2025-05-10' },
      { name: 'White', availability_prob: 0.55, risk_level: 'at_risk', return_date_estimate: null },
    ],
    summary: { available_count: 1, high_risk_count: 1, unavailable_count: 1 },
    ...overrides,
  };
}

describe('AvailabilityTimeline', () => {
  it('renders summary counts correctly', () => {
    render(<AvailabilityTimeline availability={makeAvailability()} />);
    expect(screen.getByText(/1 available/i)).toBeInTheDocument();
    expect(screen.getByText(/1 at risk/i)).toBeInTheDocument();
    expect(screen.getByText(/1 unavailable/i)).toBeInTheDocument();
  });

  it('groups unavailable players before at_risk and available', () => {
    render(<AvailabilityTimeline availability={makeAvailability()} />);
    const groups = screen.getAllByText(/^(Unavailable|At Risk|Available)$/i);
    const groupLabels = groups.map(el => el.textContent?.toLowerCase());
    const unavailIdx = groupLabels.findIndex(t => t?.includes('unavailable'));
    const atRiskIdx = groupLabels.findIndex(t => t?.includes('at risk'));
    expect(unavailIdx).toBeLessThan(atRiskIdx);
  });

  it('shows return_date_estimate when present', () => {
    render(<AvailabilityTimeline availability={makeAvailability()} />);
    expect(screen.getByText(/Est. return: 2025-05-10/i)).toBeInTheDocument();
  });

  it('renders UncertaintyNote when players list is empty', () => {
    const empty = makeAvailability({
      players: [],
      summary: { available_count: 0, high_risk_count: 0, unavailable_count: 0 },
    });
    render(<AvailabilityTimeline availability={empty} />);
    expect(screen.getByTestId('uncertainty-note')).toBeInTheDocument();
  });
});