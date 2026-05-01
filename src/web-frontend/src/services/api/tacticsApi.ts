import apiClient from './client';
import type {
  AddOpponentFormationPayload,
  CreateTacticsBoardFromTeamsheetPayload,
  CreateTacticsBoardFramePayload,
  CreateTacticsBoardItemPayload,
  CreateTacticsBoardPayload,
  DuplicateTacticsBoardFramePayload,
  DuplicateTacticsBoardPayload,
  TacticsBoard,
  TacticsBoardFrame,
  TacticsBoardItem,
  TacticsBoardListItem,
  TacticsItemPositionPatchPayload,
  UpdateTacticsBoardFramePayload,
  UpdateTacticsBoardItemPayload,
  UpdateTacticsBoardPayload,
} from '../../types/tactics';

const getBoardBasePath = (clubId: number) => `/clubs/${clubId}/tactics-boards`;

const getBoardPath = (clubId: number, boardId: number) =>
  `${getBoardBasePath(clubId)}/${boardId}`;

const getFrameBasePath = (clubId: number, boardId: number) =>
  `${getBoardPath(clubId, boardId)}/frames`;

const getFramePath = (clubId: number, boardId: number, frameId: number) =>
  `${getFrameBasePath(clubId, boardId)}/${frameId}`;

const getItemBasePath = (clubId: number, boardId: number, frameId: number) =>
  `${getFramePath(clubId, boardId, frameId)}/items`;

const getItemPath = (
  clubId: number,
  boardId: number,
  frameId: number,
  itemId: number
) => `${getItemBasePath(clubId, boardId, frameId)}/${itemId}`;

const patchItemRequest = async (
  clubId: number,
  boardId: number,
  frameId: number,
  itemId: number,
  data: UpdateTacticsBoardItemPayload
): Promise<TacticsBoardItem> => {
  return apiClient.patch<TacticsBoardItem>(
    `${getItemPath(clubId, boardId, frameId, itemId)}/`,
    data
  );
};

export const tacticsBoardApi = {
  listBoards: async (
    clubId: number,
    options?: { trash?: 'only' | 'include' }
  ): Promise<TacticsBoardListItem[]> =>
    apiClient.get<TacticsBoardListItem[]>(
      `${getBoardBasePath(clubId)}/`,
      options?.trash ? { trash: options.trash } : undefined
    ),

  getBoard: async (
    clubId: number,
    boardId: number,
    options?: { trash?: 'only' | 'include' }
  ): Promise<TacticsBoard> =>
    apiClient.get<TacticsBoard>(
      `${getBoardPath(clubId, boardId)}/`,
      options?.trash ? { trash: options.trash } : undefined
    ),

  createBoard: async (
    clubId: number,
    data: CreateTacticsBoardPayload
  ): Promise<TacticsBoard> =>
    apiClient.post<TacticsBoard>(`${getBoardBasePath(clubId)}/`, data),

  updateBoard: async (
    clubId: number,
    boardId: number,
    data: UpdateTacticsBoardPayload
  ): Promise<TacticsBoard> =>
    apiClient.patch<TacticsBoard>(`${getBoardPath(clubId, boardId)}/`, data),

  deleteBoard: async (clubId: number, boardId: number): Promise<void> =>
    apiClient.delete<void>(`${getBoardPath(clubId, boardId)}/`),

  trashBoard: async (clubId: number, boardId: number): Promise<TacticsBoard> =>
    apiClient.post<TacticsBoard>(`${getBoardPath(clubId, boardId)}/trash/`, {}),

  restoreBoard: async (clubId: number, boardId: number): Promise<TacticsBoard> =>
    apiClient.post<TacticsBoard>(`${getBoardPath(clubId, boardId)}/restore/`, {}),

  permanentDeleteBoard: async (clubId: number, boardId: number): Promise<void> =>
    apiClient.delete<void>(`${getBoardPath(clubId, boardId)}/permanent-delete/`),

  createFromTeamsheet: async (
    clubId: number,
    data: CreateTacticsBoardFromTeamsheetPayload
  ): Promise<TacticsBoard> =>
    apiClient.post<TacticsBoard>(
      `${getBoardBasePath(clubId)}/from-teamsheet/`,
      data
    ),

  addOpponentFormation: async (
    clubId: number,
    boardId: number,
    data: AddOpponentFormationPayload
  ): Promise<TacticsBoard> =>
    apiClient.post<TacticsBoard>(
      `${getBoardPath(clubId, boardId)}/add-opponent-formation/`,
      data
    ),

  duplicateBoard: async (
    clubId: number,
    boardId: number,
    data: DuplicateTacticsBoardPayload
  ): Promise<TacticsBoard> =>
    apiClient.post<TacticsBoard>(
      `${getBoardPath(clubId, boardId)}/duplicate/`,
      data
    ),
};

