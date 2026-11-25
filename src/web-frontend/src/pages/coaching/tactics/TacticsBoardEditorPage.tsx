import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import BoardSidebar from '../../../components/tactics/BoardSidebar';
import BoardToolbar from '../../../components/tactics/BoardToolbar';
import FrameList from '../../../components/tactics/FrameList';
import PitchCanvas from '../../../components/tactics/PitchCanvas';
import PlaybackOverlay from '../../../components/tactics/PlaybackOverlay';
import ToolPalette from '../../../components/tactics/ToolPalette';
import usePlayback from '../../../hooks/usePlayback';
import useTacticsBoardEditor from '../../../hooks/useTacticsBoardEditor';
import useTacticsKeyboardShortcuts from '../../../hooks/useTacticsKeyboardShortcuts';
import { tacticsBoardApi, tacticsFrameApi, tacticsItemApi } from '../../../services/api';
import type {
  TacticsActiveTool,
  TacticsBoard,
  TacticsBoardFrame,
  TacticsBoardItem,
  TacticsExportState,
  TacticsHistorySnapshot,
  UpdateTacticsBoardItemPayload,
} from '../../../types/tactics';
import { exportBoardPng } from '../../../utils/exportBoardPng';
import { interpolateFrames } from '../../../utils/interpolateFrames';
import { useAuth } from '../../../context/useAuth';
import styles from './css/TacticsBoardEditorPage.module.css';

const POSITION_EPSILON = 0.001;

const getFrameByIndex = (
  board: TacticsBoard | null,
  frameIndex: number
): TacticsBoardFrame | null => {
  if (!board) {
    return null;
  }

  return board.frames.find((frame) => frame.frame_index === frameIndex) ?? null;
};

const hasPositionChanged = (
  previousItem: TacticsBoardItem | undefined,
  currentItem: TacticsBoardItem
): boolean => {
  if (!previousItem) {
    return true;
  }

  return (
    Math.abs(previousItem.x - currentItem.x) > POSITION_EPSILON ||
    Math.abs(previousItem.y - currentItem.y) > POSITION_EPSILON
  );
};

const getChangedItems = (
  previousFrame: TacticsBoardFrame | null,
  currentFrame: TacticsBoardFrame
): TacticsBoardItem[] => {
  const previousItemsById = new Map<number, TacticsBoardItem>(
    (previousFrame?.items ?? []).map((item) => [item.id, item])
  );

  return currentFrame.items.filter((item) =>
    hasPositionChanged(previousItemsById.get(item.id), item)
  );
};

const sortItems = (items: TacticsBoardItem[]): TacticsBoardItem[] => {
  return [...items].sort((left, right) => {
    if (left.z_index !== right.z_index) {
      return left.z_index - right.z_index;
    }

    return left.id - right.id;
  });
};

const sortFrames = (frames: TacticsBoardFrame[]): TacticsBoardFrame[] => {
  return [...frames].sort((left, right) => {
    if (left.frame_index !== right.frame_index) {
      return left.frame_index - right.frame_index;
    }

    return left.id - right.id;
  });
};

const insertItemIntoBoard = (
  board: TacticsBoard,
  frameId: number,
  item: TacticsBoardItem
): TacticsBoard => {
  return {
    ...board,
    frames: board.frames.map((frame) => {
      if (frame.id !== frameId) {
        return frame;
      }

      return {
        ...frame,
        items: sortItems([...frame.items, item]),
      };
    }),
  };
};

const replaceItemInBoard = (
  board: TacticsBoard,
  frameId: number,
  item: TacticsBoardItem
): TacticsBoard => {
  return {
    ...board,
    frames: board.frames.map((frame) => {
      if (frame.id !== frameId) {
        return frame;
      }

      return {
        ...frame,
        items: sortItems(
          frame.items.map((existingItem) =>
            existingItem.id === item.id ? item : existingItem
          )
        ),
      };
    }),
  };
};

const removeItemFromBoard = (
  board: TacticsBoard,
  frameId: number,
  itemId: number
): TacticsBoard => {
  return {
    ...board,
    frames: board.frames.map((frame) => {
      if (frame.id !== frameId) {
        return frame;
      }

      return {
        ...frame,
        items: frame.items.filter((item) => item.id !== itemId),
      };
    }),
  };
};

const getNextZIndex = (frame: TacticsBoardFrame): number => {
  if (frame.items.length === 0) {
    return 0;
  }

  return Math.max(...frame.items.map((item) => item.z_index)) + 1;
};

const isTypingElement = (target: EventTarget | null): boolean => {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tagName = target.tagName.toLowerCase();

  return (
    tagName === 'input' ||
    tagName === 'textarea' ||
    tagName === 'select' ||
    target.isContentEditable
  );
};

const getNextActiveFrameIndexAfterDelete = (
  frames: TacticsBoardFrame[],
  deletedFrameIndex: number,
  currentActiveFrameIndex: number
): number | null => {
  const remainingFrames = sortFrames(
    frames.filter((frame) => frame.frame_index !== deletedFrameIndex)
  );

  if (remainingFrames.length === 0) {
    return null;
  }

  if (currentActiveFrameIndex !== deletedFrameIndex) {
    return currentActiveFrameIndex;
  }

  const previousFrame = [...remainingFrames]
    .reverse()
    .find((frame) => frame.frame_index < deletedFrameIndex);

  if (previousFrame) {
    return previousFrame.frame_index;
  }

  return remainingFrames[0].frame_index;
};

