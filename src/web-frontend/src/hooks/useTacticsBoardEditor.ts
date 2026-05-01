import { useMemo, useReducer } from 'react';
import type {
    TacticsActiveTool,
    TacticsBoard,
    TacticsBoardEditorState,
    TacticsBoardFrame,
    TacticsBoardItem,
    TacticsDraftItem,
    TacticsHistorySnapshot,
} from '../types/tactics';

type LoadBoardAction = {
    type: 'load_board';
    payload: TacticsBoard;
};

type SelectItemAction = {
    type: 'select_item';
    payload: number | null;
};

type SetActiveFrameAction = {
    type: 'set_active_frame';
    payload: number;
};

type SetActiveToolAction = {
    type: 'set_active_tool';
    payload: TacticsActiveTool;
};

type PushExplicitHistorySnapshotAction = {
    type: 'push_explicit_history_snapshot';
    payload: TacticsHistorySnapshot;
};

type ClearToolStateAction = {
    type: 'clear_tool_state';
};

type StartDraftItemAction = {
    type: 'start_draft_item';
    payload: TacticsDraftItem;
};

type UpdateDraftItemAction = {
    type: 'update_draft_item';
    payload: TacticsDraftItem;
};

type ClearDraftItemAction = {
    type: 'clear_draft_item';
};

type AddFrameLocalAction = {
    type: 'add_frame_local';
    payload: {
        frame: TacticsBoardFrame;
        setActiveFrame?: boolean;
    };
};

type ReplaceFrameLocalAction = {
    type: 'replace_frame_local';
    payload: {
        frame: TacticsBoardFrame;
        setActiveFrame?: boolean;
    };
};

type DeleteFrameLocalAction = {
    type: 'delete_frame_local';
    payload: {
        frameId: number;
        nextActiveFrameIndex?: number | null;
    };
};

type AddItemLocalAction = {
    type: 'add_item_local';
    payload: {
        frameId: number;
        item: TacticsBoardItem;
        selectAfterAdd?: boolean;
    };
};

type ReplaceItemLocalAction = {
    type: 'replace_item_local';
    payload: {
        frameId: number;
        item: TacticsBoardItem;
        selectAfterReplace?: boolean;
    };
};

type DeleteItemLocalAction = {
    type: 'delete_item_local';
    payload: {
        frameId: number;
        itemId: number;
    };
};

type MoveItemLocalAction = {
    type: 'move_item_local';
    payload: {
        frameIndex: number;
        itemId: number;
        x: number;
        y: number;
    };
};

type PushHistorySnapshotAction = {
    type: 'push_history_snapshot';
};

type UndoAction = {
    type: 'undo';
};

type RedoAction = {
    type: 'redo';
};

type ResetHistoryAction = {
    type: 'reset_history';
};

type SaveStartedAction = {
    type: 'save_started';
};

type SaveSucceededAction = {
    type: 'save_succeeded';
    payload?: TacticsBoard;
};

type SaveFailedAction = {
    type: 'save_failed';
    payload: string;
};

type ClearErrorAction = {
    type: 'clear_error';
};

type TacticsBoardEditorAction =
    | LoadBoardAction
    | SelectItemAction
    | SetActiveFrameAction
    | SetActiveToolAction
    | PushExplicitHistorySnapshotAction
    | ClearToolStateAction
    | StartDraftItemAction
    | UpdateDraftItemAction
    | ClearDraftItemAction
    | AddFrameLocalAction
    | ReplaceFrameLocalAction
    | DeleteFrameLocalAction
    | AddItemLocalAction
    | ReplaceItemLocalAction
    | DeleteItemLocalAction
    | MoveItemLocalAction
    | PushHistorySnapshotAction
    | UndoAction
    | RedoAction
    | ResetHistoryAction
    | SaveStartedAction
    | SaveSucceededAction
    | SaveFailedAction
    | ClearErrorAction;

const HISTORY_LIMIT = 50;

