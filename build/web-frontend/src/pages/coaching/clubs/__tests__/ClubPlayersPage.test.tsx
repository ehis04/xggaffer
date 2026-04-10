import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import ClubPlayersPage from '../ClubPlayersPage';

const { mockNavigate, mockClubsApi, mockPlayerdataApi } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockClubsApi: {
    get: vi.fn(),
    listPlayers: vi.fn(),
    listClubJoinRequests: vi.fn(),
    linkPlayer: vi.fn(),
    unlinkPlayer: vi.fn(),
    relinkPlayer: vi.fn(),
    createPlayer: vi.fn(),
    updatePlayer: vi.fn(),
    syncClubSquad: vi.fn(),
  },
  mockPlayerdataApi: {
    getPlayerSeasonSummary: vi.fn(),
  },
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useParams: () => ({ clubId: '42' }),
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
    canonicalPlayerIdSource,
    error,
    isLoading,
  }: {
    player?: { display_name?: string; full_name?: string } | null;
    canonicalPlayerId?: number | null;
    canonicalPlayerIdSource?: string | null;
    error?: string | null;
    isLoading?: boolean;
  }) => (
    <div data-testid="compact-player-preview">
      <div>Preview Player: {player?.display_name || player?.full_name || 'none'}</div>
      <div>Canonical ID: {canonicalPlayerId ?? 'none'}</div>
      <div>Canonical Source: {canonicalPlayerIdSource ?? 'none'}</div>
      <div>Preview Loading: {isLoading ? 'yes' : 'no'}</div>
      <div>Preview Error: {error || 'none'}</div>
    </div>
  ),
}));

const buildClub = () => ({
  id: 42,
  name: 'Phase C Test Club',
  description: 'Club for Phase C roster tests.',
  badge: null,
  creator: 7,
  creator_username: 'coach@example.com',
  visibility: 'private' as const,
  club_type: 'user_fictional' as const,
  fictional_basis: 'original' as const,
  source_real_club_name: '',
  directory_visibility: 'listed' as const,
  join_policy: 'approval_required' as const,
  join_code: null,
  verification_status: 'not_required' as const,
  city: 'Dublin',
  country: 'IE',
  stadium: '',
  division: '',
  achievements: '',
  member_count: 5,
  player_count: 2,
  latest_understat_summary: null,
  created_at: '2026-04-01T10:00:00Z',
  updated_at: '2026-04-01T10:00:00Z',
});

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
  club: {
    id: 42,
    name: 'Phase C Test Club',
    short_name: 'PCTC',
    crest_url: null,
  },
  context: {
    provider: 'understat',
    season: '2023',
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
  provider_coverage: {
    provider: 'understat',
    has_data: true,
    coverage_status: 'complete',
    freshness_label: 'current',
    source_updated_at: null,
    last_synced_at: null,
    matches_sampled: 20,
    minutes_sampled: 1600,
    coverage_notes: [],
  },
  has_summary_data: true,
  missing_reasons: [],
};