const toExportFileName = (title: string): string => {
  const safeTitle = title
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

  return `${safeTitle || 'tactics-board'}.png`;
};

const cloneBoardForSnapshot = (board: TacticsBoard): TacticsBoard => {
  return {
    ...board,
    frames: board.frames.map((frame) => ({
      ...frame,
      items: frame.items.map((item) => {
        if (item.item_type === 'player') {
          return {
            ...item,
            style: { ...(item.style ?? {}) },
            player_summary: item.player_summary
              ? { ...item.player_summary }
              : null,
          } as TacticsBoardItem;
        }

        return {
          ...item,
          style: { ...(item.style ?? {}) },
          player_summary: null,
        } as TacticsBoardItem;
      }),
    })),
  };
};

const createExplicitHistorySnapshot = (
  board: TacticsBoard,
  activeFrameIndex: number,
  selectedItemId: number | null
): TacticsHistorySnapshot => {
  return {
    board: cloneBoardForSnapshot(board),
    activeFrameIndex,
    selectedItemId,
  };
};

const createPreMoveSnapshot = (
  board: TacticsBoard,
  frameIndex: number,
  itemId: number,
  initialX: number,
  initialY: number,
  selectedItemId: number | null
): TacticsHistorySnapshot => {
  const snapshotBoard = cloneBoardForSnapshot(board);

  return {
    board: {
      ...snapshotBoard,
      frames: snapshotBoard.frames.map((frame) => {
        if (frame.frame_index !== frameIndex) {
          return frame;
        }

        return {
          ...frame,
          items: frame.items.map((item) =>
            item.id === itemId
              ? {
                  ...item,
                  x: initialX,
                  y: initialY,
                }
              : item
          ),
        };
      }),
    },
    activeFrameIndex: frameIndex,
    selectedItemId,
  };
};

