export interface TeamsheetPlayer {
  id: number;
  slot_number: number;
  is_substitute: boolean;
  player_profile: number | null;
  player_profile_name: string | null;
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

export interface Club {
  id: number;
  name: string;
  description: string;
  badge: string | null;
  creator: number;
  creator_username: string;
  visibility: string;
  city: string;
  country: string;
  stadium: string;
  division: string;
  member_count: number;
  player_count: number;
}

export interface AvailablePlayer {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  display_name: string | null;
  squad_number: number | null;
  position: string;
  photo: string | null;
  club: number;
  is_public: boolean;
  source_type: 'club_member' | 'public' | 'unknown';
}

export interface PlayerSlotAssignment {
  slot_number: number;
  player_profile_id?: number | null;
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
  CB: 'DEF',
  RB: 'DEF',
  LB: 'DEF',
  RWB: 'DEF',
  LWB: 'DEF',
  CDM: 'MID',
  CM: 'MID',
  CAM: 'MID',
  RM: 'MID',
  LM: 'MID',
  RW: 'FWD',
  LW: 'FWD',
  CF: 'FWD',
  ST: 'FWD',
};

export const getPositionGroup = (position: string): PositionGroup => {
  return POSITION_GROUPS[position] || 'MID';
};