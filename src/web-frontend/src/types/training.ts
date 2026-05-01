export type TrainingSessionStatus = 'draft' | 'published' | 'completed' | 'cancelled';
export type TrainingSessionType =
  | 'technical'
  | 'tactical'
  | 'fitness'
  | 'set_pieces'
  | 'recovery'
  | 'match_preparation'
  | 'goalkeeper'
  | 'other';
export type TrainingIntensity = 'low' | 'medium' | 'high';
export type TrainingBlockType =
  | 'warm_up'
  | 'technical'
  | 'tactical'
  | 'conditioned_game'
  | 'set_pieces'
  | 'fitness'
  | 'recovery'
  | 'cool_down'
  | 'review'
  | 'other';
export type TrainingAttendanceStatus =
  | 'invited'
  | 'attended'
  | 'absent'
  | 'late'
  | 'excused'
  | 'injured'
  | 'not_selected';

export interface TrainingBlock {
  id: number;
  session: number;
  order: number;
  title: string;
  block_type: TrainingBlockType;
  duration_minutes: number;
  description: string;
  coaching_points: string;
  equipment: string;
  player_group: string;
  created_at: string;
  updated_at: string;
}

export interface TrainingSessionPlayer {
  id: number;
  session: number;
  club_player: number;
  player_name: string;
  squad_number: number | null;
  primary_position: string;
  is_active: boolean;
  attendance_status: TrainingAttendanceStatus;
  rpe_score: number | null;
  coach_notes: string;
  injury_note: string;
  performance_note: string;
  created_at: string;
  updated_at: string;
}

export interface TrainingSessionListItem {
  id: number;
  club: number;
  created_by: number | null;
  title: string;
  status: TrainingSessionStatus;
  status_display: string;
  session_type: TrainingSessionType;
  session_type_display: string;
  intensity: TrainingIntensity;
  intensity_display: string;
  start_datetime: string;
  end_datetime: string | null;
  location: string;
  is_mandatory: boolean;
  main_objective: string;
  linked_opponent: string;
  linked_teamsheet: number | null;
  assigned_player_count: number;
  attended_count: number;
  block_count: number;
  created_at: string;
  updated_at: string;
}

export interface TrainingSession extends TrainingSessionListItem {
  secondary_objectives: string;
  match_context: string;
  notes: string;
  what_went_well: string;
  needs_improvement: string;
  next_focus: string;
  squad_notes: string;
  calendar_event: number | null;
  blocks: TrainingBlock[];
  players: TrainingSessionPlayer[];
}

export type CreateTrainingSessionPayload = Partial<Omit<
  TrainingSession,
  | 'id'
  | 'club'
  | 'created_by'
  | 'status_display'
  | 'session_type_display'
  | 'intensity_display'
  | 'assigned_player_count'
  | 'attended_count'
  | 'block_count'
  | 'created_at'
  | 'updated_at'
  | 'calendar_event'
  | 'blocks'
  | 'players'
>>;

export type UpdateTrainingSessionPayload = CreateTrainingSessionPayload;

export type CreateTrainingBlockPayload = Omit<
  Partial<TrainingBlock>,
  'id' | 'session' | 'created_at' | 'updated_at'
> & {
  order: number;
  title: string;
  block_type: TrainingBlockType;
  duration_minutes: number;
};

export type UpdateTrainingBlockPayload = Partial<CreateTrainingBlockPayload>;

export interface AssignTrainingPlayersPayload {
  mode: 'all' | 'selected';
  club_player_ids?: number[];
}

export interface TrainingAttendanceUpdate {
  id?: number;
  club_player?: number;
  attendance_status: TrainingAttendanceStatus;
  rpe_score?: number | null;
  coach_notes?: string;
  injury_note?: string;
  performance_note?: string;
}

export interface TrainingSessionListParams {
  status?: TrainingSessionStatus;
  session_type?: TrainingSessionType;
  search?: string;
}