const TacticsBoardEditorPage: React.FC = () => {
  const { clubId, boardId } = useParams<{ clubId: string; boardId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  const numericClubId = useMemo(() => Number(clubId), [clubId]);
  const numericBoardId = useMemo(() => Number(boardId), [boardId]);
  const isTrashView = searchParams.get('view') === 'trash';

  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [persistedBoard, setPersistedBoard] = useState<TacticsBoard | null>(null);
  const [isBoardActionLoading, setIsBoardActionLoading] = useState(false);
  const [isUpdatingProperties, setIsUpdatingProperties] = useState(false);
  const [isDeletingItem, setIsDeletingItem] = useState(false);
  const [isMutatingFrames, setIsMutatingFrames] = useState(false);
  const [isPresentationOpen, setIsPresentationOpen] = useState(false);
  const pitchSvgRef = useRef<SVGSVGElement | null>(null);
  const [exportState, setExportState] = useState<TacticsExportState>({
    status: 'idle',
    error: null,
  });

  const {
    state,
    activeFrame,
    selectedItem,
    loadBoard,
    selectItem,
    setActiveFrameIndex,
    setActiveTool,
    startDraftItem,
    updateDraftItem,
    clearDraftItem,
    addFrameLocal,
    deleteFrameLocal,
    addItemLocal,
    replaceItemLocal,
    deleteItemLocal,
    moveItemLocal,
    pushHistorySnapshot,
    undo,
    redo,
    saveStarted,
    saveSucceeded,
    saveFailed,
    clearError,
    canUndo,
    canRedo,
  } = useTacticsBoardEditor();

  const playback = usePlayback({
    frames: state.board?.frames ?? [],
    initialFrameIndex: state.activeFrameIndex,
  });
  const loadBoardRef = useRef(loadBoard);
  const resetPlaybackRef = useRef(playback.reset);
  loadBoardRef.current = loadBoard;
  resetPlaybackRef.current = playback.reset;

  const playbackRenderFrame = useMemo(() => {
    if (!playback.activePair || !playback.activePair.targetFrame) {
      return null;
    }

    return interpolateFrames(
      playback.activePair.sourceFrame,
      playback.activePair.targetFrame,
      playback.progress
    );
  }, [playback.activePair, playback.progress]);

  const isPlaybackActive = playback.status !== 'idle';
  const isBoardTrashed = Boolean(state.board?.is_trashed);
  const isAnimatedBoard = state.board?.board_type === 'animated';
  const canManageBoardTrash =
    typeof user?.id === 'number' &&
    typeof state.board?.created_by === 'number' &&
    user.id === state.board.created_by;

  const displayedFrame = useMemo(() => {
    if (isPlaybackActive && playback.activePair) {
      return playback.activePair.sourceFrame;
    }

    return activeFrame;
  }, [activeFrame, isPlaybackActive, playback.activePair]);

  const displayedRenderItems = useMemo(() => {
    if (!isPlaybackActive || !playbackRenderFrame) {
      return undefined;
    }

    return playbackRenderFrame.items;
  }, [isPlaybackActive, playbackRenderFrame]);

  const refreshBoardDetail = useCallback(async () => {
    const refreshedBoard = await tacticsBoardApi.getBoard(
      numericClubId,
      numericBoardId,
      isTrashView ? { trash: 'only' } : undefined
    );
    setPersistedBoard(refreshedBoard);
    saveSucceeded(refreshedBoard);
    return refreshedBoard;
  }, [isTrashView, numericBoardId, numericClubId, saveSucceeded]);

  useEffect(() => {
    const loadBoardDetail = async () => {
      if (!Number.isInteger(numericClubId) || numericClubId <= 0) {
        setPageError('Invalid club ID.');
        setLoading(false);
        return;
      }

      if (!Number.isInteger(numericBoardId) || numericBoardId <= 0) {
        setPageError('Invalid board ID.');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setPageError(null);

        const data = await tacticsBoardApi.getBoard(
          numericClubId,
          numericBoardId,
          isTrashView ? { trash: 'only' } : undefined
        );
        loadBoardRef.current(data);
        setPersistedBoard(data);
        resetPlaybackRef.current(data.frames[0]?.frame_index ?? 0);
      } catch (err) {
        setPageError(err instanceof Error ? err.message : 'Failed to load tactics board.');
      } finally {
        setLoading(false);
      }
    };

    void loadBoardDetail();
  }, [numericBoardId, numericClubId, isTrashView]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && state.draftItem) {
        clearDraftItem();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [clearDraftItem, state.draftItem]);

  const handleDeleteSelectedItem = useCallback(async () => {
    if (isBoardTrashed) {
      saveFailed('Restore this board before editing it.');
      return;
    }

    if (!activeFrame || !selectedItem || selectedItem.item_type === 'player') {
      return;
    }

    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    try {
      setIsDeletingItem(true);

      await tacticsItemApi.deleteItem(
        numericClubId,
        numericBoardId,
        activeFrame.id,
        selectedItem.id
      );

      pushHistorySnapshot();

      deleteItemLocal(activeFrame.id, selectedItem.id);
      setPersistedBoard((previousBoard) => {
        if (!previousBoard) {
          return previousBoard;
        }

        return removeItemFromBoard(previousBoard, activeFrame.id, selectedItem.id);
      });
    } catch (err) {
      saveFailed(
        err instanceof Error ? err.message : 'Failed to delete selected item.'
      );
    } finally {
      setIsDeletingItem(false);
    }
  }, [
    activeFrame,
    clearError,
    deleteItemLocal,
    isBoardTrashed,
    isPlaybackActive,
    numericBoardId,
    numericClubId,
    pushHistorySnapshot,
    saveFailed,
    selectedItem,
    state.error,
  ]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Delete') {
        return;
      }

      if (isTypingElement(event.target)) {
        return;
      }

      if (!selectedItem || selectedItem.item_type === 'player' || isDeletingItem) {
        return;
      }

      event.preventDefault();
      void handleDeleteSelectedItem();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleDeleteSelectedItem, isDeletingItem, selectedItem]);

  const playerCount = displayedFrame
    ? displayedFrame.items.filter((item) => item.item_type === 'player').length
    : 0;

  const activeTool: TacticsActiveTool = state.activeTool ?? 'select';
  const hasSelectedDeletableItem =
    Boolean(selectedItem) && selectedItem?.item_type !== 'player';
  const hasAnySelection = state.selectedItemId !== null;
  const canSaveBoard = state.isDirty && !state.isSaving && !isPlaybackActive;

  const handleBack = () => {
    const params = new URLSearchParams({ tab: 'tactics' });
    if (isTrashView) {
      params.set('view', 'trash');
    }
    navigate(`/clubs/${numericClubId}?${params.toString()}`);
  };

  const handleMoveToTrash = async () => {
    if (!state.board) {
      return;
    }

    const confirmed = window.confirm('Move this tactics board to trash?');
    if (!confirmed) {
      return;
    }

    try {
      setIsBoardActionLoading(true);
      setPageError(null);
      await tacticsBoardApi.trashBoard(numericClubId, numericBoardId);
      navigate(`/clubs/${numericClubId}/tactics-boards?view=trash`);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : 'Failed to move board to trash.');
    } finally {
      setIsBoardActionLoading(false);
    }
  };

  const handleRestoreBoard = async () => {
    if (!state.board) {
      return;
    }

    try {
      setIsBoardActionLoading(true);
      setPageError(null);
      await tacticsBoardApi.restoreBoard(numericClubId, numericBoardId);
      navigate(`/clubs/${numericClubId}/tactics-boards/${numericBoardId}`);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : 'Failed to restore board.');
    } finally {
      setIsBoardActionLoading(false);
    }
  };

  const handlePermanentDeleteBoard = async () => {
    if (!state.board) {
      return;
    }

    const confirmed = window.confirm(
      'Delete this tactics board permanently? This cannot be undone.'
    );
    if (!confirmed) {
      return;
    }

    try {
      setIsBoardActionLoading(true);
      setPageError(null);
      await tacticsBoardApi.permanentDeleteBoard(numericClubId, numericBoardId);
      navigate(`/clubs/${numericClubId}/tactics-boards?view=trash`);
    } catch (err) {
      setPageError(
        err instanceof Error ? err.message : 'Failed to permanently delete board.'
      );
    } finally {
      setIsBoardActionLoading(false);
    }
  };

  const guardDirtyFrameTransition = (message: string) => {
    if (state.isDirty) {
      saveFailed(message);
      return true;
    }

    return false;
  };

  const handleSelectTool = (tool: TacticsActiveTool) => {
    if (isBoardTrashed) {
      saveFailed('Restore this board before editing it.');
      return;
    }

    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    setActiveTool(tool);
  };

  const handleSelectFrame = (frameIndex: number) => {
    if (guardDirtyFrameTransition('Save current frame changes before switching frames.')) {
      return;
    }

    if (state.error) {
      clearError();
    }

    if (isPlaybackActive) {
      playback.stop();
      setIsPresentationOpen(false);
    }

    setActiveFrameIndex(frameIndex);
    playback.reset(frameIndex);
  };

  const handleAddFrame = async () => {
    if (isBoardTrashed) {
      saveFailed('Restore this board before editing it.');
      return;
    }

    if (!state.board) {
      return;
    }

    if (!isAnimatedBoard) {
      saveFailed('Frame controls are available only on animated boards.');
      return;
    }

    if (guardDirtyFrameTransition('Save current frame changes before adding a frame.')) {
      return;
    }

    if (state.error) {
      clearError();
    }

    if (isPlaybackActive) {
      playback.stop();
      setIsPresentationOpen(false);
    }

    const historySnapshot = createExplicitHistorySnapshot(
      state.board,
      state.activeFrameIndex,
      state.selectedItemId
    );

    try {
      setIsMutatingFrames(true);

      const currentFrameIndex = state.activeFrameIndex;
      const createdFrame = await tacticsFrameApi.createFrame(
        numericClubId,
        numericBoardId,
        { copy_items_from_frame_index: currentFrameIndex }
      );

      addFrameLocal(createdFrame, { setActiveFrame: true });
      await refreshBoardDetail();
      pushHistorySnapshot(historySnapshot);
      playback.reset(createdFrame.frame_index);
    } catch (err) {
      saveFailed(err instanceof Error ? err.message : 'Failed to add frame.');
    } finally {
      setIsMutatingFrames(false);
    }
  };

  const handleDuplicateFrame = async (frame: TacticsBoardFrame) => {
    if (isBoardTrashed) {
      saveFailed('Restore this board before editing it.');
      return;
    }

    if (guardDirtyFrameTransition('Save current frame changes before duplicating a frame.')) {
      return;
    }

    if (!isAnimatedBoard) {
      saveFailed('Frame controls are available only on animated boards.');
      return;
    }

    if (state.error) {
      clearError();
    }

    if (isPlaybackActive) {
      playback.stop();
      setIsPresentationOpen(false);
    }

    if (!state.board) {
      return;
    }

    const historySnapshot = createExplicitHistorySnapshot(
      state.board,
      state.activeFrameIndex,
      state.selectedItemId
    );

    try {
      setIsMutatingFrames(true);

      const duplicatedFrame = await tacticsFrameApi.duplicateFrame(
        numericClubId,
        numericBoardId,
        frame.id,
        {}
      );

      addFrameLocal(duplicatedFrame, { setActiveFrame: true });
      await refreshBoardDetail();
      pushHistorySnapshot(historySnapshot);
      playback.reset(duplicatedFrame.frame_index);
    } catch (err) {
      saveFailed(err instanceof Error ? err.message : 'Failed to duplicate frame.');
    } finally {
      setIsMutatingFrames(false);
    }
  };

  const handleDeleteFrame = async (frame: TacticsBoardFrame) => {
    if (isBoardTrashed) {
      saveFailed('Restore this board before editing it.');
      return;
    }

    if (!state.board || state.board.frames.length <= 1) {
      return;
    }

    if (guardDirtyFrameTransition('Save current frame changes before deleting a frame.')) {
      return;
    }

    if (!isAnimatedBoard) {
      saveFailed('Frame controls are available only on animated boards.');
      return;
    }

    if (state.error) {
      clearError();
    }

    if (isPlaybackActive) {
      playback.stop();
      setIsPresentationOpen(false);
    }

    const historySnapshot = createExplicitHistorySnapshot(
      state.board,
      state.activeFrameIndex,
      state.selectedItemId
    );

    const nextActiveFrameIndex = getNextActiveFrameIndexAfterDelete(
      state.board.frames,
      frame.frame_index,
      state.activeFrameIndex
    );

    try {
      setIsMutatingFrames(true);

      await tacticsFrameApi.deleteFrame(
        numericClubId,
        numericBoardId,
        frame.id
      );

      deleteFrameLocal(frame.id, { nextActiveFrameIndex });
      await refreshBoardDetail();
      pushHistorySnapshot(historySnapshot);
      playback.reset(nextActiveFrameIndex ?? 0);
    } catch (err) {
      saveFailed(err instanceof Error ? err.message : 'Failed to delete frame.');
    } finally {
      setIsMutatingFrames(false);
    }
  };

  const handleCreatePointItem = async (
    tool: Extract<TacticsActiveTool, 'ball' | 'text'>,
    x: number,
    y: number
  ) => {
    if (!activeFrame) {
      return;
    }

    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    try {
      const nextZIndex = getNextZIndex(activeFrame);

      const createdItem =
        tool === 'ball'
          ? await tacticsItemApi.createItem(
              numericClubId,
              numericBoardId,
              activeFrame.id,
              {
                item_type: 'ball',
                team_side: 'neutral',
                x,
                y,
                z_index: nextZIndex,
                rotation: 0,
                style: {},
              }
            )
          : await (async () => {
              const rawLabel = window.prompt('Enter text label');
              if (rawLabel === null) {
                return null;
              }

              const label = rawLabel.trim();
              if (!label) {
                return null;
              }

              return tacticsItemApi.createItem(
                numericClubId,
                numericBoardId,
                activeFrame.id,
                {
                  item_type: 'text',
                  team_side: 'neutral',
                  label,
                  x,
                  y,
                  z_index: nextZIndex,
                  rotation: 0,
                  style: {},
                }
              );
            })();

      if (!createdItem) {
        return;
      }

      pushHistorySnapshot();

      addItemLocal(activeFrame.id, createdItem, { selectAfterAdd: true });
      setPersistedBoard((previousBoard) => {
        if (!previousBoard) {
          return previousBoard;
        }

        return insertItemIntoBoard(previousBoard, activeFrame.id, createdItem);
      });
    } catch (err) {
      saveFailed(
        err instanceof Error ? err.message : `Failed to create ${tool} item.`
      );
    }
  };

  const handleStartDirectionalDraft = (
    tool: Extract<TacticsActiveTool, 'arrow' | 'line'>,
    x: number,
    y: number
  ) => {
    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    startDraftItem({
      tool,
      startX: x,
      startY: y,
      currentX: x,
      currentY: y,
    });
  };

  const handleUpdateDirectionalDraft = (x: number, y: number) => {
    if (!state.draftItem) {
      return;
    }

    if (state.draftItem.tool !== 'arrow' && state.draftItem.tool !== 'line') {
      return;
    }

    updateDraftItem({
      ...state.draftItem,
      currentX: x,
      currentY: y,
    });
  };

  const handleCompleteDirectionalItem = async (
    tool: Extract<TacticsActiveTool, 'arrow' | 'line'>,
    startX: number,
    startY: number,
    endX: number,
    endY: number
  ) => {
    if (!activeFrame) {
      return;
    }

    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    try {
      const nextZIndex = getNextZIndex(activeFrame);

      const createdItem = await tacticsItemApi.createItem(
        numericClubId,
        numericBoardId,
        activeFrame.id,
        {
          item_type: tool,
          team_side: 'neutral',
          x: startX,
          y: startY,
          end_x: endX,
          end_y: endY,
          z_index: nextZIndex,
          rotation: 0,
          style: {},
        }
      );

      pushHistorySnapshot();

      addItemLocal(activeFrame.id, createdItem, { selectAfterAdd: true });
      clearDraftItem();

      setPersistedBoard((previousBoard) => {
        if (!previousBoard) {
          return previousBoard;
        }

        return insertItemIntoBoard(previousBoard, activeFrame.id, createdItem);
      });
    } catch (err) {
      saveFailed(
        err instanceof Error ? err.message : `Failed to create ${tool} item.`
      );
    }
  };

  const handleStartZoneDraft = (x: number, y: number) => {
    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    startDraftItem({
      tool: 'zone',
      startX: x,
      startY: y,
      currentX: x,
      currentY: y,
    });
  };

  const handleUpdateZoneDraft = (x: number, y: number) => {
    if (!state.draftItem || state.draftItem.tool !== 'zone') {
      return;
    }

    updateDraftItem({
      ...state.draftItem,
      currentX: x,
      currentY: y,
    });
  };

  const handleCompleteZoneItem = async (
    x: number,
    y: number,
    width: number,
    height: number
  ) => {
    if (!activeFrame) {
      return;
    }

    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    try {
      const nextZIndex = getNextZIndex(activeFrame);

      const createdItem = await tacticsItemApi.createItem(
        numericClubId,
        numericBoardId,
        activeFrame.id,
        {
          item_type: 'zone',
          team_side: 'neutral',
          x,
          y,
          width,
          height,
          z_index: nextZIndex,
          rotation: 0,
          style: {},
        }
      );

      pushHistorySnapshot();

      addItemLocal(activeFrame.id, createdItem, { selectAfterAdd: true });
      clearDraftItem();

      setPersistedBoard((previousBoard) => {
        if (!previousBoard) {
          return previousBoard;
        }

        return insertItemIntoBoard(previousBoard, activeFrame.id, createdItem);
      });
    } catch (err) {
      saveFailed(
        err instanceof Error ? err.message : 'Failed to create zone item.'
      );
    }
  };

  const handleCancelDraft = () => {
    clearDraftItem();
  };

  const handleUpdateSelectedItemProperties = async (
    payload: UpdateTacticsBoardItemPayload
  ) => {
    if (!activeFrame || !selectedItem || selectedItem.item_type === 'player') {
      return;
    }

    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    try {
      setIsUpdatingProperties(true);

      const updatedItem = await tacticsItemApi.patchItemProperties(
        numericClubId,
        numericBoardId,
        activeFrame.id,
        selectedItem.id,
        payload
      );

      pushHistorySnapshot();

      replaceItemLocal(activeFrame.id, updatedItem, {
        selectAfterReplace: true,
      });

      setPersistedBoard((previousBoard) => {
        if (!previousBoard) {
          return previousBoard;
        }

        return replaceItemInBoard(previousBoard, activeFrame.id, updatedItem);
      });
    } catch (err) {
      saveFailed(
        err instanceof Error ? err.message : 'Failed to update item properties.'
      );
    } finally {
      setIsUpdatingProperties(false);
    }
  };

  const handleMoveItem = (itemId: number, x: number, y: number) => {
    if (isBoardTrashed) {
      saveFailed('Restore this board before editing it.');
      return;
    }

    if (!activeFrame) {
      return;
    }

    if (isPlaybackActive) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (state.error) {
      clearError();
    }

    moveItemLocal(activeFrame.frame_index, itemId, x, y);
  };

  const handleCommitMoveItem = useCallback(
    (
      frameIndex: number,
      itemId: number,
      initialX: number,
      initialY: number,
      finalX: number,
      finalY: number
    ) => {
      if (!state.board) {
        return;
      }

      if (
        Math.abs(initialX - finalX) <= POSITION_EPSILON &&
        Math.abs(initialY - finalY) <= POSITION_EPSILON
      ) {
        return;
      }

      pushHistorySnapshot(
        createPreMoveSnapshot(
          state.board,
          frameIndex,
          itemId,
          initialX,
          initialY,
          state.selectedItemId
        )
      );
    },
    [pushHistorySnapshot, state.board, state.selectedItemId]
  );

  const handleUndo = () => {
    if (isPlaybackActive || state.isSaving) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (!canUndo) {
      return;
    }

    if (state.error) {
      clearError();
    }

    undo();
  };

  const handleRedo = () => {
    if (isPlaybackActive || state.isSaving) {
      saveFailed('Stop playback before editing items.');
      return;
    }

    if (!canRedo) {
      return;
    }

    if (state.error) {
      clearError();
    }

    redo();
  };

  const handleSave = async () => {
  if (isBoardTrashed) {
    saveFailed('Restore this board before editing it.');
    return;
  }
    
    if (!state.board || !activeFrame) {
      return;
    }

    if (isPlaybackActive) {
      saveFailed('Stop playback before saving.');
      return;
    }

    const previousFrame = getFrameByIndex(persistedBoard, activeFrame.frame_index);
    const changedItems = getChangedItems(previousFrame, activeFrame);

    if (changedItems.length === 0) {
      saveSucceeded(state.board);
      return;
    }

    try {
      saveStarted();

      await Promise.all(
        changedItems.map((item) =>
          tacticsItemApi.saveItemPosition(
            numericClubId,
            numericBoardId,
            activeFrame.id,
            item.id,
            {
              x: item.x,
              y: item.y,
            }
          )
        )
      );

      const refreshedBoard = await tacticsBoardApi.getBoard(
        numericClubId,
        numericBoardId,
        isTrashView ? { trash: 'only' } : undefined
      );

      setPersistedBoard(refreshedBoard);
      saveSucceeded(refreshedBoard);
    } catch (err) {
      saveFailed(
        err instanceof Error
            ? `${err.message} Local edits are still visible and not yet saved. Retry save or reload the latest board.`
            : 'Failed to save board changes. Local edits are still visible and not yet saved. Retry save or reload the latest board.'
        );
    }
  };

  const handleExportPng = useCallback(async () => {
    if (isPlaybackActive || isPresentationOpen) {
      setExportState({
        status: 'error',
        error: 'Stop playback before exporting a PNG.',
      });
      return;
    }

    if (!pitchSvgRef.current) {
      setExportState({
        status: 'error',
        error: 'Pitch view is not ready for export.',
      });
      return;
    }

    try {
      setExportState({
        status: 'exporting',
        error: null,
      });

      await exportBoardPng(pitchSvgRef.current, {
        fileName: toExportFileName(state.board?.title ?? 'tactics-board'),
        scale: 2,
      });

      setExportState({
        status: 'idle',
        error: null,
      });
    } catch (err) {
      setExportState({
        status: 'error',
        error: err instanceof Error ? err.message : 'Failed to export PNG.',
      });
    }
  }, [isPlaybackActive, isPresentationOpen, state.board?.title]);

  const handlePlay = () => {
    if (!isAnimatedBoard) {
      saveFailed('Playback is only available on animated boards.');
      return;
    }

    if (guardDirtyFrameTransition('Save current frame changes before playback.')) {
      return;
    }

    if (state.error) {
      clearError();
    }

    playback.play(state.activeFrameIndex);
  };

  const handlePause = () => {
    if (!isAnimatedBoard) {
      return;
    }

    playback.pause();
  };

  const handleStop = () => {
    if (!isAnimatedBoard) {
      return;
    }

    playback.stop();
  };

  const handleOpenPresentation = () => {
    if (!isAnimatedBoard) {
      saveFailed('Presentation mode is only available on animated boards.');
      return;
    }

    if (guardDirtyFrameTransition('Save current frame changes before presentation mode.')) {
      return;
    }

    if (state.error) {
      clearError();
    }

    if (playback.status === 'idle') {
      playback.play(state.activeFrameIndex);
    }

    setIsPresentationOpen(true);
  };

  const handleClosePresentation = () => {
    setIsPresentationOpen(false);
    playback.stop();
  };

  const handleReloadLatestBoard = useCallback(async () => {
  if (!Number.isInteger(numericClubId) || !Number.isInteger(numericBoardId)) {
    return;
  }

  try {
    setLoading(true);
    setPageError(null);
    clearError();
    setExportState({ status: 'idle', error: null });

    const refreshedBoard = await tacticsBoardApi.getBoard(
      numericClubId,
      numericBoardId
    );

    setPersistedBoard(refreshedBoard);
    loadBoard(refreshedBoard);
    playback.reset(refreshedBoard.frames[0]?.frame_index ?? 0);
    setIsPresentationOpen(false);
    } catch (err) {
        setPageError(
        err instanceof Error
            ? err.message
            : 'Failed to reload the latest board state.'
        );
    } finally {
        setLoading(false);
    }
    }, [
    clearError,
    loadBoard,
    numericBoardId,
    numericClubId,
    playback,
    ]);

  useTacticsKeyboardShortcuts({
    enabled: true,
    hasDraft: Boolean(state.draftItem),
    hasSelectedDeletableItem,
    hasAnySelection,
    canUndo,
    canRedo,
    canSave: canSaveBoard,
    isPlaybackActive,
    isDeletingItem,
    onUndo: handleUndo,
    onRedo: handleRedo,
    onDeleteSelectedItem: () => {
      void handleDeleteSelectedItem();
    },
    onCancelDraft: handleCancelDraft,
    onDeselect: () => selectItem(null),
    onSave: () => {
      void handleSave();
    },
  });

  if (loading) {
    return (
      <div className={styles.feedbackState}>
        <h1 className={styles.feedbackTitle}>Tactics Board Editor</h1>
        <p className={styles.feedbackText}>Loading tactics board...</p>
      </div>
    );
  }

  if (pageError) {
    return (
      <div className={styles.feedbackState}>
        <button type="button" onClick={handleBack} className={styles.utilityButton}>
          ← 
        </button>
        <h1 className={styles.feedbackTitle}>Tactics Board Editor</h1>
        <p className={styles.feedbackText}>Error: {pageError}</p>
      </div>
    );
  }

  if (!state.board) {
    return (
      <div className={styles.feedbackState}>
        <button type="button" onClick={handleBack} className={styles.utilityButton}>
          ← Back to Tactics Boards
        </button>
        <h1 className={styles.feedbackTitle}>Tactics Board Editor</h1>
        <p className={styles.feedbackText}>Tactics board not found.</p>
      </div>
    );
  }

  if (!activeFrame || !displayedFrame) {
    return (
      <div className={styles.feedbackState}>
        <button type="button" onClick={handleBack} className={styles.utilityButton}>
          ← Back to Tactics Boards
        </button>
        <h1 className={styles.feedbackTitle}>{state.board.title}</h1>
        <p className={styles.feedbackText}>This board does not currently contain a usable frame.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <BoardToolbar
        title={state.board.title}
        isDirty={state.isDirty}
        isSaving={state.isSaving}
        activeTool={activeTool}
        hasDraft={Boolean(state.draftItem)}
        currentFrameIndex={
          isPlaybackActive ? playback.currentFrameIndex : state.activeFrameIndex
        }
        targetFrameIndex={isPlaybackActive ? playback.targetFrameIndex : null}
        playbackStatus={playback.status}
        isAnimatedBoard={isAnimatedBoard}
        canPlay={isAnimatedBoard && playback.canPlay}
        isPresentationOpen={isPresentationOpen}
        isExportingPng={exportState.status === 'exporting'}
        exportError={exportState.error}
        canUndo={canUndo && !isPlaybackActive && !state.isSaving}
        canRedo={canRedo && !isPlaybackActive && !state.isSaving}
        onBack={handleBack}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onSave={handleSave}
        canSave={canSaveBoard}
        onPlay={handlePlay}
        onPause={handlePause}
        onStop={handleStop}
        onOpenPresentation={handleOpenPresentation}
        onExportPng={handleExportPng}
        canExportPng={
          exportState.status !== 'exporting' &&
          !isPlaybackActive &&
          !isPresentationOpen
        }
      />

      <section className={styles.heroCard}>
        <div className={styles.heroCopy}>
          <h1 className={styles.heroTitle}>{state.board.title}</h1>
          <p className={styles.heroText}>
            {state.board.description || 'No description provided.'}
          </p>
          <p className={styles.heroSupportingText}>
            {isBoardTrashed
              ? 'This board is in trash and has been switched into read-only mode.'
              : isAnimatedBoard
                ? 'Animated board mode keeps frame progression, playback, and presentation tools available.'
                : 'Static board mode focuses on a single tactical picture without playback controls.'}
          </p>
        </div>

        <div className={styles.heroActions}>
          <span className={styles.heroPill}>
            {isAnimatedBoard ? 'Animated board' : 'Static board'}
          </span>
          <span className={styles.heroPill}>
            {state.board.pitch_orientation}
          </span>

          <button
            type="button"
            onClick={handleBack}
            className={styles.utilityButton}
          >
            ← Back
          </button>

          {canManageBoardTrash && !isBoardTrashed ? (
            <button
              type="button"
              onClick={() => void handleMoveToTrash()}
              disabled={isBoardActionLoading}
              className={styles.dangerButton}
            >
              {isBoardActionLoading ? 'Moving…' : 'Move to Trash'}
            </button>
          ) : null}

          {canManageBoardTrash && isBoardTrashed ? (
            <>
              <button
                type="button"
                onClick={() => void handleRestoreBoard()}
                disabled={isBoardActionLoading}
                className={styles.successButton}
              >
                {isBoardActionLoading ? 'Restoring…' : 'Restore'}
              </button>

              <button
                type="button"
                onClick={() => void handlePermanentDeleteBoard()}
                disabled={isBoardActionLoading}
                className={styles.dangerButton}
              >
                {isBoardActionLoading ? 'Deleting…' : 'Delete Permanently'}
              </button>
            </>
          ) : null}
        </div>
      </section>

      {state.error ? (
    <div className={styles.errorBanner}>
        <span>{state.error}</span>
        <button type="button" onClick={() => void handleReloadLatestBoard()} className={styles.utilityButton}>
        Reload latest board
        </button>
    </div>
    ) : null}

      <FrameList
        frames={state.board.frames}
        activeFrameIndex={
          isPlaybackActive ? playback.currentFrameIndex : state.activeFrameIndex
        }
        allowAnimationActions={isAnimatedBoard}
        isMutating={isMutatingFrames || isPlaybackActive}
        onSelectFrame={handleSelectFrame}
        onAddFrame={handleAddFrame}
        onDuplicateFrame={handleDuplicateFrame}
        onDeleteFrame={handleDeleteFrame}
      />

      <div className={isBoardTrashed ? `${styles.readOnlyBlock} ${styles.readOnlyMuted}` : styles.readOnlyBlock}>
        <ToolPalette
          activeTool={activeTool}
          onSelectTool={handleSelectTool}
        />
      </div>

      {isBoardTrashed ? (
        <div className={styles.trashBanner}>
          This tactics board is currently in trash and has been switched into read-only mode.
          {state.board.trash_expires_at ? (
            <span className={styles.trashBannerMeta}>
              {' '}It will be removed permanently after{' '}
              {new Date(state.board.trash_expires_at).toLocaleDateString('en-IE', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
              })}
              .
            </span>
          ) : null}
        </div>
      ) : null}

        <div className={isBoardTrashed ? `${styles.editorGrid} ${styles.readOnlyMuted}` : styles.editorGrid}>
        <div className={styles.canvasPanel}>
          <PitchCanvas
            svgElementRef={pitchSvgRef}
            frame={displayedFrame}
            pitchOrientation={state.board.pitch_orientation}
            renderItems={displayedRenderItems}
            isPlaybackMode={isPlaybackActive}
            activeTool={activeTool}
            draftItem={state.draftItem}
            selectedItemId={state.selectedItemId}
            onSelectItem={selectItem}
            onMoveItem={handleMoveItem}
            onCommitMoveItem={handleCommitMoveItem}
            onCreatePointItem={handleCreatePointItem}
            onStartDirectionalDraft={handleStartDirectionalDraft}
            onUpdateDirectionalDraft={handleUpdateDirectionalDraft}
            onCompleteDirectionalItem={handleCompleteDirectionalItem}
            onStartZoneDraft={handleStartZoneDraft}
            onUpdateZoneDraft={handleUpdateZoneDraft}
            onCompleteZoneItem={handleCompleteZoneItem}
            onCancelDraft={handleCancelDraft}
          />
        </div>

        <BoardSidebar
          board={state.board}
          activeFrameIndex={
            isPlaybackActive ? playback.currentFrameIndex : activeFrame.frame_index
          }
          playerCount={playerCount}
          selectedItem={selectedItem}
          error={state.error}
          isUpdatingProperties={isUpdatingProperties}
          onUpdateSelectedItemProperties={handleUpdateSelectedItemProperties}
          isDeletingItem={isDeletingItem}
          onDeleteSelectedItem={handleDeleteSelectedItem}
        />
      </div>

      <PlaybackOverlay
        isOpen={isPresentationOpen}
        boardTitle={state.board.title}
        pitchOrientation={state.board.pitch_orientation}
        frame={playback.activePair?.sourceFrame ?? activeFrame}
        renderItems={playbackRenderFrame?.items ?? []}
        status={playback.status}
        sourceFrameIndex={playback.sourceFrameIndex}
        targetFrameIndex={playback.targetFrameIndex}
        progress={playback.progress}
        onPlay={handlePlay}
        onPause={handlePause}
        onStop={handleStop}
        onClose={handleClosePresentation}
      />
    </div>
  );
};

export default TacticsBoardEditorPage;
