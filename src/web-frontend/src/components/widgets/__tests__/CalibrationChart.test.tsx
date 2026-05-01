import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import CalibrationChart from '../CalibrationChart';
import type { ConfidenceBucketAccuracy } from '../../../services/api/widgetApi';

vi.mock('../NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => (
    <div data-testid="null-placeholder">{message}</div>
  ),
}));

const BUCKETS: ConfidenceBucketAccuracy[] = [
  { band: 'high', total: 50, correct_count: 30, accuracy: 0.60 },
  { band: 'medium', total: 40, correct_count: 20, accuracy: 0.50 },
  { band: 'low', total: 30, correct_count: 12, accuracy: 0.40 },
];

describe('CalibrationChart', () => {
  it('renders three bars (one per confidence band)', () => {
    const { container } = render(<CalibrationChart buckets={BUCKETS} />);
    const bars = container.querySelectorAll('[class*="bar"]:not([class*="barTrack"]):not([class*="barGroup"])');
    expect(bars.length).toBeGreaterThanOrEqual(3);
  });

  it('bar height reflects accuracy prop via inline style', () => {
    const { container } = render(<CalibrationChart buckets={BUCKETS} />);
    const bars = container.querySelectorAll('[class*="high"]');
    const barEl = Array.from(bars).find(el => el.getAttribute('style')?.includes('height'));
    expect(barEl).toBeTruthy();
  });

  it('renders "No data" for band with null accuracy', () => {
    const withNull: ConfidenceBucketAccuracy[] = [
      { band: 'high', total: 0, correct_count: 0, accuracy: null },
      ...BUCKETS.slice(1),
    ];
    render(<CalibrationChart buckets={withNull} />);
    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('renders RANDOM_BASELINE_PCT reference line label', () => {
    render(<CalibrationChart buckets={BUCKETS} />);
    expect(screen.getByText(/Random.*33\.3/)).toBeInTheDocument();
  });

  it('renders MODEL_ACCURACY_BASELINE_PCT reference line label', () => {
    render(<CalibrationChart buckets={BUCKETS} />);
    expect(screen.getByText(/Model avg.*52\.4/)).toBeInTheDocument();
  });

  it('renders sample size below each bar', () => {
    render(<CalibrationChart buckets={BUCKETS} />);
    expect(screen.getByText('(n=50)')).toBeInTheDocument();
    expect(screen.getByText('(n=40)')).toBeInTheDocument();
    expect(screen.getByText('(n=30)')).toBeInTheDocument();
  });
});