import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../client';
import liveFootballApi from '../livefootballApi';

vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
  },
}));

describe('liveFootballApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({} as never);
  });

  it('uses the app-owned livefootball endpoint for the competition table', async () => {
    await liveFootballApi.getCompetitionTable(8, {
      season: ' 2024/2025 ',
      snapshot: ' latest ',
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      '/livefootball/competitions/8/table/',
      {
        season: '2024/2025',
        snapshot: 'latest',
      }
    );
  });

  it('uses the split fixtures endpoint and cleans params', async () => {
    await liveFootballApi.getCompetitionPreviousNextFixtures(4, {
      season: ' 2024/2025 ',
      previous_limit: 3,
      next_limit: 4,
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      '/livefootball/competitions/4/fixtures/split/',
      {
        season: '2024/2025',
        previous_limit: '3',
        next_limit: '4',
      }
    );
  });

  it('uses the scorers endpoint through the app API', async () => {
    await liveFootballApi.getCompetitionScorers(11, {
      season: '2024/2025',
      limit: 10,
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      '/livefootball/competitions/11/scorers/',
      {
        season: '2024/2025',
        limit: '10',
      }
    );
  });

  it('drops blank player-search params instead of leaking noisy query values', async () => {
    await liveFootballApi.searchPlayers({
      q: '  saka ',
      competition_id: undefined,
      team_id: null as any,
      season: '   ',
      active_only: true,
      limit: 5,
    });

    expect(apiClient.get).toHaveBeenCalledWith('/livefootball/players/search/', {
      q: 'saka',
      active_only: 'true',
      limit: '5',
    });
  });
});