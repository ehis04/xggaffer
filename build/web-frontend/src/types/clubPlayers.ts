export interface ClubPlayer {
  id: number;
  club: number;
  club_name?: string;
  player?: number | null;
  player_id?: number | null;
  user?: number | null;

  first_name: string;
  last_name: string;
  full_name: string;
  display_name: string;
  squad_number: number | null;
  primary_position: string;
  secondary_positions: string[];
  preferred_foot: string;
  date_of_birth: string | null;
  nationality?: string;
  height_cm: number | null;
  photo?: string | null;
  profile_image?: string | null;

  is_active: boolean;
  is_claimed?: boolean;
  is_public: boolean;

  is_linked_to_player?: boolean;
  canonical_player_id?: number | null;
  canonical_display_name?: string | null;
  canonical_primary_position?: string | null;

  has_provider_identity?: boolean;
  provider_sources?: string[];
  last_synced_at?: string | null;

  created_at: string;
  updated_at: string;
}

export type ClubPlayerListItem = ClubPlayer;

export interface CreateClubPlayerPayload {
  first_name: string;
  last_name: string;
  display_name?: string;
  squad_number?: number | null;
  primary_position?: string;
  secondary_positions?: string[];
  preferred_foot?: string;
  date_of_birth?: string | null;
  nationality?: string;
  height_cm?: number | null;
  photo?: string | null;
  profile_image?: string | null;
  is_public?: boolean;
  canonical_player_id?: number | null;
}

export interface UpdateClubPlayerPayload extends CreateClubPlayerPayload {
  is_active?: boolean;
}

export interface LinkClubPlayerPayload {
  canonical_player_id: number;
}

export type UnlinkClubPlayerPayload = Record<string, never>;

export interface RelinkClubPlayerPayload {
  canonical_player_id: number;
}