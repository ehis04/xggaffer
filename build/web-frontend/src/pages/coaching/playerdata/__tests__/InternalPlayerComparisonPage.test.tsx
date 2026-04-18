import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import InternalPlayerComparisonPage from '../InternalPlayerComparisonPage';

const { getPlayerOverviewComparisonMock } = vi.hoisted(() => ({
  getPlayerOverviewComparisonMock: vi.fn<(...args: any[]) => Promise<any>>(),
}));

vi.mock('../../../../services/api/playerdataApi', () => ({
  playerdataApi: {
    getPlayerOverviewComparison: getPlayerOverviewComparisonMock,
  },
}));

vi.mock('../../../../components/playerdiscovery/LeagueSelector', () => ({
  default: () => <div data-testid="league-selector" />,
}));

vi.mock('../../../../components/playerdiscovery/ClubSelector', () => ({
  default: () => <div data-testid="club-selector" />,
}));

vi.mock('../../../../components/playerdiscovery/PlayerSelector', () => ({
  default: ({
    label,
    onChange,
  }: {
    label: string;
    onChange: (player: any) => void;
  }) => (
    <button
      type="button"
      onClick={() =>
        onChange(
          label === 'Player A'
            ? {
                id: 1001,
                player_name: 'Martin Ødegaard',
                first_name: 'Martin',
                last_name: 'Ødegaard',
                nationality: 'Norway',
                primary_position: 'AM',
                raw_position: 'AM',
                squad_number: 8,
                provider: 'football-data',
                external_player_id: 'ext-a',
                is_active: true,
                team: { id: 11, name: 'Arsenal' },
                canonical_player: { id: 21, display_name: 'Martin Ødegaard' },
              }
            : {
                id: 1002,
                player_name: 'Bruno Fernandes',
                first_name: 'Bruno',
                last_name: 'Fernandes',
                nationality: 'Portugal',
                primary_position: 'AM',
                raw_position: 'AM',
                squad_number: 8,
                provider: 'football-data',
                external_player_id: 'ext-b',
                is_active: true,
                team: { id: 22, name: 'Manchester United' },
                canonical_player: { id: 22, display_name: 'Bruno Fernandes' },
              }
        )
      }
    >
      {`Choose ${label}`}
    </button>
  ),
}));

describe('InternalPlayerComparisonPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    getPlayerOverviewComparisonMock.mockResolvedValue({
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

    fireEvent.click(screen.getByRole('button', { name: 'Choose Player A' }));
    fireEvent.click(screen.getByRole('button', { name: 'Choose Player B' }));
    fireEvent.click(screen.getByRole('button', { name: 'Compare Selected Players' }));

    await waitFor(() => {
      expect(getPlayerOverviewComparisonMock).toHaveBeenCalledWith(
        expect.objectContaining({
          player_a_id: 21,
          player_b_id: 22,
        })
      );
    });

    expect(await screen.findByText('Creative midfield comparison')).toBeInTheDocument();
    expect(screen.getByText('Player B produces more key passes.')).toBeInTheDocument();
    expect(screen.getByText('Chance Creation')).toBeInTheDocument();
  });
});