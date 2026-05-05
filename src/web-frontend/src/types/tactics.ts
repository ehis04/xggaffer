export type TacticsBoardType = 'static' | 'animated';
export type TacticsPitchOrientation = 'vertical' | 'horizontal';

export type TacticsItemType =
  | 'player'
  | 'ball'
  | 'arrow'
  | 'line'
  | 'zone'
  | 'text';

export type TacticsAnnotationItemType = Exclude<TacticsItemType, 'player'>;

export type TacticsTeamSide = 'home' | 'away' | 'neutral';
export type TacticsPlayerTeamSide = Extract<TacticsTeamSide, 'home' | 'away'>;
export type TacticsNeutralTeamSide = Extract<TacticsTeamSide, 'neutral'>;
export type TacticsDrawableTeamSide = TacticsTeamSide;

export type TacticsPointTool = 'ball' | 'text';
export type TacticsDirectionalTool = 'arrow' | 'line';
export type TacticsAreaTool = 'zone';
export type TacticsActiveTool = 'select' | TacticsAnnotationItemType;

export type TacticsPlaybackStatus = 'idle' | 'playing' | 'paused';

export type TacticsItemStyle = Record<string, unknown>;

export interface TacticsLinkedPlayerSummary {
  id: number;
  display_name: string;
  full_name: string;
  squad_number: number | null;
  primary_position: string;
  photo: string | null;
}

interface TacticsBoardItemBase {
  id: number;
  frame: number;
  stable_id: string;
  x: number;
  y: number;
  rotation: number;
  z_index: number;
  style: TacticsItemStyle;
}

export interface TacticsPlayerItem extends TacticsBoardItemBase {
  item_type: 'player';
  team_side: TacticsPlayerTeamSide;
  linked_player: number | null;
  label: string;
  shirt_number: number | null;
  position_label: string;
  end_x: null;
  end_y: null;
  width: null;
  height: null;
  player_summary: TacticsLinkedPlayerSummary | null;
}

export interface TacticsBallItem extends TacticsBoardItemBase {
  item_type: 'ball';
  team_side: TacticsNeutralTeamSide;
  linked_player: null;
  label: '';
  shirt_number: null;
  position_label: '';
  end_x: null;
  end_y: null;
  width: null;
  height: null;
  player_summary: null;
}

export interface TacticsArrowItem extends TacticsBoardItemBase {
  item_type: 'arrow';
  team_side: TacticsDrawableTeamSide;
  linked_player: null;
  label: string;
  shirt_number: null;
  position_label: '';
  end_x: number;
  end_y: number;
  width: null;
  height: null;
  player_summary: null;
}

export interface TacticsLineItem extends TacticsBoardItemBase {
  item_type: 'line';
  team_side: TacticsDrawableTeamSide;
  linked_player: null;
  label: '';
  shirt_number: null;
  position_label: '';
  end_x: number;
  end_y: number;
  width: null;
  height: null;
  player_summary: null;
}

export interface TacticsZoneItem extends TacticsBoardItemBase {
  item_type: 'zone';
  team_side: TacticsDrawableTeamSide;
  linked_player: null;
  label: '';
  shirt_number: null;
  position_label: '';
  end_x: null;
  end_y: null;
  width: number;
  height: number;
  player_summary: null;
}

export interface TacticsTextItem extends TacticsBoardItemBase {
  item_type: 'text';
  team_side: TacticsNeutralTeamSide;
  linked_player: null;
  label: string;
  shirt_number: null;
  position_label: '';
  end_x: null;
  end_y: null;
  width: null;
  height: null;
  player_summary: null;
}

export type TacticsBoardItem =
  | TacticsPlayerItem
  | TacticsBallItem
  | TacticsArrowItem
  | TacticsLineItem
  | TacticsZoneItem
  | TacticsTextItem;

export type TacticsNonPlayerItem = Exclude<TacticsBoardItem, TacticsPlayerItem>;

export interface TacticsBoardFrame {
  id: number;
  board: number;
  frame_index: number;
  label: string;
  duration_ms: number;
  notes: string;
  items: TacticsBoardItem[];
}

