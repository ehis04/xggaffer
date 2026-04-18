import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import IndividualClubBase from '../IndividualClubBase';

const { mockNavigate, mockClubsApi } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockClubsApi: {
    get: vi.fn(),
    myClubs: vi.fn(),
    listMyJoinRequests: vi.fn(),
    listClubJoinRequests: vi.fn(),
    listClubInvitations: vi.fn(),
    listPlayers: vi.fn(),
    approveJoinRequest: vi.fn(),
    rejectJoinRequest: vi.fn(),
    createInvitation: vi.fn(),
    revokeInvitation: vi.fn(),
    requestToJoin: vi.fn(),
  },
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ clubId: '1' }),
  };
});

vi.mock('../../../../services/api', () => ({
  clubsApi: mockClubsApi,
}));

const club = {
  id: 1,
  name: 'Reviewer Club',
  description: 'Reviewer workflow test club.',
  badge: null,
  creator: 10,
  creator_username: 'owner@example.com',
  visibility: 'private',
  club_type: 'user_fictional',
  fictional_basis: 'original',
  source_real_club_name: '',
  directory_visibility: 'listed',
  join_policy: 'approval_required',
  join_code: null,
  verification_status: 'not_required',
  city: 'Dublin',
  country: 'IE',
  stadium: '',
  division: 'Premier',
  achievements: '',
  member_count: 4,
  player_count: 20,
  created_at: '2026-04-03T10:00:00Z',
  updated_at: '2026-04-03T10:00:00Z',
};

describe('IndividualClubBase', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockClubsApi.get.mockResolvedValue(club);
    mockClubsApi.myClubs.mockResolvedValue([club]);
    mockClubsApi.listMyJoinRequests.mockResolvedValue([]);
    mockClubsApi.listClubJoinRequests.mockResolvedValue([
      {
        id: 201,
        club: 1,
        club_name: 'Reviewer Club',
        user: 42,
        user_email: 'player@example.com',
        requested_role: 'player',
        message: 'Can I join?',
        status: 'pending',
        reviewed_by: null,
        reviewed_by_email: null,
        reviewed_at: null,
        review_note: '',
        selected_club_player: null,
        selected_club_player_name: null,
        created_at: '2026-04-03T10:00:00Z',
        updated_at: '2026-04-03T10:00:00Z',
      },
    ]);
    mockClubsApi.listClubInvitations.mockResolvedValue([
      {
        id: 301,
        club: 1,
        club_name: 'Reviewer Club',
        invited_user: 55,
        invited_user_email: 'invitee@example.com',
        invited_by: 10,
        invited_by_email: 'owner@example.com',
        invited_role: 'coach',
        note: 'Please join the staff.',
        status: 'pending',
        responded_at: null,
        response_note: '',
        created_at: '2026-04-03T10:00:00Z',
        updated_at: '2026-04-03T10:00:00Z',
      },
    ]);
    mockClubsApi.listPlayers.mockResolvedValue([
      {
        id: 31,
        club: 1,
        club_name: 'Reviewer Club',
        player: null,
        player_id: null,
        user: null,
        first_name: 'Jamie',
        last_name: 'Byrne',
        full_name: 'Jamie Byrne',
        display_name: 'Jamie Byrne',
        squad_number: 9,
        primary_position: 'ST',
        secondary_positions: [],
        preferred_foot: 'R',
        date_of_birth: null,
        nationality: 'IE',
        height_cm: 180,
        photo: null,
        is_active: true,
        is_claimed: false,
        is_public: false,
        created_at: '2026-04-03T10:00:00Z',
        updated_at: '2026-04-03T10:00:00Z',
      },
    ]);
    mockClubsApi.approveJoinRequest.mockResolvedValue({});
    mockClubsApi.rejectJoinRequest.mockResolvedValue({});
    mockClubsApi.createInvitation.mockResolvedValue({});
    mockClubsApi.revokeInvitation.mockResolvedValue({});
  });

  it('renders reviewer workflow actions', async () => {
    render(
      <MemoryRouter>
        <IndividualClubBase />
      </MemoryRouter>
    );

    expect(await screen.findByText('Pending Join Requests')).toBeInTheDocument();
    expect(screen.getByText('Invitations')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send Invitation' })).toBeInTheDocument();
  });

  it('passes the selected ClubPlayer when approving a request', async () => {
    render(
      <MemoryRouter>
        <IndividualClubBase />
      </MemoryRouter>
    );

    await screen.findByText('Pending Join Requests');

    fireEvent.change(screen.getByLabelText('Optional roster link'), {
      target: { value: '31' },
    });

    fireEvent.change(screen.getByLabelText('Review note'), {
      target: { value: 'Ready for approval.' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));

    await waitFor(() => {
      expect(mockClubsApi.approveJoinRequest).toHaveBeenCalledWith(1, 201, {
        review_note: 'Ready for approval.',
        selected_club_player: 31,
      });
    });
  });
});