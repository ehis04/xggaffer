export type ClubVisibility = 'public' | 'private';

export type ClubType =
  | 'system_professional'
  | 'user_real_non_pro'
  | 'user_fictional';

export type FictionalBasis =
  | 'original'
  | 'real_club_copy';

export type DirectoryVisibility =
  | 'listed'
  | 'hidden_code_only';

export type JoinPolicy =
  | 'approval_required'
  | 'invite_only'
  | 'system_managed';

export type VerificationStatus =
  | 'not_required'
  | 'pending'
  | 'approved'
  | 'rejected';

export type ClubListScope = 'mine' | 'browse';

export type ClubJoinRequestStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'withdrawn'
  | 'cancelled';

export type ClubInvitationStatus =
  | 'pending'
  | 'accepted'
  | 'declined'
  | 'revoked'
  | 'expired';

export type ClubMembershipRole =
  | 'owner'
  | 'admin'
  | 'coach'
  | 'player'
  | 'viewer';

export interface ClubUnderstatSummary {
  provider: 'understat';
  season_label: string;
  competition_code: string;
  competition_name: string;
  matches_played: number;
  xg: string | null;
  xga: string | null;
  npxg: string | null;
  last_synced_at: string | null;
}

export interface ClubUnderstatSeasonSummaryResponse {
  club_id: number;
  provider: 'understat';
  season_label: string;
  competition_code: string;
  competition_name: string;
  matches_played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  xg: string | null;
  xga: string | null;
  npxg: string | null;
  ppda: string | null;
  last_synced_at: string | null;
}

export type ClubTrashMode = 'only' | 'include';

export interface Club {
  id: number;
  name: string;
  description: string;
  badge: string | null;
  creator: number;
  creator_username: string;
  visibility: ClubVisibility;

  club_type: ClubType | null;
  fictional_basis: FictionalBasis | null;
  source_real_club_name: string;
  directory_visibility: DirectoryVisibility | null;
  join_policy: JoinPolicy | null;
  join_code: string | null;
  verification_status: VerificationStatus | null;

