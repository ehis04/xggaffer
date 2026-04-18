import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import InternalPlayerProfilePage from '../InternalPlayerProfilePage';

const { getPlayerOverviewMock } = vi.hoisted(() => ({
  getPlayerOverviewMock: vi.fn<(...args: any[]) => Promise<any>>(),
}));

vi.mock('../../../../services/api/playerdataApi', () => ({
  playerdataApi: {
    getPlayerOverview: getPlayerOverviewMock,
  },
}));

vi.mock('../../../../components/playerdiscovery/LeagueSelector', () => ({
  default: () => <div data-testid="league-selector" />,
}));

vi.mock('../../../../components/playerdiscovery/ClubSelector', () => ({
  default: () => <div data-testid="club-selector" />,
}));

vi.mock('../../../../components/playerdiscovery/PlayerSelector', () => ({
  default: ({ onChange }: { onChange: (player: any) => void }) => (
    <div>
      <button
        type="button"
        onClick={() =>
          onChange({
            id: 501,
            player_name: 'Bukayo Saka',
            first_name: 'Bukayo',
            last_name: 'Saka',
            nationality: 'England',
            primary_position: 'RW',
            raw_position: 'RW',
            squad_number: 7,
            provider: 'football-data',
            external_player_id: 'ext-501',
            is_active: true,
            team: {
              id: 11,
              name: 'Arsenal',
              short_name: 'Arsenal',
              tla: 'ARS',
              season_label: '2024/2025',
              provider: 'football-data',
              external_id: 'team-11',
              competition_id: 1,
              area_name: 'England',
              emblem_url: '',
              venue: 'Emirates Stadium',
              website: '',
              founded_year: 1886,
              last_synced_at: null,
            },
            canonical_player: {
              id: 12,
              display_name: 'Bukayo Saka',
              first_name: 'Bukayo',
              last_name: 'Saka',
            },
          })
        }
      >
        Choose canonical player
      </button>

      <button
        type="button"
        onClick={() =>
          onChange({
            id: 777,
            player_name: 'Local Only Player',
            first_name: 'Local',
            last_name: 'Only',
            nationality: 'Ireland',
            primary_position: 'CM',
            raw_position: 'CM',
            squad_number: 8,
            provider: 'football-data',
            external_player_id: 'ext-777',
            is_active: true,
            team: null,
            canonical_player: null,
          })
        }
      >
        Choose local-only player
      </button>
    </div>
  ),
}));

vi.mock('../../../../components/playerdiscovery/PlayerSearchInput', () => ({
  default: () => <div data-testid="player-search-input" />,
}));

describe('InternalPlayerProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    getPlayerOverviewMock.mockResolvedValue({
      player: {
        id: 12,
        display_name: 'Bukayo Saka',
        full_name: 'Bukayo Saka',
        short_name: 'Saka',
        primary_position: 'RW',
        nationality: 'England',
        age: 23,
      },
      club: {
        id: 11,
        name: 'Arsenal',
      },
      context: {
        season: '2024/2025',
        competition_name: 'Premier League',
        provider: 'understat',
        competition_id: 1,
        team_id: 11,
      },
      provider_coverage: null,
      general_overview: {
        headline: 'Strong wide forward output',
        summary: 'High carrying and chance creation involvement.',
        strengths: [],
        watchouts: [],
        notes: [],
      },
      metric_groups: [
        {
          key: 'attacking',
          label: 'Attacking',
          metrics: [
            {
              key: 'goals',
              label: 'Goals',
              value: 10,
              formatted_value: '10',
              source: 'understat',
              preferred_provider: 'understat',
            },
          ],
        },
      ],
      has_overview_data: true,
      missing_reasons: [],
    });
  });

  it('opens a merged profile from selector flow without manual id entry', async () => {
    render(
      <MemoryRouter initialEntries={['/coaching/playerdata/player']}>
        <Routes>
          <Route path="/coaching/playerdata/player" element={<InternalPlayerProfilePage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(
      screen.getByText('Select a player from discovery or search')
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Choose canonical player' }));
    fireEvent.click(screen.getByRole('button', { name: 'Open Selected Profile' }));

    await waitFor(() => {
      expect(getPlayerOverviewMock).toHaveBeenCalledWith(
        12,
        expect.objectContaining({})
      );
    });

    expect(await screen.findByText('Bukayo Saka')).toBeInTheDocument();
    expect(screen.getByText('Strong wide forward output')).toBeInTheDocument();
  });

  it('keeps the local-only fallback honest when no canonical link exists', () => {
    render(
      <MemoryRouter initialEntries={['/coaching/playerdata/player']}>
        <Routes>
          <Route path="/coaching/playerdata/player" element={<InternalPlayerProfilePage />} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Choose local-only player' }));

    expect(
      screen.getByText(
        'No canonical player link is available for the selected discovery player yet.'
      )
    ).toBeInTheDocument();

    expect(
      screen.getByRole('button', { name: 'Open Selected Profile' })
    ).toBeDisabled();
  });
});