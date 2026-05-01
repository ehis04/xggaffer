import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import RotatingLeaguePreviewCard from '../RotatingLeaguePreviewCard';

const cards = [
  {
    competition: {
      id: 1,
      code: 'PL',
      name: 'Premier League',
      country: 'England',
      emblem_url: '',
    },
    synced_at: '2026-03-30T09:59:00Z',
    top_rows: [
      {
        position: 1,
        team: { id: 1, name: 'Arsenal', short_name: 'Arsenal', crest_url: '' },
        played: 30,
        won: 22,
        drawn: 4,
        lost: 4,
        goals_for: 60,
        goals_against: 25,
        goal_difference: 35,
        points: 70,
        form_label: 'W-W-W-D-W',
      },
    ],
    bottom_rows: [
      {
        position: 20,
        team: { id: 2, name: 'Bottom FC', short_name: 'Bottom', crest_url: '' },
        played: 30,
        won: 2,
        drawn: 5,
        lost: 23,
        goals_for: 20,
        goals_against: 70,
        goal_difference: -50,
        points: 11,
        form_label: 'L-L-L-D-L',
      },
    ],
    cta: {
      label: 'View league',
      path: '/livefootball/leagues',
      query: { competition: 'PL' },
    },
  },
  {
    competition: {
      id: 2,
      code: 'LL',
      name: 'La Liga',
      country: 'Spain',
      emblem_url: '',
    },
    synced_at: '2026-03-30T09:59:00Z',
    top_rows: [
      {
        position: 1,
        team: { id: 3, name: 'Real Madrid', short_name: 'Real', crest_url: '' },
        played: 30,
        won: 23,
        drawn: 5,
        lost: 2,
        goals_for: 68,
        goals_against: 24,
        goal_difference: 44,
        points: 74,
        form_label: 'W-W-W-W-W',
      },
    ],
    bottom_rows: [
      {
        position: 20,
        team: { id: 4, name: 'Bottom Liga', short_name: 'Bottom', crest_url: '' },
        played: 30,
        won: 2,
        drawn: 6,
        lost: 22,
        goals_for: 19,
        goals_against: 66,
        goal_difference: -47,
        points: 12,
        form_label: 'L-L-D-L-L',
      },
    ],
    cta: {
      label: 'View league',
      path: '/livefootball/leagues',
      query: { competition: 'LL' },
    },
  },
];

describe('RotatingLeaguePreviewCard', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the first card initially', () => {
    render(
      <MemoryRouter>
        <RotatingLeaguePreviewCard cards={cards as any} />
      </MemoryRouter>
    );

    expect(screen.getByText('Premier League')).toBeInTheDocument();
    const viewLeagueLinks = screen.getAllByRole('link', { name: /View league/i });
    expect(viewLeagueLinks.length).toBeGreaterThan(0);
    expect(
      viewLeagueLinks.some((link) => link.getAttribute('href') === '/livefootball/leagues?competition=PL')
    ).toBe(true);
  });

  it('rotates to the next league after 5 seconds', () => {
    render(
      <MemoryRouter>
        <RotatingLeaguePreviewCard cards={cards as any} />
      </MemoryRouter>
    );

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText('La Liga')).toBeInTheDocument();
    const viewLeagueLinks = screen.getAllByRole('link', { name: /View league/i });
    expect(viewLeagueLinks.length).toBeGreaterThan(0);
    expect(
      viewLeagueLinks.some((link) => link.getAttribute('href') === '/livefootball/leagues?competition=LL')
    ).toBe(true);
  });

  it('pauses rotation while hovered', () => {
    render(
      <MemoryRouter>
        <RotatingLeaguePreviewCard cards={cards as any} />
      </MemoryRouter>
    );

    const section = screen.getByText('League snapshot').closest('section');
    expect(section).not.toBeNull();

    fireEvent.mouseEnter(section!);

    act(() => {
      vi.advanceTimersByTime(7000);
    });

    expect(screen.getByText('Premier League')).toBeInTheDocument();

    fireEvent.mouseLeave(section!);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText('La Liga')).toBeInTheDocument();
  });

  it('moves to the next league when the next arrow is clicked', () => {
    render(
      <MemoryRouter>
        <RotatingLeaguePreviewCard cards={cards as any} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /Next league/i }));

    expect(screen.getByText('La Liga')).toBeInTheDocument();
  });

  it('moves to the previous league when the previous arrow is clicked', () => {
    render(
      <MemoryRouter>
        <RotatingLeaguePreviewCard cards={cards as any} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /Previous league/i }));

    expect(screen.getByText('La Liga')).toBeInTheDocument();
  });
});