const initialState: TacticsBoardEditorState = {
    board: null,
    activeFrameIndex: 0,
    selectedItemId: null,
    activeTool: 'select',
    draftItem: null,
    isDirty: false,
    isSaving: false,
    error: null,
    history: {
        past: [],
        future: [],
    },
};

const sortFrames = (frames: TacticsBoardFrame[]): TacticsBoardFrame[] => {
    return [...frames].sort((left, right) => {
        if (left.frame_index !== right.frame_index) {
            return left.frame_index - right.frame_index;
        }

        return left.id - right.id;
    });
};

const sortItems = (items: TacticsBoardItem[]): TacticsBoardItem[] => {
    return [...items].sort((left, right) => {
        if (left.z_index !== right.z_index) {
            return left.z_index - right.z_index;
        }

        return left.id - right.id;
    });
};

const normaliseBoard = (board: TacticsBoard): TacticsBoard => {
    return {
        ...board,
        frames: sortFrames(
            board.frames.map((frame) => ({
                ...frame,
                items: sortItems(frame.items),
            }))
        ),
    };
};

const cloneItem = (item: TacticsBoardItem): TacticsBoardItem => {
    switch (item.item_type) {
        case 'player':
            return {
                ...item,
                style: { ...(item.style ?? {}) },
                player_summary: item.player_summary
                    ? { ...item.player_summary }
                    : null,
            };

        case 'ball':
        case 'arrow':
        case 'line':
        case 'zone':
        case 'text':
            return {
                ...item,
                style: { ...(item.style ?? {}) },
            };

        default:
            return item;
    }
};

const cloneBoard = (board: TacticsBoard): TacticsBoard => {
    return {
        ...board,
        frames: board.frames.map((frame) => ({
            ...frame,
            items: frame.items.map(cloneItem),
        })),
    };
};

const createHistorySnapshot = (
    board: TacticsBoard,
    activeFrameIndex: number,
    selectedItemId: number | null
): TacticsHistorySnapshot => {
    return {
        board: cloneBoard(board),
        activeFrameIndex,
        selectedItemId,
    };
};

const trimHistoryStack = <T,>(items: T[]): T[] => {
    if (items.length <= HISTORY_LIMIT) {
        return items;
    }

    return items.slice(items.length - HISTORY_LIMIT);
};

const resolveInitialFrameIndex = (board: TacticsBoard): number => {
    const frameZero = board.frames.find((frame) => frame.frame_index === 0);
    return frameZero ? frameZero.frame_index : (board.frames[0]?.frame_index ?? 0);
};

const resolveActiveFrameIndex = (
    board: TacticsBoard,
    requestedFrameIndex: number
): number => {
    const frameExists = board.frames.some(
        (frame) => frame.frame_index === requestedFrameIndex
    );

    return frameExists ? requestedFrameIndex : resolveInitialFrameIndex(board);
};

const resolveSelectedItemId = (
    board: TacticsBoard,
    activeFrameIndex: number,
    selectedItemId: number | null
): number | null => {
    if (selectedItemId === null) {
        return null;
    }

    const activeFrame = board.frames.find(
        (frame) => frame.frame_index === activeFrameIndex
    );

    if (!activeFrame) {
        return null;
    }

    return activeFrame.items.some((item) => item.id === selectedItemId)
        ? selectedItemId
        : null;
};

const updateItemPositionInBoard = (
    board: TacticsBoard,
    frameIndex: number,
    itemId: number,
    x: number,
    y: number
): TacticsBoard => {
    return {
        ...board,
        frames: board.frames.map((frame) => {
            if (frame.frame_index !== frameIndex) {
                return frame;
            }

            return {
                ...frame,
                items: frame.items.map((item) => {
                    if (item.id !== itemId) {
                        return item;
                    }

                    return {
                        ...item,
                        x,
                        y,
                    };
                }),
            };
        }),
    };
};

