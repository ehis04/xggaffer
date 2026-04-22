import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import LiveFootballBasePage from '../LiveFootballBasePage';
import { getLiveFootballOverview } from '../../../services/api/livefootballApi';

vi.mock('../../../services/api/livefootballApi', () => ({
  getLiveFootballOverview: vi.fn(),
}));

vi.mock('../../../components/livefootball/home/LiveFootballHeroHeader', () => ({
  default: ({ generatedAt }: { generatedAt?: string | null }) => (
    <div data-testid="hero-header">hero-{generatedAt ?? 'none'}</div>
  ),
}));

vi.mock('../../../components/livefootball/home/RotatingLeaguePreviewCard', () => ({
  default: ({ cards }: { cards: unknown[] }) => (
    <div data-testid="rotating-card">cards-{cards.length}</div>
  ),
}));

vi.mock('../../../components/livefootball/home/AllTimeStreaksPreview', () => ({
  default: ({ data }: { data: { all_time: unknown[]; current: unknown[] } }) => (
    <div data-testid="streaks-preview">
      streaks-{data.all_time.length + data.current.length}
    </div>
  ),
}));

vi.mock('../../../components/livefootball/home/TrendSection', () => ({
  default: ({ title }: { title: string }) => <div>{title}</div>,
}));

vi.mock('../../../components/livefootball/home/LeagueMatchesSection', () => ({
  default: ({ title }: { title: string }) => <div>{title}</div>,
}));

vi.mock('../../../components/livefootball/home/FirstVsLastLeagueSection', () => ({
  default: ({ title }: { title: string }) => <div>{title}</div>,
}));

const mockedGetLiveFootballOverview = vi.mocked(getLiveFootballOverview);

const overviewPayload = {
  generated_at: '2026-03-30T10:00:00Z',
  league_order: ['PL', 'LL', 'BL1', 'SA', 'FL1', 'RPL'],
  league_snapshot: [
    {
      competition: {
        id: 1,
        code: 'PL',
        name: 'Premier League',
        country: 'England',
        emblem_url: '',
      },
      synced_at: '2026-03-30T09:59:00Z',
      top_rows: [],
      bottom_rows: [],
      cta: {
        label: 'View league',
        path: '/livefootball/leagues',
        query: { competition: 'PL' },
      },
    },
  ],
  top_performing_teams: { updated_at: null, items: [] },
  top_performing_scorers: { updated_at: null, items: [] },
  latest_hat_tricks: { updated_at: null, items: [] },
  strikers_with_a_lull: { updated_at: null, items: [] },
  recent_matches_by_league: [],
  upcoming_matches_by_league: [],
  first_vs_last_by_league: [],
  all_time_streaks: {
    updated_at: null,
    all_time: [],
    current: [],
    cta: { label: 'View streaks', path: '/livefootball/streaks', query: {} },
  },
};

describe('LiveFootballBasePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state first', () => {
    mockedGetLiveFootballOverview.mockReturnValue(new Promise(() => {}));

    render(
      <MemoryRouter>
        <LiveFootballBasePage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Loading Live Football overview/i)).toBeInTheDocument();
  });

  it('renders error state when overview request fails', async () => {
    mockedGetLiveFootballOverview.mockRejectedValue(new Error('boom'));

    render(
      <MemoryRouter>
        <LiveFootballBasePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Live Football overview unavailable/i)
      ).toBeInTheDocument();
    });
  });

  it('renders success state with core homepage sections', async () => {
    mockedGetLiveFootballOverview.mockResolvedValue({ data: overviewPayload } as any);

    render(
      <MemoryRouter>
        <LiveFootballBasePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('hero-header')).toBeInTheDocument();
    });

    expect(screen.getByTestId('rotating-card')).toHaveTextContent('cards-1');
    expect(screen.getByText('Top performing teams')).toBeInTheDocument();
    expect(screen.getByText('Recent matches by league')).toBeInTheDocument();
    expect(screen.getByText('First vs last by league')).toBeInTheDocument();
  });

  it('only makes one overview request on initial render', async () => {
    mockedGetLiveFootballOverview.mockResolvedValue({ data: overviewPayload } as any);

    render(
      <MemoryRouter>
        <LiveFootballBasePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockedGetLiveFootballOverview).toHaveBeenCalledTimes(1);
    });
  });
});