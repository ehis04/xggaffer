import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import useTacticsBoardEditor from '../useTacticsBoardEditor';
import type { TacticsBoard, TacticsBoardFrame, TacticsBoardItem } from '../../types/tactics';

const createPlayerItem = (overrides: Partial<TacticsBoardItem> = {}): TacticsBoardItem =>
  ({
    id: 101,
    frame: 11,
    item_type: 'player',
    team_side: 'home',
    stable_id: 'player-stable-id',
    linked_player: null,
    label: '',
    shirt_number: 8,
    position_label: 'CM',
    x: 50,
    y: 40,
    end_x: null,
    end_y: null,
    width: null,
    height: null,
    rotation: 0,
    z_index: 0,
    style: {},
    player_summary: null,
    ...overrides,
  }) as TacticsBoardItem;

const createBallItem = (overrides: Partial<TacticsBoardItem> = {}): TacticsBoardItem =>
  ({
    id: 201,
    frame: 11,
    item_type: 'ball',
    team_side: 'neutral',
    stable_id: 'ball-stable-id',
    linked_player: null,
    label: '',
    shirt_number: null,
    position_label: '',
    x: 52,
    y: 48,
    end_x: null,
    end_y: null,
    width: null,
    height: null,
    rotation: 0,
    z_index: 1,
    style: {},
    player_summary: null,
    ...overrides,
  }) as TacticsBoardItem;

const createFrame = (
  frameIndex: number,
  items: TacticsBoardItem[] = [],
  overrides: Partial<TacticsBoardFrame> = {}
): TacticsBoardFrame => ({
  id: 11 + frameIndex,
  board: 1,
  frame_index: frameIndex,
  label: '',
  duration_ms: 1500,
  notes: '',
  items,
  ...overrides,
});

const createBoard = (frames?: TacticsBoardFrame[]): TacticsBoard => ({
  id: 1,
  club: 9,
  created_by: 3,
  title: 'Phase E Test Board',
  description: 'Test board',
  board_type: frames && frames.length > 1 ? 'animated' : 'static',
  pitch_orientation: 'vertical',
  linked_teamsheet: null,
  home_formation: '433',
  away_formation: '',
  home_colour: '#1E40AF',
  away_colour: '#DC2626',
  is_template: false,
  is_trashed: false,
  trashed_at: null,
  trash_expires_at: null,
  trashed_by: null,
  created_at: '2026-04-13T10:00:00Z',
  updated_at: '2026-04-13T10:00:00Z',
  frames:
    frames ??
    [
      createFrame(0, [createPlayerItem()]),
    ],
});