export const tacticsFrameApi = {
  listFrames: async (
    clubId: number,
    boardId: number
  ): Promise<TacticsBoardFrame[]> =>
    apiClient.get<TacticsBoardFrame[]>(`${getFrameBasePath(clubId, boardId)}/`),

  createFrame: async (
    clubId: number,
    boardId: number,
    data: CreateTacticsBoardFramePayload
  ): Promise<TacticsBoardFrame> =>
    apiClient.post<TacticsBoardFrame>(
      `${getFrameBasePath(clubId, boardId)}/`,
      data
    ),

  updateFrame: async (
    clubId: number,
    boardId: number,
    frameId: number,
    data: UpdateTacticsBoardFramePayload
  ): Promise<TacticsBoardFrame> =>
    apiClient.patch<TacticsBoardFrame>(
      `${getFramePath(clubId, boardId, frameId)}/`,
      data
    ),

  deleteFrame: async (
    clubId: number,
    boardId: number,
    frameId: number
  ): Promise<void> =>
    apiClient.delete<void>(`${getFramePath(clubId, boardId, frameId)}/`),

  duplicateFrame: async (
    clubId: number,
    boardId: number,
    frameId: number,
    data: DuplicateTacticsBoardFramePayload = {}
  ): Promise<TacticsBoardFrame> =>
    apiClient.post<TacticsBoardFrame>(
      `${getFramePath(clubId, boardId, frameId)}/duplicate/`,
      data
    ),
};

export const tacticsItemApi = {
  listItems: async (
    clubId: number,
    boardId: number,
    frameId: number
  ): Promise<TacticsBoardItem[]> =>
    apiClient.get<TacticsBoardItem[]>(
      `${getItemBasePath(clubId, boardId, frameId)}/`
    ),

  createItem: async (
    clubId: number,
    boardId: number,
    frameId: number,
    data: CreateTacticsBoardItemPayload
  ): Promise<TacticsBoardItem> =>
    apiClient.post<TacticsBoardItem>(
      `${getItemBasePath(clubId, boardId, frameId)}/`,
      data
    ),

  patchItemProperties: async (
    clubId: number,
    boardId: number,
    frameId: number,
    itemId: number,
    data: UpdateTacticsBoardItemPayload
  ): Promise<TacticsBoardItem> =>
    patchItemRequest(clubId, boardId, frameId, itemId, data),

  updateItem: async (
    clubId: number,
    boardId: number,
    frameId: number,
    itemId: number,
    data: UpdateTacticsBoardItemPayload
  ): Promise<TacticsBoardItem> =>
    patchItemRequest(clubId, boardId, frameId, itemId, data),

  deleteItem: async (
    clubId: number,
    boardId: number,
    frameId: number,
    itemId: number
  ): Promise<void> =>
    apiClient.delete<void>(`${getItemPath(clubId, boardId, frameId, itemId)}/`),

  saveItemPosition: async (
    clubId: number,
    boardId: number,
    frameId: number,
    itemId: number,
    data: TacticsItemPositionPatchPayload
  ): Promise<TacticsBoardItem> =>
    apiClient.patch<TacticsBoardItem>(
      `${getItemPath(clubId, boardId, frameId, itemId)}/`,
      data
    ),
};

export const tacticsApi = {
  ...tacticsBoardApi,
  ...tacticsFrameApi,
  ...tacticsItemApi,
};

export default tacticsApi;