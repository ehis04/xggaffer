import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { FreshnessBadge } from '../FreshnessBadge';

vi.mock('../utils/freshness', () => ({
  getFreshnessState: vi.fn((freshness) => {
    if (!freshness) return 'unknown';
    if (freshness.is_degraded) return 'degraded';
    if (freshness.is_stale) return 'stale';
    return 'fresh';
  }),
  formatLastUpdated: vi.fn(() => null),
}));

const BASE_FRESHNESS = {
  source_fetched_at: null,
  snapshot_published_at: null,
  is_stale: false,
  is_degraded: false,
  stale_reason: null,
  sla_seconds: 21600,
};

describe('FreshnessBadge', () => {
  it('renders fresh badge when is_stale is false and no staleness_status override', () => {
    render(<FreshnessBadge freshness={BASE_FRESHNESS} />);
    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('renders stale badge when is_stale is true', () => {
    render(<FreshnessBadge freshness={{ ...BASE_FRESHNESS, is_stale: true, stale_reason: 'overdue' }} />);
    expect(screen.getByText('Stale')).toBeInTheDocument();
  });

  it('renders static dataset badge for staleness_status static_dataset', () => {
    render(<FreshnessBadge freshness={{ ...BASE_FRESHNESS, staleness_status: 'static_dataset' }} />);
    expect(screen.getByText('Static dataset')).toBeInTheDocument();
  });

  it('does not render fresh/stale/degraded for static_dataset status', () => {
    render(<FreshnessBadge freshness={{ ...BASE_FRESHNESS, staleness_status: 'static_dataset' }} />);
    expect(screen.queryByText('Live')).not.toBeInTheDocument();
    expect(screen.queryByText('Stale')).not.toBeInTheDocument();
    expect(screen.queryByText('Data issue')).not.toBeInTheDocument();
  });

  it('renders null for no_coverage status', () => {
    const { container } = render(
      <FreshnessBadge freshness={{ ...BASE_FRESHNESS, staleness_status: 'no_coverage' }} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders null for unknown freshness state (null input)', () => {
    const { container } = render(<FreshnessBadge freshness={null} />);
    expect(container.firstChild).toBeNull();
  });
});