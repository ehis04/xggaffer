import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ZoneHeatmap from '../ZoneHeatmap';
import type { ZoneProfile } from '../../../services/api/widgetApi';

vi.mock('../NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => (
    <div data-testid="null-placeholder">{message}</div>
  ),
}));

const ZONE_NAMES = [
  'ATK-L', 'ATK-C', 'ATK-R',
  'MID-L', 'MID-C', 'MID-R',
  'DEF-L', 'DEF-C', 'DEF-R',
];

function makeProfiles(overrides: Partial<ZoneProfile>[] = []): ZoneProfile[] {
  return ZONE_NAMES.map((name, i) => ({
    zone_name: name,
    pass_success_rate: 0.65,
    pressure_rate: null,
    strength_flag: 'neutral' as const,
    ...overrides[i],
  }));
}

describe('ZoneHeatmap', () => {
  it('renders NullStatePlaceholder when zoneProfiles is null', () => {
    render(<ZoneHeatmap zoneProfiles={null} team="Arsenal" />);
    expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
  });

  it('renders NullStatePlaceholder when zoneProfiles is empty array', () => {
    render(<ZoneHeatmap zoneProfiles={[]} team="Arsenal" />);
    expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
  });

  it('renders 9 zone cells when 9 profiles provided', () => {
    const { container } = render(
      <ZoneHeatmap zoneProfiles={makeProfiles()} team="Barcelona" />
    );
    const cells = container.querySelectorAll('[class*="cell"]');
    expect(cells.length).toBeGreaterThanOrEqual(9);
  });

  it('applies strength class to zones with strength_flag "strength"', () => {
    const profiles = makeProfiles([{ strength_flag: 'strength' }]);
    const { container } = render(
      <ZoneHeatmap zoneProfiles={profiles} team="Barcelona" />
    );
    const strengthCells = container.querySelectorAll('[class*="cellStrength"]');
    expect(strengthCells.length).toBeGreaterThan(0);
  });

  it('applies weakness class to zones with strength_flag "weakness"', () => {
    const profiles = makeProfiles([{}, { strength_flag: 'weakness' }]);
    const { container } = render(
      <ZoneHeatmap zoneProfiles={profiles} team="Barcelona" />
    );
    const weaknessCells = container.querySelectorAll('[class*="cellWeakness"]');
    expect(weaknessCells.length).toBeGreaterThan(0);
  });

  it('renders legend with three swatches', () => {
    const { container } = render(
      <ZoneHeatmap zoneProfiles={makeProfiles()} team="Barcelona" />
    );
    const swatches = container.querySelectorAll('[class*="legendSwatch"]');
    expect(swatches.length).toBe(3);
  });

  it('renders explanatory notes for reading the pitch', () => {
    render(<ZoneHeatmap zoneProfiles={makeProfiles()} team="Barcelona" />);
    expect(screen.getByText(/how to read this pitch/i)).toBeInTheDocument();
    expect(screen.getByText(/ATK-L means the attacking-left channel/i)).toBeInTheDocument();
    expect(screen.getByText(/colours are relative to this team's own zone profile/i)).toBeInTheDocument();
  });
});