import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PlayersTab from '../tabs/PlayersTab';

const { mockNavigate, mockClubsApi, mockPlayerdataApi } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockClubsApi: {
    listPlayers: vi.fn(),
    createPlayer: vi.fn(),
    updatePlayer: vi.fn(),
    syncClubSquad: vi.fn(),
    manualStats: {
      list: vi.fn(),
    },
    injuries: {
      list: vi.fn(),
      resolve: vi.fn(),
    },
  },
  mockPlayerdataApi: {
    getPlayerSeasonSummary: vi.fn(),
  },
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('../../../../services/api', () => ({
  clubsApi: mockClubsApi,
}));

vi.mock('../../../../services/api/playerdataApi', () => ({
  playerdataApi: mockPlayerdataApi,
}));

vi.mock('../../../../components/playerdata/CompactPlayerPreview', () => ({
  default: ({
    player,
    canonicalPlayerId,
    error,
    isLoading,
  }: {
    player?: { display_name?: string; full_name?: string } | null;
    canonicalPlayerId?: number | null;
    error?: string | null;
    isLoading?: boolean;
  }) => (
    <div data-testid="compact-player-preview">
      <div>Preview Player: {player?.display_name || player?.full_name || 'none'}</div>
      <div>Canonical ID: {canonicalPlayerId ?? 'none'}</div>
      <div>Preview Loading: {isLoading ? 'yes' : 'no'}</div>
      <div>Preview Error: {error || 'none'}</div>
    </div>
  ),
}));

vi.mock('../../../../components/Clubs/ManualStatsPanel', () => ({
  ManualStatsPanel: ({ player, canManage }: { player: { display_name: string }; canManage: boolean }) => (
    <div data-testid="manual-stats-panel">
      Manual stats for {player.display_name} · {canManage ? 'can manage' : 'view only'}
    </div>
  ),
}));

vi.mock('../../../../components/Clubs/InjuryModal', () => ({
  InjuryModal: () => <div data-testid="injury-modal" />,
}));

const buildLinkedPlayer = () => ({
  id: 1,
  club: 42,
  club_name: 'Phase C Test Club',
  player: 101,
  player_id: 101,
  user: null,
  first_name: 'Erin',
  last_name: 'Moore',
  full_name: 'Erin Moore',
  display_name: 'Captain Erin',
  squad_number: 8,
  primary_position: 'CM',
  secondary_positions: ['CAM'],
  preferred_foot: 'r',
  date_of_birth: '2000-01-01',
  nationality: 'IE',
  height_cm: 168,
  photo: null,
  profile_image: null,
  is_active: true,
  is_claimed: false,
  is_public: false,
  is_linked_to_player: true,
  canonical_player_id: 101,
  canonical_display_name: 'Erin Moore',
  canonical_primary_position: 'CM',
  has_provider_identity: true,
  provider_sources: ['understat'],
  last_synced_at: '2026-04-03T12:00:00Z',
  availability_status: 'AV',
  created_at: '2026-04-01T10:00:00Z',
  updated_at: '2026-04-03T12:00:00Z',
});

const buildUnlinkedPlayer = () => ({
  id: 2,
  club: 42,
  club_name: 'Phase C Test Club',
  player: null,
  player_id: null,
  user: null,
  first_name: 'Local',
  last_name: 'Prospect',
  full_name: 'Local Prospect',
  display_name: 'Local Prospect',
  squad_number: 14,
  primary_position: 'RW',
  secondary_positions: [],
  preferred_foot: 'l',
  date_of_birth: null,
  nationality: '',
  height_cm: null,
  photo: null,
  profile_image: null,
  is_active: true,
  is_claimed: false,
  is_public: false,
  is_linked_to_player: false,
  canonical_player_id: null,
  canonical_display_name: null,
  canonical_primary_position: null,
  has_provider_identity: false,
  provider_sources: [],
  last_synced_at: null,
  availability_status: 'AV',
  created_at: '2026-04-01T10:00:00Z',
  updated_at: '2026-04-01T10:00:00Z',
});

const seasonSummary = {
  player: {
    id: 101,
    full_name: 'Erin Moore',
    display_name: 'Erin Moore',
    short_name: 'E. Moore',
    position: 'CM',
    nationality: 'IE',
    age: 25,
    photo_url: null,
  },
  club: null,
  context: {
    provider: 'understat',
    season: '2025',
    competition_code: 'EPL',
    competition_name: 'Premier League',
  },
  metrics: [],
  explanation: {
    headline: 'Strong midfield profile',
    summary: 'Consistent ball progression output.',
    strengths: [],
    watchouts: [],
    notes: [],
  },
  provider_coverage: null,
  has_summary_data: true,
  missing_reasons: [],
};

const renderPlayersTab = (canManage = true) =>
  render(
    <PlayersTab
      ctx={{
        clubId: 42,
        club: null,
        canManage,
        isCreator: canManage,
        membership: null,
        refreshClub: vi.fn(),
      }}
    />
  );

describe('ClubPlayersPage Phase C UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockClubsApi.listPlayers.mockResolvedValue([
      buildLinkedPlayer(),
      buildUnlinkedPlayer(),
    ]);
    mockClubsApi.createPlayer.mockResolvedValue(buildUnlinkedPlayer());
    mockClubsApi.updatePlayer.mockResolvedValue(buildUnlinkedPlayer());
    mockClubsApi.syncClubSquad.mockResolvedValue({
      players_created: 0,
      players_updated: 2,
    });
    mockClubsApi.manualStats.list.mockResolvedValue([]);
    mockClubsApi.injuries.list.mockResolvedValue([]);
    mockPlayerdataApi.getPlayerSeasonSummary.mockResolvedValue(seasonSummary);
  });

  it('renders linked and unlinked roster state clearly', async () => {
    renderPlayersTab();

    expect(await screen.findByText('Roster')).toBeInTheDocument();
    expect(screen.getByText('Captain Erin')).toBeInTheDocument();
    expect(screen.getByText('Local Prospect')).toBeInTheDocument();
    expect(screen.getByText(/2 players .* 1 linked/i)).toBeInTheDocument();
    expect(screen.getByText(/CM .* #8 .* Linked/i)).toBeInTheDocument();
    expect(screen.getByText(/RW .* #14 .* Local/i)).toBeInTheDocument();
  });

  it('opens selected player details with canonical preview and manual stats', async () => {
    renderPlayersTab();

    fireEvent.click(await screen.findByText('Captain Erin'));

    expect(await screen.findByTestId('compact-player-preview')).toBeInTheDocument();
    expect(screen.getByText('Preview Player: Captain Erin')).toBeInTheDocument();
    expect(screen.getByText('Canonical ID: 101')).toBeInTheDocument();
    expect(screen.getByTestId('manual-stats-panel')).toHaveTextContent('can manage');

    await waitFor(() => {
      expect(mockPlayerdataApi.getPlayerSeasonSummary).toHaveBeenCalledWith(
        101,
        expect.objectContaining({ provider: 'understat' })
      );
    });
  });

  it('hides management controls from users without manage permission', async () => {
    renderPlayersTab(false);

    expect(await screen.findByText('Roster')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Sync squad' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '+ Add player' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Captain Erin'));
    expect(await screen.findByTestId('manual-stats-panel')).toHaveTextContent('view only');
  });
});
