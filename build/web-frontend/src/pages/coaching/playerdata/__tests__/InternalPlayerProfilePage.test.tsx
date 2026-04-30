import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import InternalPlayerProfilePage from '../InternalPlayerProfilePage';

vi.mock('../../../../components/Navigation/SideBar', () => ({
  Sidebar: () => <nav aria-label="Sidebar" />,
}));

vi.mock('../../../../components/Social/SocialUserButtons', () => ({
  SocialUserButtons: () => <div data-testid="social-user-buttons" />,
}));

const { getPlayerOverviewMock, listEnrichedPlayersMock, browseClubsMock } = vi.hoisted(() => ({
  getPlayerOverviewMock: vi.fn<(...args: any[]) => Promise<any>>(),
  listEnrichedPlayersMock: vi.fn<(...args: any[]) => Promise<any>>(),
  browseClubsMock: vi.fn<(...args: any[]) => Promise<any>>(),
}));

vi.mock('../../../../services/api/playerdataApi', () => ({
  playerdataApi: {
    getPlayerOverview: getPlayerOverviewMock,
    listEnrichedPlayers: listEnrichedPlayersMock,
  },
}));

vi.mock('../../../../services/api', () => ({
  clubsApi: {
    browse: (...args: unknown[]) => browseClubsMock(...args),
  },
}));

describe('InternalPlayerProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    browseClubsMock.mockResolvedValue([
      { id: 11, name: 'Arsenal', club_type: 'system_professional', division: 'Premier League' },
    ]);

    listEnrichedPlayersMock.mockImplementation(({ search }: { search?: string }) => {
      if (search === 'nobody') {
        return Promise.resolve({ data: { results: [] } });
      }

      return Promise.resolve({
        data: {
          results: [
            {
              player: {
                id: 12,
                display_name: 'Bukayo Saka',
                full_name: 'Bukayo Saka',
                position: 'RW',
                nationality: 'England',
              },
              club: {
                id: 11,
                name: 'Arsenal',
              },
            },
          ],
        },
      });
    });

    getPlayerOverviewMock.mockResolvedValue({
      data: {
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
      },
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
      screen.getByText('Select a club above or search by name to browse players.')
    ).toBeInTheDocument();

    fireEvent.click(await screen.findByRole('button', { name: /Arsenal/i }, { timeout: 10000 }));
    fireEvent.click(await screen.findByRole('button', { name: /Bukayo Saka/i }, { timeout: 10000 }));

    await waitFor(() => {
      expect(getPlayerOverviewMock).toHaveBeenCalledWith(
        12,
        expect.objectContaining({})
      );
    }, { timeout: 10000 });

    expect(await screen.findByRole('heading', { name: 'Bukayo Saka' }, { timeout: 10000 })).toBeInTheDocument();
    expect(screen.getByText('High carrying and chance creation involvement.')).toBeInTheDocument();
  }, 15000);

  it('shows an empty-state message when search has no results', async () => {
    render(
      <MemoryRouter initialEntries={['/coaching/playerdata/player']}>
        <Routes>
          <Route path="/coaching/playerdata/player" element={<InternalPlayerProfilePage />} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('Search by player name…'), {
      target: { value: 'nobody' },
    });

    expect(await screen.findByText('No players found. Try a different search term or club.')).toBeInTheDocument();
  });
});