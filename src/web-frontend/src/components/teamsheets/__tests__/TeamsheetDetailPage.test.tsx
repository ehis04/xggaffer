import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TeamsheetDetailPage from '../../../pages/coaching/teamsheets/TeamsheetDetailPage';

vi.mock('../../../services/api/predictionsApi', () => ({
  chatQuery: vi.fn(),
}));

vi.mock('../../../services/api/teamsheetApi', () => ({
  teamsheetApi: {
    get: vi.fn(),
    duplicate: vi.fn(),
  },
  teamsheetPlayerApi: {
    bulkUpdatePositions: vi.fn(),
  },
}));

vi.mock('../../../context/useAuth', () => ({
  useAuth: () => ({ user: { id: 1 } }),
}));

vi.mock('../../../components/Navigation/SideBar', () => ({
  Sidebar: () => <aside data-testid="sidebar" />,
}));

vi.mock('../../../components/Social/SocialUserButtons', () => ({
  SocialUserButtons: () => <div data-testid="social-user-buttons" />,
}));

vi.mock('../../../components/teamsheets', () => ({
  Pitch: ({ players }: { players: { display_name: string }[] }) => (
    <div data-testid="pitch">
      {players.map((p) => (
        <span key={p.display_name}>{p.display_name}</span>
      ))}
    </div>
  ),
  TeamsheetHeader: ({ teamsheet }: { teamsheet: { title: string } }) => (
    <div data-testid="teamsheet-header">{teamsheet.title}</div>
  ),
  SubstitutesList: () => <div data-testid="substitutes-list" />,
  PlayerDetailPanel: () => <div data-testid="player-detail-panel" />,
}));

import { chatQuery } from '../../../services/api/predictionsApi';
import { teamsheetApi } from '../../../services/api/teamsheetApi';

const makeTeamsheet = (overrides = {}) => ({
  id: 1,
  title: 'Test Teamsheet',
  club: 4,
  club_name: 'Arsenal',
  created_by: null,
  created_by_username: null,
  formation: '4-3-3',
  formation_display: '4-3-3',
  match_date: null,
  opponent: '',
  notes: '',
  is_template: false,
  is_complete: true,
  starter_count: 11,
  substitute_count: 0,
  players: [
    {
      id: 1,
      slot_number: 1,
      is_substitute: false,
      club_player: null,
      club_player_name: null,
      custom_name: '',
      custom_number: null,
      display_name: 'John Smith',
      display_number: 1,
      display_photo_url: null,
      is_linked: false,
      position_label: 'GK',
      position_x: 50,
      position_y: 8,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

const makeChatResponse = (players: object[]) => ({
  data: {
    prose: 'Test prose',
    structured_data: {
      intent: 'AVAILABILITY_QUERY',
      entities: { home_team: null, away_team: null, team: 'Arsenal', player_name: null, league: null, season: null },
      engine_data: { players },
      partial: false,
      error: null,
      timestamp: '2026-01-01T00:00:00Z',
    },
    intent: 'AVAILABILITY_QUERY',
    entities: { home_team: null, away_team: null, team: 'Arsenal', player_name: null, league: null, season: null },
    used_fallback: false,
    query_type: 'AVAILABILITY_QUERY',
  },
});

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/clubs/4/teamsheets/1']}>
      <Routes>
        <Route path="/clubs/:clubId/teamsheets/:teamsheetId" element={<TeamsheetDetailPage />} />
      </Routes>
    </MemoryRouter>
  );

describe('TeamsheetDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing when chatQuery returns empty players', async () => {
    vi.mocked(teamsheetApi.get).mockResolvedValue(makeTeamsheet() as any);
    vi.mocked(chatQuery).mockResolvedValue(makeChatResponse([]) as any);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('teamsheet-header')).toBeInTheDocument();
    });
  });

  it('renders availability badge for matched player', async () => {
    vi.mocked(teamsheetApi.get).mockResolvedValue(makeTeamsheet() as any);
    vi.mocked(chatQuery).mockResolvedValue(
      makeChatResponse([{ player_name: 'John Smith', status: 'available' }]) as any
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Fit')).toBeInTheDocument();
    });
  });

  it('renders no badge for unmatched player', async () => {
    vi.mocked(teamsheetApi.get).mockResolvedValue(makeTeamsheet() as any);
    vi.mocked(chatQuery).mockResolvedValue(
      makeChatResponse([{ player_name: 'Unrelated Player', status: 'injured' }]) as any
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('John Smith').length).toBeGreaterThan(0);
    });
  });

  it('does not crash when chatQuery rejects', async () => {
    vi.mocked(teamsheetApi.get).mockResolvedValue(makeTeamsheet() as any);
    vi.mocked(chatQuery).mockRejectedValue(new Error('network error'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('teamsheet-header')).toBeInTheDocument();
    });

    expect(screen.queryByText('Fit')).not.toBeInTheDocument();
    expect(screen.queryByText('Out')).not.toBeInTheDocument();
  });

  it('preserves existing teamsheet content after availability loads', async () => {
    vi.mocked(teamsheetApi.get).mockResolvedValue(makeTeamsheet() as any);
    vi.mocked(chatQuery).mockResolvedValue(
      makeChatResponse([{ player_name: 'John Smith', status: 'risk_flagged' }]) as any
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Test Teamsheet')).toBeInTheDocument();
      expect(screen.getAllByText('John Smith').length).toBeGreaterThan(0);
      expect(screen.getByText('Doubt')).toBeInTheDocument();
    });

    expect(chatQuery).toHaveBeenCalledTimes(1);
    expect(chatQuery).toHaveBeenCalledWith(expect.stringContaining('John Smith'));
  });

  it('calls chatQuery with team name from teamsheet.club_name', async () => {
    vi.mocked(teamsheetApi.get).mockResolvedValue(makeTeamsheet() as any);
    vi.mocked(chatQuery).mockResolvedValue(makeChatResponse([]) as any);

    renderPage();

    await waitFor(() => {
      expect(chatQuery).toHaveBeenCalledWith('injury risk John Smith');
    });
  });
});