  city: string;
  country: string;
  stadium: string;
  division: string;
  achievements: string;
  member_count: number;
  player_count: number;
  latest_understat_summary?: ClubUnderstatSummary | null;
  is_trashed: boolean;
  trashed_at: string | null;
  trash_expires_at: string | null;
  trashed_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface ClubJoinRequest {
  id: number;
  club: number;
  club_name: string;
  user: number;
  user_email: string;
  requested_role: ClubMembershipRole;
  message: string;
  status: ClubJoinRequestStatus;
  reviewed_by: number | null;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  review_note: string;
  selected_club_player: number | null;
  selected_club_player_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClubInvitation {
  id: number;
  club: number;
  club_name: string;
  invited_user: number;
  invited_user_email: string;
  invited_by: number | null;
  invited_by_email: string | null;
  invited_role: ClubMembershipRole;
  note: string;
  status: ClubInvitationStatus;
  responded_at: string | null;
  response_note: string;
  created_at: string;
  updated_at: string;
}

export interface ClubListParams {
  scope?: ClubListScope;
  search?: string;
  trash?: ClubTrashMode;
}

export type TrashSection = 'all' | 'clubs' | 'teamsheets' | 'tactics';

export interface TrashListParams {
  section?: TrashSection;
}

export interface TrashListItem {
  id: number;
  section: Exclude<TrashSection, 'all'>;
  title: string;
  secondary_text?: string | null;
  club_id: number | null;
  club_name?: string | null;
  trashed_at: string | null;
  trash_expires_at: string | null;
  updated_at: string | null;
  route_path: string;
}

export interface DuplicateClubPayload {
  name?: string;
  include_players?: boolean;
  visibility?: ClubVisibility;
}

export interface CreateClubPayload {
  name: string;
  description?: string;
  city?: string;
  country?: string;
  stadium?: string;
  division?: string;
  achievements?: string;
  visibility?: ClubVisibility;

  club_type?: ClubType;
  fictional_basis?: FictionalBasis | null;
  source_real_club_name?: string;
  directory_visibility?: DirectoryVisibility | null;
  join_policy?: JoinPolicy | null;

  verification_contact_name?: string;
  verification_contact_role?: string;
  verification_contact_email?: string;
  verification_evidence_text?: string;
  verification_evidence_url?: string;
}

export type UpdateClubPayload = Partial<CreateClubPayload>;

export interface LookupClubByCodeResponse extends Club { }

export interface CreateClubJoinRequestPayload {
  requested_role?: Extract<ClubMembershipRole, 'player'>;
  message?: string;
}

export interface ApproveClubJoinRequestPayload {
  review_note?: string;
  selected_club_player?: number | null;
}

export interface RejectClubJoinRequestPayload {
  review_note?: string;
}

export type WithdrawClubJoinRequestPayload = Record<string, never>;

export interface CreateClubInvitationPayload {
  invited_email: string;
  invited_role: Exclude<ClubMembershipRole, 'owner'>;
  note?: string;
}

export interface AcceptClubInvitationPayload {
  response_note?: string;
}

export interface DeclineClubInvitationPayload {
  response_note?: string;
}

export interface RevokeClubInvitationPayload {
  response_note?: string;
}

export type SchedulingSourceType =
  | 'manual'
  | 'system'
  | 'provider';

export type ClubEventType =
  | 'training'
  | 'meeting'
  | 'social'
  | 'analysis'
  | 'other';

export type FixtureVenue =
  | 'home'
  | 'away'
  | 'neutral';

export type FixtureStatus =
  | 'scheduled'
  | 'completed'
  | 'postponed'
  | 'cancelled';

export type ClubCalendarItemType =
  | 'event'
  | 'fixture';

export interface ClubEvent {
  id: number;
  club: number;
  club_name: string;
  title: string;
  event_type: ClubEventType;
  event_type_display: string;
  description: string;
  start_datetime: string;
  end_datetime: string | null;
  is_all_day: boolean;
  location: string;
  is_mandatory: boolean;
  source_type: SchedulingSourceType;
  source_type_display: string;
  created_by: number | null;
  created_by_email: string | null;
  is_user_editable: boolean;
  is_system_managed_item: boolean;
  is_future_item: boolean;
  calendar_label: string;
  created_at: string;
  updated_at: string;
}

export interface Fixture {
  id: number;
  club: number;
  club_name: string;
  opponent_name: string;
  venue: FixtureVenue;
  venue_display: string;
  competition: string;
  match_datetime: string;
  location: string;
  fixture_status: FixtureStatus;
  fixture_status_display: string;
  source_type: SchedulingSourceType;
  source_type_display: string;
  external_fixture_id: string;
  created_by: number | null;
  created_by_email: string | null;
  is_user_editable: boolean;
  is_system_managed_item: boolean;
  is_future_item: boolean;
  calendar_label: string;
  created_at: string;
  updated_at: string;
}

export interface ClubCalendarFeedItem {
  item_type: ClubCalendarItemType;
  sort_datetime: string;
  calendar_label: string;
  event: ClubEvent | null;
  fixture: Fixture | null;
}

export interface ClubCalendarFeedParams {
  include_past?: boolean;
  limit?: number;
}

export interface CreateClubEventPayload {
  title: string;
  event_type?: ClubEventType;
  description?: string;
  start_datetime: string;
  end_datetime?: string | null;
  is_all_day?: boolean;
  location?: string;
  is_mandatory?: boolean;
}

export type UpdateClubEventPayload = Partial<CreateClubEventPayload>;

export interface CreateFixturePayload {
  opponent_name: string;
  venue: FixtureVenue;
  competition?: string;
  match_datetime: string;
  location?: string;
  fixture_status?: FixtureStatus;
}

export type UpdateFixturePayload = Partial<CreateFixturePayload>;

export type ClubResourceFileKind =
  | 'pdf'
  | 'docx'
  | 'pptx'
  | 'xlsx'
  | 'csv'
  | 'image';

export type ClubResourceStorageBackend =
  | 'local'
  | 'cloudinary';

export type ClubResourceEngagementVisibility =
  | 'staff_only'
  | 'club_visible';

export type ClubResourceViewerMode =
  | 'inline'
  | 'download';

export interface ClubResource {
  id: number;
  club: number;
  club_name: string;
  uploaded_by: number | null;
  uploaded_by_email: string | null;
  title: string;
  description: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  file_kind: ClubResourceFileKind;
  engagement_visibility: ClubResourceEngagementVisibility;
  is_archived: boolean;
  total_pages: number | null;
  viewer_mode: ClubResourceViewerMode;
  can_inline_view: boolean;
  is_download_only: boolean;
  opened_count: number | null;
  completed_count: number | null;
  latest_opened_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClubResourceViewSummary {
  id: number;
  resource: number;
  user: number;
  user_email: string;
  first_opened_at: string | null;
  last_opened_at: string | null;
  total_active_seconds: number;
  highest_page_reached: number;
  opened: boolean;
  completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClubResourceEngagement {
  id: number;
  title: string;
  engagement_visibility: ClubResourceEngagementVisibility;
  is_archived: boolean;
  total_viewers: number;
  opened_count: number;
  completed_count: number;
  resource_views: ClubResourceViewSummary[];
}

export interface ClubResourceSignedAccessResponse {
  resource_id: number;
  title: string;
  original_filename: string;
  mime_type: string;
  file_kind: ClubResourceFileKind;
  access_mode: ClubResourceViewerMode;
  can_inline_view: boolean;
  is_download_only: boolean;
  access_url: string;
  expires_at: string;
}

export interface ClubResourceMyStatus {
  resource_id: number;
  engagement_visibility: ClubResourceEngagementVisibility;
  can_view_club_status: boolean;
  opened_count: number | null;
  completed_count: number | null;
  my_view_summary: ClubResourceViewSummary | null;
}

export interface UploadClubResourcePayload {
  title: string;
  description?: string;
  file: File;
  engagement_visibility?: ClubResourceEngagementVisibility;
}

export interface UpdateClubResourcePayload {
  title?: string;
  description?: string;
  engagement_visibility?: ClubResourceEngagementVisibility;
}

export interface ArchiveClubResourcePayload {
  is_archived: boolean;
}

export interface ClubResourceHeartbeatPayload {
  active_seconds_delta: number;
  page_reached?: number | null;
}

export type ClubImportType =
  | 'player_profile_update'
  | 'player_season_stats'
  | 'squad_metrics'
  | 'other';

export type ClubImportJobStatus =
  | 'uploaded'
  | 'validating'
  | 'preview_ready'
  | 'confirmed'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface ClubImportJobListItem {
  id: number;
  club: number;
  club_name: string;
  uploaded_by: number | null;
  uploaded_by_email: string | null;
  source_resource: number;
  source_resource_title: string;
  source_resource_original_filename: string;
  import_type: ClubImportType;
  status: ClubImportJobStatus;
  row_count: number;
  valid_row_count: number;
  imported_row_count: number;
  skipped_row_count: number;
  failed_row_count: number;
  warning_count: number;
  created_at: string;
  updated_at: string;
}

export interface ClubImportJob extends ClubImportJobListItem {
  error_summary: Record<string, unknown>;
  preview_payload: Record<string, unknown>;
  report_payload: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
}

export interface CreateClubImportJobPayload {
  source_resource: number;
  import_type: ClubImportType;
}

export interface CommitClubImportJobPayload {
  confirm: true;
}

export type PlayerAvailabilityStatus = 'AV' | 'IN' | 'DO' | 'SU';

export type InjuryType =
  | 'muscle'
  | 'ligament'
  | 'bone'
  | 'tendon'
  | 'cartilage'
  | 'head'
  | 'illness'
  | 'suspension'
  | 'other';

export type InjurySeverity = 'minor' | 'moderate' | 'severe';

export interface ClubPlayerInjury {
  id: number;
  club_player: number;
  injury_type: InjuryType;
  injury_type_display: string;
  severity: InjurySeverity;
  severity_display: string;
  availability_status: PlayerAvailabilityStatus;
  availability_status_display: string;
  injured_at: string;
  estimated_return: string | null;
  notes: string;
  is_current: boolean;
  recorded_by: number | null;
  recorded_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateClubPlayerInjuryPayload {
  injury_type: InjuryType;
  severity: InjurySeverity;
  availability_status: Exclude<PlayerAvailabilityStatus, 'AV'>;
  injured_at: string;
  estimated_return?: string | null;
  notes?: string;
}

export interface ClubPlayerManualStats {
  id: number;
  club_player: number;
  season: string;
  appearances: number | null;
  minutes_played: number | null;
  goals: number | null;
  assists: number | null;
  xg: string | null;
  npxg: string | null;
  xa: string | null;
  shots: number | null;
  shots_on_target: number | null;
  key_passes: number | null;
  dribbles_completed: number | null;
  progressive_passes: number | null;
  progressive_carries: number | null;
  tackles: number | null;
  interceptions: number | null;
  aerials_won: number | null;
  clearances: number | null;
  blocks: number | null;
  saves: number | null;
  save_percentage: string | null;
  clean_sheets: number | null;
  goals_conceded: number | null;
  last_updated: string;
  created_at: string;
}

export type CreateOrUpdateClubPlayerManualStatsPayload = Partial<
  Omit<ClubPlayerManualStats, 'id' | 'club_player' | 'last_updated' | 'created_at'>
> & { season: string };

export type SeasonResultVenue = 'home' | 'away' | 'neutral';

export type MatchOutcome = 'W' | 'D' | 'L';

export interface ClubSeasonResult {
  id: number;
  club: number;
  opponent_name: string;
  venue: SeasonResultVenue;
  venue_display: string;
  competition: string;
  match_date: string;
  goals_for: number;
  goals_against: number;
  outcome: MatchOutcome;
  fixture: number | null;
  notes: string;
  created_by: number | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateClubSeasonResultPayload {
  opponent_name: string;
  venue: SeasonResultVenue;
  competition?: string;
  match_date: string;
  goals_for: number;
  goals_against: number;
  fixture?: number | null;
  notes?: string;
}

export type UpdateClubSeasonResultPayload = Partial<CreateClubSeasonResultPayload>;

export interface ClubSeasonRecord {
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  played: number;
}