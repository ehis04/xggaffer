import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TacticsBoardEditorPage from '../TacticsBoardEditorPage';

const mockNavigate = vi.fn();
const mockGetBoard = vi.fn();
const mockSaveItemPosition = vi.fn();

const mockEditorHook = vi.fn();
const mockPlaybackHook = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useParams: () => ({ clubId: '1', boardId: '10' }),
}));

vi.mock('../../../../hooks/useTacticsBoardEditor', () => ({
  default: (...args: unknown[]) => mockEditorHook(...args),
}));

vi.mock('../../../../hooks/usePlayback', () => ({
  default: (...args: unknown[]) => mockPlaybackHook(...args),
}));

vi.mock('../../../../services/api', () => ({
  tacticsBoardApi: {
    getBoard: (...args: unknown[]) => mockGetBoard(...args),
  },
  tacticsFrameApi: {
    createFrame: vi.fn(),
    duplicateFrame: vi.fn(),
    deleteFrame: vi.fn(),
  },
  tacticsItemApi: {
    createItem: vi.fn(),
    patchItemProperties: vi.fn(),
    deleteItem: vi.fn(),
    saveItemPosition: (...args: unknown[]) => mockSaveItemPosition(...args),
  },
}));

vi.mock('../../../../components/tactics/BoardSidebar', () => ({
  default: () => <div data-testid="board-sidebar">Sidebar</div>,
}));

vi.mock('../../../../components/tactics/ToolPalette', () => ({
  default: () => <div data-testid="tool-palette">Tool palette</div>,
}));

vi.mock('../../../../components/tactics/PlaybackOverlay', () => ({
  default: () => null,
}));

vi.mock('../../../../components/tactics/BoardToolbar', () => ({
  default: (props: any) => (
    <div data-testid="board-toolbar">
      <div>{props.title}</div>
      <button type="button" onClick={props.onSave} disabled={!props.canSave}>
        Save Changes
      </button>
    </div>
  ),
}));

vi.mock('../../../../components/tactics/FrameList', () => ({
  default: (props: any) => (
    <div data-testid="frame-list">
      <div>Active frame: {props.activeFrameIndex}</div>
      {props.frames.map((frame: any) => (
        <button
          key={frame.id}
          type="button"
          onClick={() => props.onSelectFrame(frame.frame_index)}
        >
          Select frame {frame.frame_index}
        </button>
      ))}
    </div>
  ),
}));

vi.mock('../../../../components/tactics/PitchCanvas', () => ({
  default: (props: any) => {
    const firstItem = props.frame.items[0];

    return (
      <div data-testid="pitch-canvas">
        <div>Frame index: {props.frame.frame_index}</div>
        <div>Item count: {props.frame.items.length}</div>
        <div>First label: {firstItem?.label || firstItem?.position_label || 'none'}</div>
        {props.onMoveItem && firstItem ? (
          <button
            type="button"
            onClick={() => props.onMoveItem(firstItem.id, 63, 71)}
          >
            Move first item
          </button>
        ) : null}
      </div>
    );
  },
}));

const board = {
  id: 10,
  club: 1,
  created_by: 3,
  title: 'Phase E Board',
  description: 'Regression board',
  board_type: 'animated',
  pitch_orientation: 'vertical',
  linked_teamsheet: null,
  home_formation: '433',
  away_formation: '',
  home_colour: '#1E40AF',
  away_colour: '#DC2626',
  is_template: false,
  created_at: '2026-04-13T10:00:00Z',
  updated_at: '2026-04-13T10:00:00Z',
  frames: [
    {
      id: 11,
      board: 10,
      frame_index: 0,
      label: 'Frame 0',
      duration_ms: 1500,
      notes: '',
      items: [
        {
          id: 101,
          frame: 11,
          item_type: 'player',
          team_side: 'home',
          stable_id: 'stable-player-1',
          linked_player: null,
          label: 'Frame Zero Player',
          shirt_number: 8,
          position_label: 'CM',
          x: 63,
          y: 71,
          end_x: null,
          end_y: null,
          width: null,
          height: null,
          rotation: 0,
          z_index: 0,
          style: {},
          player_summary: null,
        },
      ],
    },
    {
      id: 12,
      board: 10,
      frame_index: 1,
      label: 'Frame 1',
      duration_ms: 1500,
      notes: '',
      items: [
        {
          id: 201,
          frame: 12,
          item_type: 'text',
          team_side: 'neutral',
          stable_id: 'stable-text-1',
          linked_player: null,
          label: 'Frame One Text',
          shirt_number: null,
          position_label: '',
          x: 25,
          y: 30,
          end_x: null,
          end_y: null,
          width: null,
          height: null,
          rotation: 0,
          z_index: 1,
          style: {},
          player_summary: null,
        },
      ],
    },
  ],
};

const persistedBoard = {
  ...board,
  frames: [
    {
      ...board.frames[0],
      items: [
        {
          ...board.frames[0].items[0],
          x: 50,
          y: 40,
        },
      ],
    },
    board.frames[1],
  ],
};

const makeEditorState = (isDirty = true) => ({
  state: {
    board,
    activeFrameIndex: 0,
    selectedItemId: null,
    draftItem: null,
    isDirty,
    isSaving: false,
    error: null,
  },
  activeFrame: board.frames[0],
  selectedItem: null,
  loadBoard: vi.fn(),
  selectItem: vi.fn(),
  setActiveFrameIndex: vi.fn(),
  setActiveTool: vi.fn(),
  startDraftItem: vi.fn(),
  updateDraftItem: vi.fn(),
  clearDraftItem: vi.fn(),
  addFrameLocal: vi.fn(),
  deleteFrameLocal: vi.fn(),
  addItemLocal: vi.fn(),
  replaceItemLocal: vi.fn(),
  deleteItemLocal: vi.fn(),
  moveItemLocal: vi.fn(),
  saveStarted: vi.fn(),
  saveSucceeded: vi.fn(),
  saveFailed: vi.fn(),
  clearError: vi.fn(),
});

const makePlaybackState = () => ({
  status: 'idle',
  canPlay: false,
  currentFrameIndex: 0,
  targetFrameIndex: 1,
  progress: 0,
  activePair: null,
  play: vi.fn(),
  pause: vi.fn(),
  stop: vi.fn(),
  reset: vi.fn(),
});

describe('TacticsBoardEditorPage regressions', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockGetBoard.mockReset();
    mockSaveItemPosition.mockReset();
    mockEditorHook.mockReset();
    mockPlaybackHook.mockReset();

    mockGetBoard.mockResolvedValue(persistedBoard);
    mockSaveItemPosition.mockResolvedValue(board.frames[0].items[0]);
    mockEditorHook.mockReturnValue(makeEditorState());
    mockPlaybackHook.mockReturnValue(makePlaybackState());
  });

  it('calls frame selection handler when switching frames', async () => {
    const editorState = makeEditorState(false);
    mockEditorHook.mockReturnValue(editorState);

    render(<TacticsBoardEditorPage />);

    expect(await screen.findByText('Frame index: 0')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Select frame 1' }));

    expect(editorState.setActiveFrameIndex).toHaveBeenCalledWith(1);
  });

  it('saves moved item positions for dirty boards', async () => {
    render(<TacticsBoardEditorPage />);

    expect(await screen.findByText('Frame index: 0')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Move first item' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }));

    await waitFor(() => {
      expect(mockSaveItemPosition).toHaveBeenCalledWith(
        1,
        10,
        11,
        101,
        { x: 63, y: 71 }
      );
    });
  });
});
