import apiClient from './client';
import type {
  AssignTrainingPlayersPayload,
  CreateTrainingBlockPayload,
  CreateTrainingSessionPayload,
  TrainingAttendanceUpdate,
  TrainingBlock,
  TrainingSession,
  TrainingSessionListItem,
  TrainingSessionListParams,
  TrainingSessionPlayer,
  UpdateTrainingBlockPayload,
  UpdateTrainingSessionPayload,
} from '../../types/training';

const basePath = (clubId: number) => `/clubs/${clubId}/training-sessions`;
const sessionPath = (clubId: number, sessionId: number) => `${basePath(clubId)}/${sessionId}`;
const blocksPath = (clubId: number, sessionId: number) => `${sessionPath(clubId, sessionId)}/blocks`;
const blockPath = (clubId: number, sessionId: number, blockId: number) =>
  `${blocksPath(clubId, sessionId)}/${blockId}`;
const playersPath = (clubId: number, sessionId: number) => `${sessionPath(clubId, sessionId)}/players`;

const cleanParams = (
  params?: TrainingSessionListParams
): Record<string, string> | undefined => {
  if (!params) return undefined;
  const cleaned: Record<string, string> = {};
  if (params.status) cleaned.status = params.status;
  if (params.session_type) cleaned.session_type = params.session_type;
  if (params.search?.trim()) cleaned.search = params.search.trim();
  return Object.keys(cleaned).length > 0 ? cleaned : undefined;
};

export const trainingApi = {
  listSessions: (clubId: number, params?: TrainingSessionListParams): Promise<TrainingSessionListItem[]> =>
    apiClient.get<TrainingSessionListItem[]>(`${basePath(clubId)}/`, cleanParams(params)),

  getSession: (clubId: number, sessionId: number): Promise<TrainingSession> =>
    apiClient.get<TrainingSession>(`${sessionPath(clubId, sessionId)}/`),

  createSession: (clubId: number, data: CreateTrainingSessionPayload): Promise<TrainingSession> =>
    apiClient.post<TrainingSession>(`${basePath(clubId)}/`, data),

  updateSession: (clubId: number, sessionId: number, data: UpdateTrainingSessionPayload): Promise<TrainingSession> =>
    apiClient.patch<TrainingSession>(`${sessionPath(clubId, sessionId)}/`, data),

  deleteSession: (clubId: number, sessionId: number): Promise<void> =>
    apiClient.delete<void>(`${sessionPath(clubId, sessionId)}/`),

  createBlock: (clubId: number, sessionId: number, data: CreateTrainingBlockPayload): Promise<TrainingBlock> =>
    apiClient.post<TrainingBlock>(`${blocksPath(clubId, sessionId)}/`, data),

  updateBlock: (
    clubId: number,
    sessionId: number,
    blockId: number,
    data: UpdateTrainingBlockPayload
  ): Promise<TrainingBlock> =>
    apiClient.patch<TrainingBlock>(`${blockPath(clubId, sessionId, blockId)}/`, data),

  deleteBlock: (clubId: number, sessionId: number, blockId: number): Promise<void> =>
    apiClient.delete<void>(`${blockPath(clubId, sessionId, blockId)}/`),

  listPlayers: (clubId: number, sessionId: number): Promise<TrainingSessionPlayer[]> =>
    apiClient.get<TrainingSessionPlayer[]>(`${playersPath(clubId, sessionId)}/`),

  assignPlayers: (
    clubId: number,
    sessionId: number,
    data: AssignTrainingPlayersPayload
  ): Promise<TrainingSession> =>
    apiClient.post<TrainingSession>(`${sessionPath(clubId, sessionId)}/assign-players/`, data),

  updateAttendance: (
    clubId: number,
    sessionId: number,
    players: TrainingAttendanceUpdate[]
  ): Promise<TrainingSession> =>
    apiClient.patch<TrainingSession>(`${sessionPath(clubId, sessionId)}/attendance/`, { players }),

  completeSession: (
    clubId: number,
    sessionId: number,
    data: UpdateTrainingSessionPayload
  ): Promise<TrainingSession> =>
    apiClient.post<TrainingSession>(`${sessionPath(clubId, sessionId)}/complete/`, data),
};
