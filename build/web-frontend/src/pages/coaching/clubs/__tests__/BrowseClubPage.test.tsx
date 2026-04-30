import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BrowseClubsPage from '../BrowseClubPage';

const { mockNavigate, mockClubsApi } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockClubsApi: {
    browse: vi.fn(),
    listMyJoinRequests: vi.fn(),
    requestToJoin: vi.fn(),
    duplicate: vi.fn(),
  },
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../../../services/api', () => ({
  clubsApi: mockClubsApi,
}));

vi.mock('../../../../components/Navigation/SideBar', () => ({
  Sidebar: () => <aside data-testid="sidebar" />,
}));

vi.mock('../../../../components/Social/SocialUserButtons', () => ({
  SocialUserButtons: () => <div data-testid="social-user-buttons" />,
}));

const approvalClub = {
  id: 1,
  name: 'Approval Club',
  description: 'Requires approval.',
  badge: null,
  creator: 10,
  creator_username: 'owner@example.com',
  visibility: 'public',
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
  division: 'Division One',
  achievements: '',
  member_count: 2,
  player_count: 16,
  created_at: '2026-04-03T10:00:00Z',
  updated_at: '2026-04-03T10:00:00Z',
};

const inviteOnlyClub = {
  ...approvalClub,
  id: 2,
  name: 'Invite Club',
  join_policy: 'invite_only',
};

describe('BrowseClubsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a real request action for approval-required clubs', async () => {
    mockClubsApi.browse.mockResolvedValue([approvalClub]);
    mockClubsApi.listMyJoinRequests.mockResolvedValue([]);
    mockClubsApi.requestToJoin.mockResolvedValue({
      id: 101,
      club: approvalClub.id,
      club_name: approvalClub.name,
      user: 99,
      user_email: 'player@example.com',
      requested_role: 'player',
      message: '',
      status: 'pending',
      reviewed_by: null,
      reviewed_by_email: null,
      reviewed_at: null,
      review_note: '',
      selected_club_player: null,
      selected_club_player_name: null,
      created_at: '2026-04-03T10:00:00Z',
      updated_at: '2026-04-03T10:00:00Z',
    });

    render(
      <MemoryRouter>
        <BrowseClubsPage />
      </MemoryRouter>
    );

    await screen.findByText('Approval Club');

    fireEvent.click(screen.getByText('Approval Club'));

    const requestButton = await screen.findByRole('button', { name: 'Request to Join' });
    fireEvent.click(requestButton);

    await waitFor(() => {
      expect(mockClubsApi.requestToJoin).toHaveBeenCalledWith(approvalClub.id, {
        requested_role: 'player',
        message: undefined,
      });
    });

    expect(await screen.findByText('Join request submitted successfully.')).toBeInTheDocument();
  });

  it('shows honest invite-only messaging instead of a fake request button', async () => {
    mockClubsApi.browse.mockResolvedValue([inviteOnlyClub]);
    mockClubsApi.listMyJoinRequests.mockResolvedValue([]);

    render(
      <MemoryRouter>
        <BrowseClubsPage />
      </MemoryRouter>
    );

    await screen.findByText('Invite Club');

    fireEvent.click(screen.getByText('Invite Club'));

    expect(
      await screen.findByText(
        'This club is invite only. No self-service request flow is available from browse.'
      )
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Request to Join' })).not.toBeInTheDocument();
  });
});
