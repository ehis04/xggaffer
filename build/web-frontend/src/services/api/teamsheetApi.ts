import apiClient from './client';
import type {
  Teamsheet,
  TeamsheetListItem,
  TeamsheetChoices,
  BulkPositionUpdate,
  TeamsheetPlayer,
  AvailablePlayer,
  CreateTeamsheetPayload,
} from '../../types/teamsheet';

export const teamsheetApi = {
  list: (clubId: number) =>
    apiClient.get<TeamsheetListItem[]>(`/clubs/${clubId}/teamsheets/`),

  get: (clubId: number, teamsheetId: number) =>
    apiClient.get<Teamsheet>(`/clubs/${clubId}/teamsheets/${teamsheetId}/`),

  create: (clubId: number, data: Partial<Teamsheet>) =>
    apiClient.post<Teamsheet>(`/clubs/${clubId}/teamsheets/`, data),

  createWithPlayers: (clubId: number, data: CreateTeamsheetPayload) =>
    apiClient.post<Teamsheet>(`/clubs/${clubId}/teamsheets/create_with_players/`, data),

  update: (clubId: number, teamsheetId: number, data: Partial<Teamsheet>) =>
    apiClient.patch<Teamsheet>(`/clubs/${clubId}/teamsheets/${teamsheetId}/`, data),

  delete: (clubId: number, teamsheetId: number) =>
    apiClient.delete(`/clubs/${clubId}/teamsheets/${teamsheetId}/`),

  getChoices: (clubId: number) =>
    apiClient.get<TeamsheetChoices>(`/clubs/${clubId}/teamsheets/choices/`),

  duplicate: (clubId: number, teamsheetId: number, newTitle: string, includePlayers = true) =>
    apiClient.post<Teamsheet>(`/clubs/${clubId}/teamsheets/${teamsheetId}/duplicate/`, {
      new_title: newTitle,
      include_players: includePlayers,
    }),

  resetToFormation: (clubId: number, teamsheetId: number) =>
    apiClient.post<Teamsheet>(`/clubs/${clubId}/teamsheets/${teamsheetId}/reset_to_formation/`),

  getAvailablePlayers: (
    clubId: number,
    options?: { position?: string; search?: string; exclude?: number[] }
  ) => {
    const params: Record<string, string> = {};

    if (options?.position) params.position = options.position;
    if (options?.search) params.search = options.search;
    if (options?.exclude?.length) params.exclude = options.exclude.join(',');

    return apiClient.get<AvailablePlayer[]>(
      `/clubs/${clubId}/teamsheets/available_players/`,
      Object.keys(params).length > 0 ? params : undefined
    );
  },
};

export const teamsheetPlayerApi = {
  list: (clubId: number, teamsheetId: number) =>
    apiClient.get<TeamsheetPlayer[]>(`/clubs/${clubId}/teamsheets/${teamsheetId}/players/`),

  get: (clubId: number, teamsheetId: number, playerId: number) =>
    apiClient.get<TeamsheetPlayer>(`/clubs/${clubId}/teamsheets/${teamsheetId}/players/${playerId}/`),

  updatePosition: (
    clubId: number,
    teamsheetId: number,
    playerId: number,
    x: number,
    y: number,
    label?: string
  ) =>
    apiClient.patch<TeamsheetPlayer>(
      `/clubs/${clubId}/teamsheets/${teamsheetId}/players/${playerId}/update_position/`,
      { position_x: x, position_y: y, ...(label && { position_label: label }) }
    ),

  bulkUpdatePositions: (clubId: number, teamsheetId: number, updates: BulkPositionUpdate) =>
    apiClient.post<{ updated_count: number; players: TeamsheetPlayer[] }>(
      `/clubs/${clubId}/teamsheets/${teamsheetId}/players/bulk_update_positions/`,
      updates
    ),

  assignPlayer: (clubId: number, teamsheetId: number, slotId: number, clubPlayerId: number | null) =>
    apiClient.post<TeamsheetPlayer>(
      `/clubs/${clubId}/teamsheets/${teamsheetId}/players/${slotId}/assign_player/`,
      { club_player_id: clubPlayerId }
    ),

  swapPositions: (clubId: number, teamsheetId: number, playerId: number, targetPlayerId: number) =>
    apiClient.post<{ swapped: TeamsheetPlayer[] }>(
      `/clubs/${clubId}/teamsheets/${teamsheetId}/players/${playerId}/swap_positions/`,
      { target_player_id: targetPlayerId }
    ),
};

export default teamsheetApi;