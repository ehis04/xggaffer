import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MyClubsPage from '../MyClubsPage';

const { mockNavigate, mockClubsApi, mockApiClient } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockClubsApi: {
    myClubs: vi.fn(),
    listMyJoinRequests: vi.fn(),
    listMyInvitations: vi.fn(),
    lookupByJoinCode: vi.fn(),
    requestToJoin: vi.fn(),
    withdrawJoinRequest: vi.fn(),
    acceptInvitation: vi.fn(),
    declineInvitation: vi.fn(),
  },
  mockApiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
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

vi.mock('../../../../services/api/client', () => ({
  default: mockApiClient,
}));

describe('MyClubsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockClubsApi.myClubs.mockResolvedValue([]);
    mockClubsApi.listMyJoinRequests.mockResolvedValue([
      {
        id: 501,
        club: 77,
        club_name: 'Request Club',
        user: 99,
        user_email: 'player@example.com',
        requested_role: 'player',
        message: 'Please let me in.',
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
    mockClubsApi.listMyInvitations.mockResolvedValue([
      {
        id: 601,
        club: 88,
        club_name: 'Invite Club',
        invited_user: 99,
        invited_user_email: 'player@example.com',
        invited_by: 7,
        invited_by_email: 'owner@example.com',
        invited_role: 'coach',
        note: 'Please join as coach.',
        status: 'pending',
        responded_at: null,
        response_note: '',
        created_at: '2026-04-03T10:00:00Z',
        updated_at: '2026-04-03T10:00:00Z',
      },
    ]);
    mockApiClient.get.mockResolvedValue([{ role: 'C' }]);
    mockApiClient.post.mockResolvedValue({ id: 1, role: 'C', role_display: 'Coach' });
    mockApiClient.put.mockResolvedValue({
      active_role: 'C',
      active_role_display: 'Coach',
      message: 'Active role updated',
    });
    mockClubsApi.withdrawJoinRequest.mockResolvedValue({});
    mockClubsApi.acceptInvitation.mockResolvedValue({});
    mockClubsApi.declineInvitation.mockResolvedValue({});
  });

  it('renders my requests and invitations state', async () => {
    render(
      <MemoryRouter>
        <MyClubsPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('My Join Requests')).toBeInTheDocument();
    expect(screen.getByText('Request Club')).toBeInTheDocument();
    expect(screen.getByText(/Pending review/i)).toBeInTheDocument();

    expect(screen.getByText('My Invitations')).toBeInTheDocument();
    expect(screen.getByText('Invite Club')).toBeInTheDocument();
    expect(screen.getByText(/Pending response/i)).toBeInTheDocument();
  });

  it('allows withdrawing a pending request', async () => {
    render(
      <MemoryRouter>
        <MyClubsPage />
      </MemoryRouter>
    );

    await screen.findByText('Request Club');

    fireEvent.click(screen.getByRole('button', { name: 'Withdraw' }));

    await waitFor(() => {
      expect(mockClubsApi.withdrawJoinRequest).toHaveBeenCalledWith(77, 501);
    });
  });

  it('allows responding to a pending invitation', async () => {
    render(
      <MemoryRouter>
        <MyClubsPage />
      </MemoryRouter>
    );

    await screen.findByText('Invite Club');

    fireEvent.click(screen.getByRole('button', { name: 'Accept' }));

    await waitFor(() => {
      expect(mockClubsApi.acceptInvitation).toHaveBeenCalledWith(88, 601);
    });
  });

  it('allows switching role to coach from clubs page', async () => {
    mockApiClient.get.mockResolvedValueOnce([{ role: 'P' }]);

    render(
      <MemoryRouter>
        <MyClubsPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/coach capability/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Switch Role to Coach' }));

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/users/profile/role/', { role: 'C' });
      expect(mockApiClient.put).toHaveBeenCalledWith('/users/profile/active-role/', { role: 'C' });
    });

    expect(await screen.findByText(/Role switched to Coach/i)).toBeInTheDocument();
  });
});