export interface TacticsBoard {
  id: number;
  club: number;
  created_by: number | null;
  title: string;
  description: string;
  board_type: TacticsBoardType;
  pitch_orientation: TacticsPitchOrientation;
  linked_teamsheet: number | null;
  home_formation: string;
  away_formation: string;
  home_colour: string;
  away_colour: string;
  is_template: boolean;
  is_trashed: boolean;
  trashed_at: string | null;
  trash_expires_at: string | null;
  trashed_by: number | null;
  created_at: string;
  updated_at: string;
  frames: TacticsBoardFrame[];
}

export type TacticsBoardListItem = Omit<TacticsBoard, 'frames'>;

export type TacticsBoardTrashMode = 'only' | 'include';

export interface TacticsBoardListOptions {
  trash?: TacticsBoardTrashMode;
}

export interface TacticsBoardGetOptions {
  trash?: TacticsBoardTrashMode;
}

export interface TacticsFrameOption {
  id: number;
  frame_index: number;
  label: string;
  duration_ms: number;
  notes: string;
  item_count: number;
}

export interface TacticsPlaybackFramePair {
  sourceFrame: TacticsBoardFrame;
  targetFrame: TacticsBoardFrame | null;
  sourceFrameIndex: number;
  targetFrameIndex: number | null;
}

export interface TacticsPlaybackSnapshot {
  status: TacticsPlaybackStatus;
  sourceFrameIndex: number;
  targetFrameIndex: number | null;
  progress: number;
}

interface TacticsRenderableItemMeta {
  render_key: string;
  source_item_id: number | null;
  target_item_id: number | null;
  opacity: number;
  is_interpolated: boolean;
}

export type TacticsRenderablePlayerItem =
  Omit<TacticsPlayerItem, 'id' | 'frame'> & TacticsRenderableItemMeta;

export type TacticsRenderableBallItem =
  Omit<TacticsBallItem, 'id' | 'frame'> & TacticsRenderableItemMeta;

export type TacticsRenderableArrowItem =
  Omit<TacticsArrowItem, 'id' | 'frame'> & TacticsRenderableItemMeta;

export type TacticsRenderableLineItem =
  Omit<TacticsLineItem, 'id' | 'frame'> & TacticsRenderableItemMeta;

export type TacticsRenderableZoneItem =
  Omit<TacticsZoneItem, 'id' | 'frame'> & TacticsRenderableItemMeta;

export type TacticsRenderableTextItem =
  Omit<TacticsTextItem, 'id' | 'frame'> & TacticsRenderableItemMeta;

export type TacticsRenderableItem =
  | TacticsRenderablePlayerItem
  | TacticsRenderableBallItem
  | TacticsRenderableArrowItem
  | TacticsRenderableLineItem
  | TacticsRenderableZoneItem
  | TacticsRenderableTextItem;

export interface TacticsRenderableFrame {
  frame_index: number;
  label: string;
  duration_ms: number;
  notes: string;
  items: TacticsRenderableItem[];
}

export interface CreateTacticsBoardPayload {
  title: string;
  description?: string;
  board_type?: TacticsBoardType;
  pitch_orientation?: TacticsPitchOrientation;
  linked_teamsheet?: number | null;
  home_formation?: string;
  away_formation?: string;
  home_colour?: string;
  away_colour?: string;
  is_template?: boolean;
}

export interface UpdateTacticsBoardPayload {
  title?: string;
  description?: string;
  pitch_orientation?: TacticsPitchOrientation;
  linked_teamsheet?: number | null;
  home_formation?: string;
  away_formation?: string;
  home_colour?: string;
  away_colour?: string;
  is_template?: boolean;
}

export interface CreateTacticsBoardFromTeamsheetPayload {
  teamsheet_id: number;
  title: string;
}

export interface AddOpponentFormationPayload {
  formation: string;
}

export interface DuplicateTacticsBoardPayload {
  title: string;
}

