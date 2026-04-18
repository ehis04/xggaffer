import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TeamsheetCreatePage from '../TeamsheetCreatePage';
import { teamsheetApi } from '../../../../services/api';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ clubId: '4' }),
  };
});

vi.mock('../../../../services/api', () => ({
  teamsheetApi: {
    getChoices: vi.fn(),
    getAvailablePlayers: vi.fn(),
    createWithPlayers: vi.fn(),
  },
}));

vi.mock('../../../../components/teamsheets', () => ({
  FormationPicker: ({ formations }: any) => (
    <div>Formation count: {formations.length}</div>
  ),
  PlayerSlotSelector: ({ slots, onSlotClick }: any) => (
    <div>
      {slots.map((slot: any) => (
        <button
          key={slot.slot_number}
          type="button"
          onClick={() => onSlotClick(slot.slot_number)}
        >
          Slot {slot.slot_number}
        </button>
      ))}
    </div>
  ),
  AvailablePlayersList: ({ players, loading }: any) => (
    <div>{loading ? 'Available list loading' : `Available list: ${players.length}`}</div>
  ),
}));

describe('TeamsheetCreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(teamsheetApi.getChoices).mockResolvedValue({
      positions: ['GK', 'CB', 'CM', 'ST'],
      formations_with_templates: [
        {
          value: '442',
          label: '4-4-2',
          positions: [
            { slot: 1, position: 'GK', x: 50, y: 8 },
            { slot: 2, position: 'CB', x: 35, y: 25 },
          ],
        },
      ],
    } as any);

    vi.mocked(teamsheetApi.getAvailablePlayers).mockResolvedValue([
      {
        id: 88,
        full_name: 'David Raya',
        display_name: 'David Raya',
        squad_number: 22,
        source_type: 'club_member',
        primary_position: 'GK',
      },
    ] as any);
  });

  it('renders the tiny selected-slot hook when a slot is chosen', async () => {
    render(
      <MemoryRouter>
        <TeamsheetCreatePage />
      </MemoryRouter>
    );

    expect(await screen.findByRole('heading', { name: 'Create Teamsheet' })).toBeInTheDocument();

    fireEvent.click(await screen.findByRole('button', { name: 'Slot 1' }));

    expect(await screen.findByText('Selected Slot')).toBeInTheDocument();
    expect(screen.getByText('GK · Starter')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/1 candidate available/i)).toBeInTheDocument();
    });
  });
});