const upsertFrameInBoard = (
    board: TacticsBoard,
    frame: TacticsBoardFrame
): TacticsBoard => {
    const existingIndex = board.frames.findIndex(
        (existingFrame) => existingFrame.id === frame.id
    );

    const nextFrames =
        existingIndex === -1
            ? [...board.frames, { ...frame, items: sortItems(frame.items) }]
            : board.frames.map((existingFrame, index) =>
                index === existingIndex
                    ? { ...frame, items: sortItems(frame.items) }
                    : existingFrame
            );

    return {
        ...board,
        frames: sortFrames(nextFrames),
    };
};

const deleteFrameFromBoard = (
    board: TacticsBoard,
    frameId: number
): TacticsBoard => {
    return {
        ...board,
        frames: sortFrames(
            board.frames.filter((frame) => frame.id !== frameId)
        ),
    };
};

const addItemToFrameInBoard = (
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

const replaceItemInFrameInBoard = (
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

            const existingIndex = frame.items.findIndex(
                (existingItem) => existingItem.id === item.id
            );

            if (existingIndex === -1) {
                return {
                    ...frame,
                    items: sortItems([...frame.items, item]),
                };
            }

            const nextItems = [...frame.items];
            nextItems[existingIndex] = item;

            return {
                ...frame,
                items: sortItems(nextItems),
            };
        }),
    };
};

