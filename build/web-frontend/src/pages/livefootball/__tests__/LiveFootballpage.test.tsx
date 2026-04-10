import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LiveFootballPage from '../LiveFootballPage';
import liveFootballApi from '../../../services/api/livefootballApi';

vi.mock('../../../services/api/livefootballApi', () => ({
  default: {
    getCompetitions: vi.fn(),
    getCompetitionTable: vi.fn(),
    getCompetitionPreviousNextFixtures: vi.fn(),
    getCompetitionScorers: vi.fn(),
  },
}));

const competitions = [
  {
    id: 1,
    provider: 'football-data',
    external_id: 'pl',
    code: 'PL',
    name: 'Premier League',
    area_name: 'England',
    emblem_url: '',
    current_season_label: '2024/2025',
  },
  {
    id: 2,
    provider: 'football-data',
    external_id: 'sa',
    code: 'SA',
    name: 'Serie A',
    area_name: 'Italy',
    emblem_url: '',
    current_season_label: '2024/2025',
  },
];

describe('LiveFootballPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(liveFootballApi.getCompetitions).mockResolvedValue(competitions as any);

    vi.mocked(liveFootballApi.getCompetitionTable).mockImplementation(async (competitionId) => ({
      competition: competitions.find((item) => item.id === competitionId)!,
      season_label: '2024/2025',
      snapshot_label: 'Latest',
      rows: [
        {
          position: 1,
          team: {
            id: competitionId === 1 ? 10 : 20,
            external_id: competitionId === 1 ? 'arsenal' : 'inter',
            name: competitionId === 1 ? 'Arsenal' : 'Inter',
            short_name: competitionId === 1 ? 'Arsenal' : 'Inter',
            tla: competitionId === 1 ? 'ARS' : 'INT',
            emblem_url: '',
          },
          played: 28,
          won: 20,
          drawn: 4,
          lost: 4,
          goals_for: 60,
          goals_against: 20,
          goal_difference: 40,
          points: 64,
          form: 'WWWWW',
        },
      ],
    }) as any);

    vi.mocked(liveFootballApi.getCompetitionPreviousNextFixtures).mockImplementation(
      async (competitionId) =>
        ({
          competition: competitions.find((item) => item.id === competitionId)!,
          season_label: '2024/2025',
          previous: [
            {
              id: competitionId * 100 + 1,
              external_match_id: `prev-${competitionId}`,
              season_label: '2024/2025',
              status: 'FINISHED',
              kickoff_at: '2026-03-12T15:00:00Z',
              matchday: 28,
              home_team: {
                id: 1,
                external_id: 'home',
                name: competitionId === 1 ? 'Arsenal' : 'Inter',
                short_name: competitionId === 1 ? 'Arsenal' : 'Inter',
                tla: competitionId === 1 ? 'ARS' : 'INT',
                emblem_url: '',
              },
              away_team: {
                id: 2,
                external_id: 'away',
                name: competitionId === 1 ? 'Chelsea' : 'Milan',
                short_name: competitionId === 1 ? 'Chelsea' : 'Milan',
                tla: competitionId === 1 ? 'CHE' : 'MIL',
                emblem_url: '',
              },
              home_score: 2,
              away_score: 0,
            },
          ],
          next: [],
        }) as any
    );

    vi.mocked(liveFootballApi.getCompetitionScorers).mockImplementation(async (competitionId) => ({
      competition: competitions.find((item) => item.id === competitionId)!,
      season_label: '2024/2025',
      count: 1,
      items: [
        {
          rank: 1,
          external_player_id: `top-${competitionId}`,
          player_name: competitionId === 1 ? 'Bukayo Saka' : 'Lautaro Martínez',
          goals: competitionId === 1 ? 14 : 18,
          penalties: 2,
          team: {
            id: competitionId === 1 ? 10 : 20,
            external_id: 'team',
            name: competitionId === 1 ? 'Arsenal' : 'Inter',
            short_name: competitionId === 1 ? 'Arsenal' : 'Inter',
            tla: competitionId === 1 ? 'ARS' : 'INT',
            emblem_url: '',
          },
          canonical_player: {
            id: competitionId === 1 ? 701 : 702,
            display_name: competitionId === 1 ? 'Bukayo Saka' : 'Lautaro Martínez',
          },
        },
      ],
    }) as any);
  });

  it('loads competitions and renders table, fixtures and scorers', async () => {
    render(<LiveFootballPage />);

    expect(await screen.findByText('Live Football')).toBeInTheDocument();
    expect((await screen.findAllByText('Arsenal')).length).toBeGreaterThan(0);
    expect(await screen.findByText('Bukayo Saka')).toBeInTheDocument();
    expect(screen.getByText('Recent results')).toBeInTheDocument();

    expect(liveFootballApi.getCompetitionTable).toHaveBeenCalledWith(1, {
      season: '2024/2025',
    });
    expect(liveFootballApi.getCompetitionPreviousNextFixtures).toHaveBeenCalledWith(1, {
      season: '2024/2025',
      previous_limit: 5,
      next_limit: 5,
    });
    expect(liveFootballApi.getCompetitionScorers).toHaveBeenCalledWith(1, {
      season: '2024/2025',
      limit: 10,
    });
  });

  it('re-fetches browse data when the competition changes', async () => {
    render(<LiveFootballPage />);

    const select = await screen.findByLabelText('Competition');
    fireEvent.change(select, { target: { value: '2' } });

    await waitFor(() => {
      expect(liveFootballApi.getCompetitionTable).toHaveBeenLastCalledWith(2, {
        season: '2024/2025',
      });
    });

    expect(await screen.findByText('Serie A')).toBeInTheDocument();
    expect((await screen.findAllByText('Inter')).length).toBeGreaterThan(0);
    expect(await screen.findByText('Lautaro Martínez')).toBeInTheDocument();
  });
});