describe('useTacticsBoardEditor', () => {
  it('loads a board and resolves frame 0 as the initial active frame', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([
      createFrame(2, [createPlayerItem({ frame: 13, id: 301 })]),
      createFrame(0, [createPlayerItem()]),
      createFrame(1, [createBallItem({ frame: 12, id: 202 })]),
    ]);

    act(() => {
      result.current.loadBoard(board);
    });

    expect(result.current.state.board?.id).toBe(1);
    expect(result.current.state.activeFrameIndex).toBe(0);
    expect(result.current.activeFrame?.frame_index).toBe(0);
    expect(result.current.state.selectedItemId).toBeNull();
    expect(result.current.state.activeTool).toBe('select');
    expect(result.current.state.draftItem).toBeNull();
    expect(result.current.state.isDirty).toBe(false);
  });

  it('falls back to the first available frame when frame 0 does not exist', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([
      createFrame(3, [createPlayerItem({ frame: 14, id: 401 })]),
      createFrame(1, [createBallItem({ frame: 12, id: 202 })]),
    ]);

    act(() => {
      result.current.loadBoard(board);
    });

    expect(result.current.state.activeFrameIndex).toBe(1);
    expect(result.current.activeFrame?.frame_index).toBe(1);
  });

  it('changes active tool and clears selected item when moving into a drawing tool', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([createFrame(0, [createPlayerItem()])]);

    act(() => {
      result.current.loadBoard(board);
      result.current.selectItem(101);
      result.current.setActiveTool('arrow');
    });

    expect(result.current.state.activeTool).toBe('arrow');
    expect(result.current.state.selectedItemId).toBeNull();
    expect(result.current.state.draftItem).toBeNull();
  });

  it('starts, updates, and clears a directional draft item', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());

    act(() => {
      result.current.startDraftItem({
        tool: 'arrow',
        startX: 10,
        startY: 20,
        currentX: 10,
        currentY: 20,
      });
    });

    expect(result.current.state.draftItem).toEqual({
      tool: 'arrow',
      startX: 10,
      startY: 20,
      currentX: 10,
      currentY: 20,
    });

    act(() => {
      result.current.updateDraftItem({
        tool: 'arrow',
        startX: 10,
        startY: 20,
        currentX: 35,
        currentY: 45,
      });
    });

    expect(result.current.state.draftItem).toEqual({
      tool: 'arrow',
      startX: 10,
      startY: 20,
      currentX: 35,
      currentY: 45,
    });

    act(() => {
      result.current.clearDraftItem();
    });

    expect(result.current.state.draftItem).toBeNull();
  });

  it('switches frames safely and clears selection on frame change', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([
      createFrame(0, [createPlayerItem({ id: 101, frame: 11 })]),
      createFrame(1, [createBallItem({ id: 201, frame: 12 })]),
    ]);

    act(() => {
      result.current.loadBoard(board);
      result.current.selectItem(101);
      result.current.setActiveFrameIndex(1);
    });

    expect(result.current.state.activeFrameIndex).toBe(1);
    expect(result.current.activeFrame?.frame_index).toBe(1);
    expect(result.current.state.selectedItemId).toBeNull();
    expect(result.current.selectedItem).toBeNull();
  });

  it('ignores invalid frame requests by resolving to a valid active frame', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([
      createFrame(0, [createPlayerItem({ id: 101, frame: 11 })]),
      createFrame(2, [createBallItem({ id: 202, frame: 13 })]),
    ]);

    act(() => {
      result.current.loadBoard(board);
      result.current.setActiveFrameIndex(99);
    });

    expect(result.current.state.activeFrameIndex).toBe(0);
    expect(result.current.activeFrame?.frame_index).toBe(0);
  });

  it('adds a created annotation locally and selects it', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([createFrame(0, [createPlayerItem()])]);
    const createdBall = createBallItem();

    act(() => {
      result.current.loadBoard(board);
      result.current.addItemLocal(11, createdBall, { selectAfterAdd: true });
    });

    expect(result.current.activeFrame?.items).toHaveLength(2);
    expect(result.current.state.selectedItemId).toBe(201);
    expect(result.current.selectedItem?.item_type).toBe('ball');
    expect(result.current.state.isDirty).toBe(true);
  });

  it('replaces an existing annotation locally after a PATCH response', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const originalBall = createBallItem({ rotation: 0 });
    const updatedBall = createBallItem({ rotation: 45, x: 60, y: 62 });
    const board = createBoard([createFrame(0, [originalBall])]);

    act(() => {
      result.current.loadBoard(board);
      result.current.selectItem(201);
      result.current.replaceItemLocal(11, updatedBall, { selectAfterReplace: true });
    });

    expect(result.current.selectedItem?.rotation).toBe(45);
    expect(result.current.selectedItem?.x).toBe(60);
    expect(result.current.selectedItem?.y).toBe(62);
  });

  it('deletes a selected annotation locally and clears selection', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([
      createFrame(0, [createPlayerItem(), createBallItem()]),
    ]);

    act(() => {
      result.current.loadBoard(board);
      result.current.selectItem(201);
      result.current.deleteItemLocal(11, 201);
    });

    expect(result.current.activeFrame?.items.map((item) => item.id)).toEqual([101]);
    expect(result.current.state.selectedItemId).toBeNull();
    expect(result.current.selectedItem).toBeNull();
  });

  it('keeps Phase C player movement dirty tracking intact', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([createFrame(0, [createPlayerItem()])]);

    act(() => {
      result.current.loadBoard(board);
      result.current.moveItemLocal(0, 101, 63, 71);
    });

    expect(result.current.selectedItem).toBeNull();
    expect(result.current.activeFrame?.items[0].x).toBe(63);
    expect(result.current.activeFrame?.items[0].y).toBe(71);
    expect(result.current.state.isDirty).toBe(true);
  });

  it('inserts a duplicated frame locally and makes it active predictably', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([
      createFrame(0, [createPlayerItem({ id: 101, frame: 11 })]),
      createFrame(2, [createBallItem({ id: 202, frame: 13 })]),
    ]);

    const duplicatedFrame = createFrame(
      1,
      [
        createPlayerItem({
          id: 301,
          frame: 12,
          stable_id: 'player-stable-id',
        }),
      ],
      { id: 12, label: 'Duplicated frame' }
    );

    act(() => {
      result.current.loadBoard(board);
      result.current.addFrameLocal(duplicatedFrame, { setActiveFrame: true });
    });

    expect(result.current.state.board?.frames.map((frame) => frame.frame_index)).toEqual([0, 1, 2]);
    expect(result.current.state.activeFrameIndex).toBe(1);
    expect(result.current.activeFrame?.id).toBe(12);
    expect(result.current.state.selectedItemId).toBeNull();
  });

  it('preserves selection when a non-active frame is inserted', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([
      createFrame(0, [createPlayerItem({ id: 101, frame: 11 })]),
      createFrame(2, [createBallItem({ id: 202, frame: 13 })]),
    ]);

    const insertedFrame = createFrame(1, [], { id: 12 });

    act(() => {
      result.current.loadBoard(board);
      result.current.selectItem(101);
      result.current.addFrameLocal(insertedFrame);
    });

    expect(result.current.state.activeFrameIndex).toBe(0);
    expect(result.current.state.selectedItemId).toBe(101);
    expect(result.current.selectedItem?.id).toBe(101);
  });

  it('guards active frame selection after a frame is deleted locally', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const board = createBoard([
      createFrame(0, [createPlayerItem({ id: 101, frame: 11 })]),
      createFrame(1, [createBallItem({ id: 201, frame: 12 })]),
      createFrame(2, [createBallItem({ id: 202, frame: 13 })]),
    ]);

    act(() => {
      result.current.loadBoard(board);
      result.current.setActiveFrameIndex(1);
      result.current.deleteFrameLocal(12);
    });

    expect(result.current.state.board?.frames.map((frame) => frame.frame_index)).toEqual([0, 2]);
    expect(result.current.state.activeFrameIndex).toBe(0);
    expect(result.current.activeFrame?.frame_index).toBe(0);
  });

  it('reconciles state on saveSucceeded with refreshed multi-frame board data', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const initialBoard = createBoard([
      createFrame(0, [createPlayerItem({ id: 101, frame: 11 })]),
      createFrame(1, [createBallItem({ id: 201, frame: 12 })]),
    ]);

    const refreshedBoard = createBoard([
      createFrame(0, [createPlayerItem({ id: 101, frame: 11, x: 77, y: 88 })]),
      createFrame(1, [
        createBallItem({ id: 201, frame: 12 }),
        createBallItem({ id: 202, frame: 12, stable_id: 'new-ball-stable-id' }),
      ]),
    ]);

    act(() => {
      result.current.loadBoard(initialBoard);
      result.current.setActiveFrameIndex(0);
      result.current.selectItem(101);
      result.current.saveSucceeded(refreshedBoard);
    });

    expect(result.current.state.isDirty).toBe(false);
    expect(result.current.state.error).toBeNull();
    expect(result.current.state.activeFrameIndex).toBe(0);
    expect(result.current.selectedItem?.id).toBe(101);
    expect(result.current.selectedItem?.x).toBe(77);
    expect(result.current.selectedItem?.y).toBe(88);
  });

  it('preserves stable_id continuity assumptions when a duplicated frame is inserted', () => {
    const { result } = renderHook(() => useTacticsBoardEditor());
    const sourceFrame = createFrame(0, [
      createPlayerItem({
        id: 101,
        frame: 11,
        stable_id: 'stable-player-1',
        x: 40,
        y: 55,
      }),
    ]);

    const duplicatedFrame = createFrame(
      1,
      [
        createPlayerItem({
          id: 301,
          frame: 12,
          stable_id: 'stable-player-1',
          x: 62,
          y: 71,
        }),
      ],
      { id: 12, label: 'Duplicated frame' }
    );

    act(() => {
      result.current.loadBoard(createBoard([sourceFrame]));
      result.current.addFrameLocal(duplicatedFrame, { setActiveFrame: true });
    });

    const frames = result.current.state.board?.frames ?? [];

    expect(frames).toHaveLength(2);
    expect(frames[0].frame_index).toBe(0);
    expect(frames[1].frame_index).toBe(1);

    expect(frames[0].items[0].stable_id).toBe('stable-player-1');
    expect(frames[1].items[0].stable_id).toBe('stable-player-1');

    expect(frames[0].items[0].id).toBe(101);
    expect(frames[1].items[0].id).toBe(301);

    expect(result.current.state.activeFrameIndex).toBe(1);
    expect(result.current.activeFrame?.items[0].stable_id).toBe('stable-player-1');
  });
});
