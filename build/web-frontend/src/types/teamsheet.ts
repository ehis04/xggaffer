import type { Club } from './club';
export type { Club };

export interface TeamsheetPlayer {
  id: number;
  slot_number: number;
  is_substitute: boolean;
  club_player: number | null;
  club_player_name: string | null;
  custom_name: string;
  custom_number: number | null;
  display_name: string;
  display_number: number | null;
  display_photo_url: string | null;
  is_linked: boolean;
  position_label: string;
  position_x: number;
  position_y: number;
  created_at: string;
  updated_at: string;
}

export interface Teamsheet {
  id: number;
  title: string;
  club: number;
  club_name: string;
  created_by: number | null;
  created_by_username: string | null;
  formation: string;
  formation_display: string;
  match_date: string | null;
  opponent: string;
  notes: string;
  is_template: boolean;
  is_complete: boolean;
  starter_count: number;
  substitute_count: number;
  players: TeamsheetPlayer[];
  created_at: string;
  updated_at: string;
}

export interface TeamsheetListItem {
  id: number;
  title: string;
  club: number;
  club_name: string;
  formation: string;
  formation_display: string;
  match_date: string | null;
  opponent: string;
  is_template: boolean;
  is_complete: boolean;
  starter_count: number;
  updated_at: string;
}

export interface PositionChoice {
  value: string;
  label: string;
}

export interface FormationChoice {
  value: string;
  label: string;
}

export interface FormationPosition {
  slot: number;
  position: string;
  x: number;
  y: number;
}

export interface FormationWithTemplate {
  value: string;
  label: string;
  positions: FormationPosition[];
}

export interface TeamsheetChoices {
  positions: PositionChoice[];
  formations: FormationChoice[];
  formations_with_templates: FormationWithTemplate[];
}

export interface PlayerPositionUpdate {
  id: number;
  position_x: number;
  position_y: number;
  position_label?: string;
}

export interface BulkPositionUpdate {
  updates: PlayerPositionUpdate[];
}

export interface AvailablePlayer {
  // This id is the ClubPlayer id, not the canonical Player id.
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  display_name: string | null;
  squad_number: number | null;
  primary_position: string;
  photo: string | null;
  club: number;
  is_public: boolean;
  source_type: 'club_member' | 'public' | 'unknown';
}

export interface PlayerSlotAssignment {
  slot_number: number;
  club_player_id?: number | null;
  custom_name?: string;
  custom_number?: number | null;
  position_label: string;
  position_x: number;
  position_y: number;
  is_substitute: boolean;
}

export interface CreateTeamsheetPayload {
  title: string;
  formation: string;
  match_date?: string | null;
  opponent?: string;
  notes?: string;
  is_template?: boolean;
  player_assignments?: PlayerSlotAssignment[];
}

export interface SlotState {
  slot_number: number;
  position_label: string;
  position_x: number;
  position_y: number;
  is_substitute: boolean;
  player?: AvailablePlayer | null;
  custom_name?: string;
  custom_number?: number | null;
}

export type PositionGroup = 'GK' | 'DEF' | 'MID' | 'FWD';

export const POSITION_GROUPS: Record<string, PositionGroup> = {
  GK: 'GK',

  RB: 'DEF',
  RWB: 'DEF',
  CB: 'DEF',
  RCB: 'DEF',
  CCB: 'DEF',
  LCB: 'DEF',
  LB: 'DEF',
  LWB: 'DEF',

  RDM: 'MID',
  CDM: 'MID',
  LDM: 'MID',
  CM: 'MID',
  RM: 'MID',
  LM: 'MID',
  RAM: 'MID',
  CAM: 'MID',
  LAM: 'MID',

  RW: 'FWD',
  LW: 'FWD',
  CF: 'FWD',
  ST: 'FWD',
};

export const getPositionGroup = (position: string): PositionGroup => {
  return POSITION_GROUPS[position] || 'MID';
};