const deleteItemFromFrameInBoard = (
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

const tacticsBoardEditorReducer = (
    state: TacticsBoardEditorState,
    action: TacticsBoardEditorAction
): TacticsBoardEditorState => {
    switch (action.type) {
        case 'load_board': {
            const nextBoard = normaliseBoard(action.payload);

            return {
                board: nextBoard,
                activeFrameIndex: resolveInitialFrameIndex(nextBoard),
                selectedItemId: null,
                activeTool: 'select',
                draftItem: null,
                isDirty: false,
                isSaving: false,
                error: null,
                history: {
                    past: [],
                    future: [],
                },
            };
        }

        case 'select_item':
            return {
                ...state,
                selectedItemId: action.payload,
            };

        case 'set_active_frame': {
            if (!state.board) {
                return {
                    ...state,
                    activeFrameIndex: action.payload,
                    selectedItemId: null,
                    draftItem: null,
                };
            }

            const nextActiveFrameIndex = resolveActiveFrameIndex(
                state.board,
                action.payload
            );

            return {
                ...state,
                activeFrameIndex: nextActiveFrameIndex,
                selectedItemId: null,
                draftItem: null,
            };
        }

        case 'set_active_tool':
            return {
                ...state,
                activeTool: action.payload,
                draftItem: null,
                selectedItemId: action.payload === 'select' ? state.selectedItemId : null,
            };

        case 'clear_tool_state':
            return {
                ...state,
                activeTool: 'select',
                draftItem: null,
            };

        case 'push_explicit_history_snapshot':
            return {
                ...state,
                history: {
                    past: trimHistoryStack([
                        ...state.history.past,
                        {
                            board: normaliseBoard(action.payload.board),
                            activeFrameIndex: action.payload.activeFrameIndex,
                            selectedItemId: action.payload.selectedItemId,
                        },
                    ]),
                    future: [],
                },
            };

        case 'start_draft_item':
            return {
                ...state,
                draftItem: action.payload,
                selectedItemId: null,
                error: null,
            };

        case 'update_draft_item':
            return {
                ...state,
                draftItem: action.payload,
            };

        case 'clear_draft_item':
            return {
                ...state,
                draftItem: null,
            };

        case 'add_frame_local': {
            if (!state.board) {
                return state;
            }

            const nextBoard = upsertFrameInBoard(state.board, action.payload.frame);
            const requestedFrameIndex = action.payload.setActiveFrame
                ? action.payload.frame.frame_index
                : state.activeFrameIndex;
            const nextActiveFrameIndex = resolveActiveFrameIndex(
                nextBoard,
                requestedFrameIndex
            );
            const nextSelectedItemId =
                nextActiveFrameIndex === state.activeFrameIndex && !action.payload.setActiveFrame
                    ? resolveSelectedItemId(
                        nextBoard,
                        nextActiveFrameIndex,
                        state.selectedItemId
                    )
                    : null;

            return {
                ...state,
                board: nextBoard,
                activeFrameIndex: nextActiveFrameIndex,
                selectedItemId: nextSelectedItemId,
                draftItem: null,
                isDirty: true,
                error: null,
            };
        }

        case 'replace_frame_local': {
            if (!state.board) {
                return state;
            }

            const nextBoard = upsertFrameInBoard(state.board, action.payload.frame);
            const requestedFrameIndex = action.payload.setActiveFrame
                ? action.payload.frame.frame_index
                : state.activeFrameIndex;
            const nextActiveFrameIndex = resolveActiveFrameIndex(
                nextBoard,
                requestedFrameIndex
            );

            return {
                ...state,
                board: nextBoard,
                activeFrameIndex: nextActiveFrameIndex,
                selectedItemId: resolveSelectedItemId(
                    nextBoard,
                    nextActiveFrameIndex,
                    action.payload.setActiveFrame ? null : state.selectedItemId
                ),
                draftItem: null,
                isDirty: true,
                error: null,
            };
        }

        case 'delete_frame_local': {
            if (!state.board) {
                return state;
            }

            const nextBoard = deleteFrameFromBoard(state.board, action.payload.frameId);

            if (nextBoard.frames.length === 0) {
                return {
                    ...state,
                    board: nextBoard,
                    activeFrameIndex: 0,
                    selectedItemId: null,
                    draftItem: null,
                    isDirty: true,
                    error: null,
                };
            }

            const requestedFrameIndex =
                action.payload.nextActiveFrameIndex ?? state.activeFrameIndex;
            const nextActiveFrameIndex = resolveActiveFrameIndex(
                nextBoard,
                requestedFrameIndex
            );

            return {
                ...state,
                board: nextBoard,
                activeFrameIndex: nextActiveFrameIndex,
                selectedItemId: resolveSelectedItemId(
                    nextBoard,
                    nextActiveFrameIndex,
                    state.selectedItemId
                ),
                draftItem: null,
                isDirty: true,
                error: null,
            };
        }

        case 'add_item_local':
            if (!state.board) {
                return state;
            }

            return {
                ...state,
                board: addItemToFrameInBoard(
                    state.board,
                    action.payload.frameId,
                    action.payload.item
                ),
                selectedItemId:
                    action.payload.selectAfterAdd === false
                        ? state.selectedItemId
                        : action.payload.item.id,
                draftItem: null,
                isDirty: true,
                error: null,
            };

        case 'replace_item_local':
            if (!state.board) {
                return state;
            }

            return {
                ...state,
                board: replaceItemInFrameInBoard(
                    state.board,
                    action.payload.frameId,
                    action.payload.item
                ),
                selectedItemId:
                    action.payload.selectAfterReplace === true
                        ? action.payload.item.id
                        : state.selectedItemId === action.payload.item.id
                            ? action.payload.item.id
                            : state.selectedItemId,
                isDirty: true,
                error: null,
            };

        case 'delete_item_local':
            if (!state.board) {
                return state;
            }

            return {
                ...state,
                board: deleteItemFromFrameInBoard(
                    state.board,
                    action.payload.frameId,
                    action.payload.itemId
                ),
                selectedItemId:
                    state.selectedItemId === action.payload.itemId
                        ? null
                        : state.selectedItemId,
                draftItem: null,
                isDirty: true,
                error: null,
            };

        case 'move_item_local':
            if (!state.board) {
                return state;
            }

            return {
                ...state,
                board: updateItemPositionInBoard(
                    state.board,
                    action.payload.frameIndex,
                    action.payload.itemId,
                    action.payload.x,
                    action.payload.y
                ),
                isDirty: true,
            };

        case 'push_history_snapshot': {
            if (!state.board) {
                return state;
            }

            return {
                ...state,
                history: {
                    past: trimHistoryStack([
                        ...state.history.past,
                        createHistorySnapshot(
                            state.board,
                            state.activeFrameIndex,
                            state.selectedItemId
                        ),
                    ]),
                    future: [],
                },
            };
        }

        case 'undo': {
            if (!state.board || state.history.past.length === 0) {
                return state;
            }

            const previousSnapshot = state.history.past[state.history.past.length - 1];
            const remainingPast = state.history.past.slice(0, -1);
            const nextBoard = normaliseBoard(previousSnapshot.board);
            const nextActiveFrameIndex = resolveActiveFrameIndex(
                nextBoard,
                previousSnapshot.activeFrameIndex
            );

            return {
                ...state,
                board: nextBoard,
                activeFrameIndex: nextActiveFrameIndex,
                selectedItemId: resolveSelectedItemId(
                    nextBoard,
                    nextActiveFrameIndex,
                    previousSnapshot.selectedItemId
                ),
                draftItem: null,
                isDirty: true,
                isSaving: false,
                error: null,
                history: {
                    past: remainingPast,
                    future: [
                        createHistorySnapshot(
                            state.board,
                            state.activeFrameIndex,
                            state.selectedItemId
                        ),
                        ...state.history.future,
                    ],
                },
            };
        }

        case 'redo': {
            if (!state.board || state.history.future.length === 0) {
                return state;
            }

            const nextSnapshot = state.history.future[0];
            const remainingFuture = state.history.future.slice(1);
            const nextBoard = normaliseBoard(nextSnapshot.board);
            const nextActiveFrameIndex = resolveActiveFrameIndex(
                nextBoard,
                nextSnapshot.activeFrameIndex
            );

            return {
                ...state,
                board: nextBoard,
                activeFrameIndex: nextActiveFrameIndex,
                selectedItemId: resolveSelectedItemId(
                    nextBoard,
                    nextActiveFrameIndex,
                    nextSnapshot.selectedItemId
                ),
                draftItem: null,
                isDirty: true,
                isSaving: false,
                error: null,
                history: {
                    past: trimHistoryStack([
                        ...state.history.past,
                        createHistorySnapshot(
                            state.board,
                            state.activeFrameIndex,
                            state.selectedItemId
                        ),
                    ]),
                    future: remainingFuture,
                },
            };
        }

        case 'reset_history':
            return {
                ...state,
                history: {
                    past: [],
                    future: [],
                },
            };

        case 'save_started':
            return {
                ...state,
                isSaving: true,
                error: null,
            };

        case 'save_succeeded': {
            if (!action.payload) {
                return {
                    ...state,
                    isDirty: false,
                    isSaving: false,
                    error: null,
                    draftItem: null,
                };
            }

            const nextBoard = normaliseBoard(action.payload);
            const nextActiveFrameIndex = resolveActiveFrameIndex(
                nextBoard,
                state.activeFrameIndex
            );

            return {
                ...state,
                board: nextBoard,
                activeFrameIndex: nextActiveFrameIndex,
                selectedItemId: resolveSelectedItemId(
                    nextBoard,
                    nextActiveFrameIndex,
                    state.selectedItemId
                ),
                draftItem: null,
                isDirty: false,
                isSaving: false,
                error: null,
                history: {
                    past: [],
                    future: [],
                },
            };
        }

        case 'save_failed':
            return {
                ...state,
                isSaving: false,
                error: action.payload,
            };

        case 'clear_error':
            return {
                ...state,
                error: null,
            };

        default:
            return state;
    }
};

export const useTacticsBoardEditor = () => {
    const [state, dispatch] = useReducer(tacticsBoardEditorReducer, initialState);

    const activeFrame: TacticsBoardFrame | null = useMemo(() => {
        if (!state.board) {
            return null;
        }

        return (
            state.board.frames.find(
                (frame) => frame.frame_index === state.activeFrameIndex
            ) ?? null
        );
    }, [state.activeFrameIndex, state.board]);

    const selectedItem: TacticsBoardItem | null = useMemo(() => {
        if (!activeFrame || state.selectedItemId === null) {
            return null;
        }

        return activeFrame.items.find((item) => item.id === state.selectedItemId) ?? null;
    }, [activeFrame, state.selectedItemId]);

    return {
        state,
        activeFrame,
        selectedItem,
        loadBoard: (board: TacticsBoard) =>
            dispatch({ type: 'load_board', payload: board }),
        selectItem: (itemId: number | null) =>
            dispatch({ type: 'select_item', payload: itemId }),
        setActiveFrameIndex: (frameIndex: number) =>
            dispatch({ type: 'set_active_frame', payload: frameIndex }),
        setActiveTool: (tool: TacticsActiveTool) =>
            dispatch({ type: 'set_active_tool', payload: tool }),
        clearToolState: () =>
            dispatch({ type: 'clear_tool_state' }),
        startDraftItem: (draftItem: TacticsDraftItem) =>
            dispatch({ type: 'start_draft_item', payload: draftItem }),
        updateDraftItem: (draftItem: TacticsDraftItem) =>
            dispatch({ type: 'update_draft_item', payload: draftItem }),
        clearDraftItem: () =>
            dispatch({ type: 'clear_draft_item' }),
        addFrameLocal: (
            frame: TacticsBoardFrame,
            options?: { setActiveFrame?: boolean }
        ) =>
            dispatch({
                type: 'add_frame_local',
                payload: {
                    frame,
                    setActiveFrame: options?.setActiveFrame,
                },
            }),
        replaceFrameLocal: (
            frame: TacticsBoardFrame,
            options?: { setActiveFrame?: boolean }
        ) =>
            dispatch({
                type: 'replace_frame_local',
                payload: {
                    frame,
                    setActiveFrame: options?.setActiveFrame,
                },
            }),
        deleteFrameLocal: (
            frameId: number,
            options?: { nextActiveFrameIndex?: number | null }
        ) =>
            dispatch({
                type: 'delete_frame_local',
                payload: {
                    frameId,
                    nextActiveFrameIndex: options?.nextActiveFrameIndex,
                },
            }),
        addItemLocal: (
            frameId: number,
            item: TacticsBoardItem,
            options?: { selectAfterAdd?: boolean }
        ) =>
            dispatch({
                type: 'add_item_local',
                payload: {
                    frameId,
                    item,
                    selectAfterAdd: options?.selectAfterAdd,
                },
            }),
        replaceItemLocal: (
            frameId: number,
            item: TacticsBoardItem,
            options?: { selectAfterReplace?: boolean }
        ) =>
            dispatch({
                type: 'replace_item_local',
                payload: {
                    frameId,
                    item,
                    selectAfterReplace: options?.selectAfterReplace,
                },
            }),
        deleteItemLocal: (frameId: number, itemId: number) =>
            dispatch({
                type: 'delete_item_local',
                payload: { frameId, itemId },
            }),
        moveItemLocal: (
            frameIndex: number,
            itemId: number,
            x: number,
            y: number
        ) =>
            dispatch({
                type: 'move_item_local',
                payload: { frameIndex, itemId, x, y },
            }),
        pushHistorySnapshot: (snapshot?: TacticsHistorySnapshot) =>
            dispatch(
                snapshot
                    ? { type: 'push_explicit_history_snapshot', payload: snapshot }
                    : { type: 'push_history_snapshot' }
            ),
        undo: () => dispatch({ type: 'undo' }),
        redo: () => dispatch({ type: 'redo' }),
        resetHistory: () => dispatch({ type: 'reset_history' }),
        saveStarted: () => dispatch({ type: 'save_started' }),
        saveSucceeded: (board?: TacticsBoard) =>
            dispatch({ type: 'save_succeeded', payload: board }),
        saveFailed: (message: string) =>
            dispatch({ type: 'save_failed', payload: message }),
        clearError: () => dispatch({ type: 'clear_error' }),
        canUndo: state.history.past.length > 0,
        canRedo: state.history.future.length > 0,
    };
};

export default useTacticsBoardEditor;