describe('ClubPlayersPage Phase C UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockClubsApi.get.mockResolvedValue(buildClub());
    mockClubsApi.listPlayers.mockResolvedValue([
      buildLinkedPlayer(),
      buildUnlinkedPlayer(),
    ]);
    mockClubsApi.createPlayer.mockResolvedValue(buildUnlinkedPlayer());
    mockClubsApi.updatePlayer.mockResolvedValue(buildUnlinkedPlayer());
    mockClubsApi.syncClubSquad.mockResolvedValue({
      club_id: 42,
      provider: 'football_data',
      status: 'success',
      records_processed: 2,
      records_created: 0,
      records_updated: 2,
      error_count: 0,
      players_created: 0,
      players_updated: 2,
      player_external_identities_created: 0,
      player_external_identities_updated: 0,
      club_players_created: 0,
      club_players_updated: 2,
      raw_error_summary: '',
      sync_job_id: 999,
    });
    mockPlayerdataApi.getPlayerSeasonSummary.mockResolvedValue(seasonSummary);
  });

  it('renders linked and unlinked roster state clearly', async () => {
    mockClubsApi.listClubJoinRequests.mockResolvedValue([]);

    render(<ClubPlayersPage />);

    expect(await screen.findByText('Players')).toBeInTheDocument();
    expect(await screen.findByText('Phase C Test Club')).toBeInTheDocument();

    expect(screen.getByText('Captain Erin')).toBeInTheDocument();
    expect(screen.getByText('Local Prospect')).toBeInTheDocument();

    expect(screen.getByText('Canonical linked')).toBeInTheDocument();
    expect(screen.getAllByText('Local-only').length).toBeGreaterThan(0);
    expect(screen.getAllByText('No canonical player linked yet').length).toBeGreaterThan(0);
  });

  it('shows authorised alignment controls for reviewer-capable users', async () => {
    mockClubsApi.listClubJoinRequests.mockResolvedValue([]);

    render(<ClubPlayersPage />);

    const previewButtons = await screen.findAllByRole('button', { name: 'Preview' });
    fireEvent.click(previewButtons[0]);

    expect(await screen.findByText('Canonical Alignment')).toBeInTheDocument();
    expect(
      screen.getByText('This phase uses an explicit canonical player ID input. No auto-match or heuristic suggestion flow is shown here.')
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Canonical Player ID')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Relink' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Unlink' })).toBeInTheDocument();
  });

  it('hides alignment actions from unauthorised users while still showing state', async () => {
    mockClubsApi.listClubJoinRequests.mockRejectedValue(new Error('Forbidden'));

    render(<ClubPlayersPage />);

    const previewButtons = await screen.findAllByRole('button', { name: 'Preview' });
    fireEvent.click(previewButtons[0]);

    expect(await screen.findByText('Canonical Alignment')).toBeInTheDocument();
    expect(
      screen.getByText('You can view alignment state here, but only authorised club reviewers can change canonical links.')
    ).toBeInTheDocument();

    expect(screen.queryByLabelText('Canonical Player ID')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Relink' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Unlink' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Link Canonical Player' })).not.toBeInTheDocument();
  });

  it('renders link action for an unlinked player and calls the explicit link endpoint', async () => {
    mockClubsApi.listClubJoinRequests.mockResolvedValue([]);
    mockClubsApi.linkPlayer.mockResolvedValue({
      ...buildUnlinkedPlayer(),
      player_id: 202,
      canonical_player_id: 202,
      is_linked_to_player: true,
      canonical_display_name: 'Linked Canonical Player',
      canonical_primary_position: 'RW',
    });

    render(<ClubPlayersPage />);

    const previewButtons = await screen.findAllByRole('button', { name: 'Preview' });
    fireEvent.click(previewButtons[1]);

    expect(await screen.findByText('Canonical Alignment')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Link Canonical Player' })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Canonical Player ID'), {
      target: { value: '202' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Link Canonical Player' }));

    await waitFor(() => {
      expect(mockClubsApi.linkPlayer).toHaveBeenCalledWith(42, 2, {
        canonical_player_id: 202,
      });
    });
  });

  it('calls explicit relink and unlink endpoints for a linked player', async () => {
    mockClubsApi.listClubJoinRequests.mockResolvedValue([]);
    mockClubsApi.relinkPlayer.mockResolvedValue({
      ...buildLinkedPlayer(),
      player_id: 303,
      canonical_player_id: 303,
      canonical_display_name: 'Replacement Player',
      canonical_primary_position: 'CM',
    });
    mockClubsApi.unlinkPlayer.mockResolvedValue({
      ...buildLinkedPlayer(),
      player: null,
      player_id: null,
      is_linked_to_player: false,
      canonical_player_id: null,
      canonical_display_name: null,
      canonical_primary_position: null,
    });

    render(<ClubPlayersPage />);

    const previewButtons = await screen.findAllByRole('button', { name: 'Preview' });
    fireEvent.click(previewButtons[0]);

    expect(await screen.findByText('Canonical Alignment')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Canonical Player ID'), {
      target: { value: '303' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Relink' }));

    await waitFor(() => {
      expect(mockClubsApi.relinkPlayer).toHaveBeenCalledWith(42, 1, {
        canonical_player_id: 303,
      });
    });

    fireEvent.click(screen.getByRole('button', { name: 'Unlink' }));

    await waitFor(() => {
      expect(mockClubsApi.unlinkPlayer).toHaveBeenCalledWith(42, 1);
    });
  });
});