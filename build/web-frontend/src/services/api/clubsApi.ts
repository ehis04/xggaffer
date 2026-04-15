import apiClient from './client';
import type {
  Club,
  ClubInvitation,
  ClubJoinRequest,
  ClubListParams,
  ClubListScope,
  ClubUnderstatSeasonSummaryResponse,
  CreateClubPayload,
  DuplicateClubPayload,
  LookupClubByCodeResponse,
  CreateClubJoinRequestPayload,
  ApproveClubJoinRequestPayload,
  RejectClubJoinRequestPayload,
  WithdrawClubJoinRequestPayload,
  CreateClubInvitationPayload,
  AcceptClubInvitationPayload,
  DeclineClubInvitationPayload,
  RevokeClubInvitationPayload,
  ClubEvent,
  Fixture,
  ClubCalendarFeedItem,
  ClubCalendarFeedParams,
  CreateClubEventPayload,
  UpdateClubEventPayload,
  CreateFixturePayload,
  UpdateFixturePayload,
  ClubResource,
  ClubResourceEngagement,
  ClubResourceHeartbeatPayload,
  ClubResourceMyStatus,
  ClubResourceSignedAccessResponse,
  ClubResourceViewSummary,
  UploadClubResourcePayload,
  UpdateClubResourcePayload,
  ArchiveClubResourcePayload,
  ClubImportJob,
  ClubImportJobListItem,
  CreateClubImportJobPayload,
  CommitClubImportJobPayload,
  TrashListParams,
  TrashListItem,
} from '../../types/club';
import type {
  ClubPlayer,
  ClubPlayerListItem,
  CreateClubPlayerPayload,
  UpdateClubPlayerPayload,
  LinkClubPlayerPayload,
  UnlinkClubPlayerPayload,
  RelinkClubPlayerPayload,
} from '../../types/clubPlayers';

type ListResponse<T> = T[] | { results: T[] };

export interface SyncClubSquadPayload {
  provider?: string;
  provider_team_id?: string;
}

export interface SyncClubSquadResponse {
  club_id: number;
  provider: string;
  status: string;
  records_processed: number;
  records_created: number;
  records_updated: number;
  error_count: number;
  players_created: number;
  players_updated: number;
  player_external_identities_created: number;
  player_external_identities_updated: number;
  club_players_created: number;
  club_players_updated: number;
  raw_error_summary: string;
  sync_job_id: number;
}

export interface ClubUnderstatSeasonSummaryEmptyResponse {
  club_id: number;
  provider: 'understat';
  summary: null;
}

const unwrapListResponse = <T>(response: ListResponse<T>): T[] => {
  return Array.isArray(response) ? response : response.results;
};

const buildClubListParams = (
  scopeOrParams?: ClubListScope | ClubListParams
): Record<string, string> | undefined => {
  if (!scopeOrParams) {
    return undefined;
  }

  if (typeof scopeOrParams === 'string') {
    return { scope: scopeOrParams };
  }

  const params: Record<string, string> = {};

  if (scopeOrParams.scope) {
    params.scope = scopeOrParams.scope;
  }

  if (scopeOrParams.search?.trim()) {
    params.search = scopeOrParams.search.trim();
  }

  return Object.keys(params).length > 0 ? params : undefined;
};