export interface CreateTacticsBoardFramePayload {
  label?: string;
  duration_ms?: number;
  notes?: string;
  copy_items_from_frame_index?: number;
}

export interface UpdateTacticsBoardFramePayload {
  label?: string;
  duration_ms?: number;
  notes?: string;
}

export type DuplicateTacticsBoardFramePayload = Record<string, never>;

interface CreateTacticsBoardItemBasePayload {
  x: number;
  y: number;
  rotation?: number;
  z_index?: number;
  style?: TacticsItemStyle;
}

export interface CreateTacticsPlayerItemPayload
  extends CreateTacticsBoardItemBasePayload {
  item_type: 'player';
  team_side: TacticsPlayerTeamSide;
  linked_player?: number | null;
  label?: string;
  shirt_number?: number | null;
  position_label?: string;
}

export interface CreateTacticsBallItemPayload
  extends CreateTacticsBoardItemBasePayload {
  item_type: 'ball';
  team_side: 'neutral';
}

export interface CreateTacticsArrowItemPayload
  extends CreateTacticsBoardItemBasePayload {
  item_type: 'arrow';
  team_side: TacticsDrawableTeamSide;
  end_x: number;
  end_y: number;
  label?: string;
}

export interface CreateTacticsLineItemPayload
  extends CreateTacticsBoardItemBasePayload {
  item_type: 'line';
  team_side: TacticsDrawableTeamSide;
  end_x: number;
  end_y: number;
}

export interface CreateTacticsZoneItemPayload
  extends CreateTacticsBoardItemBasePayload {
  item_type: 'zone';
  team_side: TacticsDrawableTeamSide;
  width: number;
  height: number;
}

export interface CreateTacticsTextItemPayload
  extends CreateTacticsBoardItemBasePayload {
  item_type: 'text';
  team_side: 'neutral';
  label: string;
}

export type CreateTacticsBoardItemPayload =
  | CreateTacticsPlayerItemPayload
  | CreateTacticsBallItemPayload
  | CreateTacticsArrowItemPayload
  | CreateTacticsLineItemPayload
  | CreateTacticsZoneItemPayload
  | CreateTacticsTextItemPayload;

export interface UpdateTacticsBoardItemPayload {
  item_type?: TacticsItemType;
  team_side?: TacticsTeamSide;
  linked_player?: number | null;
  label?: string;
  shirt_number?: number | null;
  position_label?: string;
  x?: number;
  y?: number;
  end_x?: number | null;
  end_y?: number | null;
  width?: number | null;
  height?: number | null;
  rotation?: number;
  z_index?: number;
  style?: TacticsItemStyle;
}

export interface TacticsItemPositionPatchPayload {
  x: number;
  y: number;
}

export interface TacticsPointDraft {
  tool: TacticsPointTool;
  startX: number;
  startY: number;
  label?: string;
}

export interface TacticsDirectionalDraft {
  tool: TacticsDirectionalTool;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  label?: string;
}

export interface TacticsZoneDraft {
  tool: 'zone';
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

export type TacticsDraftItem =
  | TacticsPointDraft
  | TacticsDirectionalDraft
  | TacticsZoneDraft;

export interface TacticsBoardEditorState {
  board: TacticsBoard | null;
  activeFrameIndex: number;
  selectedItemId: number | null;
  activeTool: TacticsActiveTool;
  draftItem: TacticsDraftItem | null;
  isDirty: boolean;
  isSaving: boolean;
  error: string | null;
  history: TacticsHistoryState;
}

export interface TacticsHistorySnapshot {
  board: TacticsBoard;
  activeFrameIndex: number;
  selectedItemId: number | null;
}

export interface TacticsHistoryState {
  past: TacticsHistorySnapshot[];
  future: TacticsHistorySnapshot[];
}

export type TacticsShortcutAction =
  | 'undo'
  | 'redo'
  | 'delete_selected_item'
  | 'cancel_draft_or_deselect'
  | 'save';

export type TacticsExportStatus = 'idle' | 'exporting' | 'error';

export interface TacticsExportState {
  status: TacticsExportStatus;
  error: string | null;
}