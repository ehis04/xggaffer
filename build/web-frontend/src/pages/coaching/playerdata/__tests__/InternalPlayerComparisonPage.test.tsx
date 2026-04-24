import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import InternalPlayerComparisonPage from '../InternalPlayerComparisonPage';

const { getPlayerOverviewComparisonMock, listEnrichedPlayersMock, browseClubsMock } = vi.hoisted(() => ({
  getPlayerOverviewComparisonMock: vi.fn<(...args: any[]) => Promise<any>>(),
  listEnrichedPlayersMock: vi.fn<(...args: any[]) => Promise<any>>(),
  browseClubsMock: vi.fn<(...args: any[]) => Promise<any>>(),
}));

vi.mock('../../../../services/api/playerdataApi', () => ({
  playerdataApi: {
    getPlayerOverviewComparison: getPlayerOverviewComparisonMock,
    getPlayerOverview: vi.fn(),
    listEnrichedPlayers: listEnrichedPlayersMock,
  },
}));

vi.mock('../../../../services/api', () => ({
  clubsApi: {
    browse: (...args: unknown[]) => browseClubsMock(...args),
  },
}));

describe('InternalPlayerComparisonPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    browseClubsMock.mockResolvedValue([
      { id: 11, name: 'Arsenal', club_type: 'system_professional' },
      { id: 22, name: 'Manchester United', club_type: 'system_professional' },
    ]);

    listEnrichedPlayersMock.mockImplementation(({ club_id }: { club_id?: number }) => {
      if (club_id === 11) {
        return Promise.resolve({
          data: {
            results: [
              {
                player: {
                  id: 21,
                  display_name: 'Martin Ødegaard',
                  full_name: 'Martin Ødegaard',
                  position: 'AM',
                  nationality: 'Norway',
                },
                club: { id: 11, name: 'Arsenal' },
              },
            ],
          },
        });
      }

      if (club_id === 22) {
        return Promise.resolve({
          data: {
            results: [
              {
                player: {
                  id: 22,
                  display_name: 'Bruno Fernandes',
                  full_name: 'Bruno Fernandes',
                  position: 'AM',
                  nationality: 'Portugal',
                },
                club: { id: 22, name: 'Manchester United' },
              },
            ],
          },
        });
      }

      return Promise.resolve({ data: { results: [] } });
    });

    getPlayerOverviewComparisonMock.mockResolvedValue({
      data: {
        context: {
          season: '2024/2025',
          competition_name: 'Premier League',
          provider: 'understat',
        },
        player_a: {
          player: {
            id: 21,
            display_name: 'Martin Ødegaard',
            primary_position: 'AM',
          },
          club: {
            id: 11,
            name: 'Arsenal',
          },
          context: {
            competition_id: 1,
          },
        },
        player_b: {
          player: {
            id: 22,
            display_name: 'Bruno Fernandes',
            primary_position: 'AM',
          },
          club: {
            id: 22,
            name: 'Manchester United',
          },
          context: {
            competition_id: 1,
          },
        },
        overall_winner: {
          winner: 'player_b',
          reason: 'Higher end-product output across the comparison window.',
        },
        general_overview: {
          headline: 'Creative midfield comparison',
          summary: 'Player B edges the overall output.',
          strengths: [],
          watchouts: [],
          notes: [],
        },
        summary_lines: ['Player B leads chance creation.'],
        provider_coverage: null,
        metric_groups: [
          {
            key: 'creation',
            label: 'Chance Creation',
            metrics: [
              {
                key: 'key_passes',
                label: 'Key Passes',
                player_a_value: 2.4,
                player_a_formatted: '2.4',
                player_b_value: 2.9,
                player_b_formatted: '2.9',
                winner: 'player_b',
                is_tie: false,
                sentence: 'Player B produces more key passes.',
                source: 'understat',
                preferred_provider: 'understat',
              },
            ],
          },
        ],
        has_comparison_data: true,
        missing_reasons: [],
      },
    });
  });

  it('loads merged comparison from selected players without manual raw id entry', async () => {
    render(
      <MemoryRouter initialEntries={['/coaching/playerdata/compare']}>
        <Routes>
          <Route path="/coaching/playerdata/compare" element={<InternalPlayerComparisonPage />} />
        </Routes>
      </MemoryRouter>
    );

    const arsenalButtons = await screen.findAllByRole('button', { name: 'Arsenal' });
    fireEvent.click(arsenalButtons[0]);
    fireEvent.click(await screen.findByRole('button', { name: /Martin Ødegaard/i }));

    const unitedButtons = await screen.findAllByRole('button', { name: 'Manchester United' });
    fireEvent.click(unitedButtons[0]);
    fireEvent.click(await screen.findByRole('button', { name: /Bruno Fernandes/i }));

    await waitFor(() => {
      expect(getPlayerOverviewComparisonMock).toHaveBeenCalledWith(
        expect.objectContaining({
          player_a_id: 21,
          player_b_id: 22,
        })
      );
    }, { timeout: 10000 });

    expect(await screen.findAllByText('Martin Ødegaard')).not.toHaveLength(0);
    expect(screen.getAllByText('Bruno Fernandes')).not.toHaveLength(0);
    expect(screen.getByText('Chance Creation')).toBeInTheDocument();
  }, 15000);
});