export const clubsApi = {
  list: async (scopeOrParams?: ClubListScope | ClubListParams) => {
    const params = buildClubListParams(scopeOrParams);

    const response = await apiClient.get<ListResponse<Club>>(
      '/clubs/',
      params
    );

    return unwrapListResponse(response);
  },

  browse: async (params?: Omit<ClubListParams, 'scope'>) => {
    return clubsApi.list({
      scope: 'browse',
      ...(params ?? {}),
    });
  },

  myClubs: async (params?: Omit<ClubListParams, 'scope'>) => {
    return clubsApi.list({
      scope: 'mine',
      ...(params ?? {}),
    });
  },

  lookupByJoinCode: (code: string) =>
    apiClient.get<LookupClubByCodeResponse>('/clubs/lookup-by-code/', {
      code: code.trim(),
    }),

  get: (clubId: number, params?: { trash?: 'only' | 'include' }) =>
    apiClient.get<Club>(`/clubs/${clubId}/`, params),

  getUnderstatSeasonSummary: (
    clubId: number,
    params?: {
      season?: string;
      competition_code?: string;
    }
  ) =>
    apiClient.get<
      ClubUnderstatSeasonSummaryResponse | ClubUnderstatSeasonSummaryEmptyResponse
    >(`/clubs/${clubId}/understat_season_summary/`, params),

  create: (payload: CreateClubPayload) =>
    apiClient.post<Club>('/clubs/', payload),

  duplicate: (clubId: number, payload: DuplicateClubPayload = {}) =>
    apiClient.post<Club>(`/clubs/${clubId}/duplicate/`, payload),

  trash: (clubId: number) =>
    apiClient.post<Club>(`/clubs/${clubId}/trash/`, {}),

  restore: (clubId: number) =>
    apiClient.post<Club>(`/clubs/${clubId}/restore/`, {}),

  permanentDelete: (clubId: number) =>
    apiClient.delete<void>(`/clubs/${clubId}/permanent-delete/`),

  listTrashItems: (params?: TrashListParams) =>
    apiClient.get<TrashListItem[]>('/clubs/trash/', params as Record<string, string | number | boolean> | undefined),

  listPlayers: async (clubId: number) => {
    const response = await apiClient.get<ListResponse<ClubPlayerListItem>>(
      `/clubs/${clubId}/players/`
    );
    return unwrapListResponse(response);
  },

  getPlayer: (clubId: number, clubPlayerId: number) =>
    apiClient.get<ClubPlayer>(`/clubs/${clubId}/players/${clubPlayerId}/`),

  createPlayer: (clubId: number, payload: CreateClubPlayerPayload) =>
    apiClient.post<ClubPlayer>(`/clubs/${clubId}/players/`, payload),

  updatePlayer: (clubId: number, clubPlayerId: number, payload: UpdateClubPlayerPayload) =>
    apiClient.patch<ClubPlayer>(`/clubs/${clubId}/players/${clubPlayerId}/`, payload),

  linkPlayer: (
    clubId: number,
    clubPlayerId: number,
    payload: LinkClubPlayerPayload
  ) =>
    apiClient.post<ClubPlayer>(`/clubs/${clubId}/players/${clubPlayerId}/link/`, payload),

  unlinkPlayer: (
    clubId: number,
    clubPlayerId: number,
    payload: UnlinkClubPlayerPayload = {}
  ) =>
    apiClient.post<ClubPlayer>(`/clubs/${clubId}/players/${clubPlayerId}/unlink/`, payload),

  relinkPlayer: (
    clubId: number,
    clubPlayerId: number,
    payload: RelinkClubPlayerPayload
  ) =>
    apiClient.post<ClubPlayer>(`/clubs/${clubId}/players/${clubPlayerId}/relink/`, payload),

  syncClubSquad: (
    clubId: number,
    payload: SyncClubSquadPayload = {}
  ) =>
    apiClient.post<SyncClubSquadResponse>(`/clubs/${clubId}/sync_squad/`, payload),

  requestToJoin: (
    clubId: number,
    payload: CreateClubJoinRequestPayload = {}
  ) =>
    apiClient.post<ClubJoinRequest>(`/clubs/${clubId}/join-requests/`, payload),

  listMyJoinRequests: async () => {
    const response = await apiClient.get<ListResponse<ClubJoinRequest>>(
      '/clubs/my-join-requests/'
    );
    return unwrapListResponse(response);
  },

  listClubJoinRequests: async (clubId: number) => {
    const response = await apiClient.get<ListResponse<ClubJoinRequest>>(
      `/clubs/${clubId}/join-requests/`
    );
    return unwrapListResponse(response);
  },

  approveJoinRequest: (
    clubId: number,
    joinRequestId: number,
    payload: ApproveClubJoinRequestPayload = {}
  ) =>
    apiClient.post<ClubJoinRequest>(
      `/clubs/${clubId}/join-requests/${joinRequestId}/approve/`,
      payload
    ),

  rejectJoinRequest: (
    clubId: number,
    joinRequestId: number,
    payload: RejectClubJoinRequestPayload = {}
  ) =>
    apiClient.post<ClubJoinRequest>(
      `/clubs/${clubId}/join-requests/${joinRequestId}/reject/`,
      payload
    ),

  withdrawJoinRequest: (
    clubId: number,
    joinRequestId: number,
    payload: WithdrawClubJoinRequestPayload = {}
  ) =>
    apiClient.post<ClubJoinRequest>(
      `/clubs/${clubId}/join-requests/${joinRequestId}/withdraw/`,
      payload
    ),

  createInvitation: (
    clubId: number,
    payload: CreateClubInvitationPayload
  ) =>
    apiClient.post<ClubInvitation>(`/clubs/${clubId}/invitations/`, payload),

  listMyInvitations: async () => {
    const response = await apiClient.get<ListResponse<ClubInvitation>>(
      '/clubs/my-invitations/'
    );
    return unwrapListResponse(response);
  },

  listClubInvitations: async (clubId: number) => {
    const response = await apiClient.get<ListResponse<ClubInvitation>>(
      `/clubs/${clubId}/invitations/`
    );
    return unwrapListResponse(response);
  },

  listEvents: async (clubId: number) => {
    const response = await apiClient.get<ListResponse<ClubEvent>>(
      `/clubs/${clubId}/events/`
    );
    return unwrapListResponse(response);
  },

  getEvent: (clubId: number, eventId: number) =>
    apiClient.get<ClubEvent>(`/clubs/${clubId}/events/${eventId}/`),

  createEvent: (clubId: number, payload: CreateClubEventPayload) =>
    apiClient.post<ClubEvent>(`/clubs/${clubId}/events/`, payload),

  updateEvent: (
    clubId: number,
    eventId: number,
    payload: UpdateClubEventPayload
  ) =>
    apiClient.patch<ClubEvent>(`/clubs/${clubId}/events/${eventId}/`, payload),

  deleteEvent: (clubId: number, eventId: number) =>
    apiClient.delete<void>(`/clubs/${clubId}/events/${eventId}/`),

  listFixtures: async (clubId: number) => {
    const response = await apiClient.get<ListResponse<Fixture>>(
      `/clubs/${clubId}/fixtures/`
    );
    return unwrapListResponse(response);
  },

  getFixture: (clubId: number, fixtureId: number) =>
    apiClient.get<Fixture>(`/clubs/${clubId}/fixtures/${fixtureId}/`),

  createFixture: (clubId: number, payload: CreateFixturePayload) =>
    apiClient.post<Fixture>(`/clubs/${clubId}/fixtures/`, payload),

  updateFixture: (
    clubId: number,
    fixtureId: number,
    payload: UpdateFixturePayload
  ) =>
    apiClient.patch<Fixture>(`/clubs/${clubId}/fixtures/${fixtureId}/`, payload),

  deleteFixture: (clubId: number, fixtureId: number) =>
    apiClient.delete<void>(`/clubs/${clubId}/fixtures/${fixtureId}/`),

  listCalendarFeed: async (
    clubId: number,
    params?: ClubCalendarFeedParams
  ) => {
    const requestParams: Record<string, string> = {};

    if (typeof params?.include_past === 'boolean') {
      requestParams.include_past = String(params.include_past);
    }

    if (typeof params?.limit === 'number') {
      requestParams.limit = String(params.limit);
    }

    const response = await apiClient.get<ListResponse<ClubCalendarFeedItem>>(
      `/clubs/${clubId}/calendar/`,
      Object.keys(requestParams).length > 0 ? requestParams : undefined
    );



    return unwrapListResponse(response);
  },

  acceptInvitation: (
    clubId: number,
    invitationId: number,
    payload: AcceptClubInvitationPayload = {}
  ) =>
    apiClient.post<ClubInvitation>(
      `/clubs/${clubId}/invitations/${invitationId}/accept/`,
      payload
    ),

  declineInvitation: (
    clubId: number,
    invitationId: number,
    payload: DeclineClubInvitationPayload = {}
  ) =>
    apiClient.post<ClubInvitation>(
      `/clubs/${clubId}/invitations/${invitationId}/decline/`,
      payload
    ),

  revokeInvitation: (
    clubId: number,
    invitationId: number,
    payload: RevokeClubInvitationPayload = {}
  ) =>
    apiClient.post<ClubInvitation>(
      `/clubs/${clubId}/invitations/${invitationId}/revoke/`,
      payload
    ),
  listResources: async (clubId: number) => {
    const response = await apiClient.get<ListResponse<ClubResource>>(
      `/clubs/${clubId}/resources/`
    );
    return unwrapListResponse(response);
  },

  getResource: (clubId: number, resourceId: number) =>
    apiClient.get<ClubResource>(`/clubs/${clubId}/resources/${resourceId}/`),

  uploadResource: async (clubId: number, payload: UploadClubResourcePayload) => {
    const formData = new FormData();
    formData.append('title', payload.title);
    formData.append('file', payload.file);

    if (payload.description?.trim()) {
      formData.append('description', payload.description.trim());
    }

    if (payload.engagement_visibility) {
      formData.append('engagement_visibility', payload.engagement_visibility);
    }

    return apiClient.post<ClubResource>(
      `/clubs/${clubId}/resources/`,
      formData
    );
  },

  updateResource: (
    clubId: number,
    resourceId: number,
    payload: UpdateClubResourcePayload
  ) =>
    apiClient.patch<ClubResource>(
      `/clubs/${clubId}/resources/${resourceId}/`,
      payload
    ),

  archiveResource: (
    clubId: number,
    resourceId: number,
    payload: ArchiveClubResourcePayload
  ) =>
    apiClient.post<ClubResource>(
      `/clubs/${clubId}/resources/${resourceId}/archive/`,
      payload
    ),

  getResourceAccess: (clubId: number, resourceId: number) =>
    apiClient.get<ClubResourceSignedAccessResponse>(
      `/clubs/${clubId}/resources/${resourceId}/access/`
    ),

  sendResourceHeartbeat: (
    clubId: number,
    resourceId: number,
    payload: ClubResourceHeartbeatPayload
  ) =>
    apiClient.post<ClubResourceViewSummary>(
      `/clubs/${clubId}/resources/${resourceId}/heartbeat/`,
      payload
    ),

  getResourceEngagement: (clubId: number, resourceId: number) =>
    apiClient.get<ClubResourceEngagement>(
      `/clubs/${clubId}/resources/${resourceId}/engagement/`
    ),

  getMyResourceStatus: (clubId: number, resourceId: number) =>
    apiClient.get<ClubResourceMyStatus>(
      `/clubs/${clubId}/resources/${resourceId}/my_status/`
    ),

  listImportJobs: async (clubId: number) => {
    const response = await apiClient.get<ListResponse<ClubImportJobListItem>>(
      `/clubs/${clubId}/import-jobs/`
    );
    return unwrapListResponse(response);
  },

  getImportJob: (clubId: number, importJobId: number) =>
    apiClient.get<ClubImportJob>(`/clubs/${clubId}/import-jobs/${importJobId}/`),

  createImportJob: (clubId: number, payload: CreateClubImportJobPayload) =>
    apiClient.post<ClubImportJob>(`/clubs/${clubId}/import-jobs/`, payload),

  commitImportJob: (
    clubId: number,
    importJobId: number,
    payload: CommitClubImportJobPayload = { confirm: true },
  ) =>
    apiClient.post<ClubImportJob>(
      `/clubs/${clubId}/import-jobs/${importJobId}/commit/`,
      payload
    ),
};



export default clubsApi;