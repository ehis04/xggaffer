export interface CompetitionListItem {
  id: number;
  provider: string;
  external_id: string;
  code: string;
  name: string;
  area_name: string;
  emblem_url: string;
  current_season_label: string;
  current_season_start_date?: string | null;
  current_season_end_date?: string | null;
  current_matchday?: number | null;
  last_synced_at?: string | null;
}

export interface TeamLookupItem {
  id: number;
  competition_id: number;
  provider: string;
  external_id: string;
  season_label: string;
  name: string;
  short_name: string;
  tla: string;
  area_name: string;
  emblem_url: string;
  venue: string;
  website: string;
  founded_year?: number | null;
  last_synced_at?: string | null;
}

export interface TeamReference {
  id?: number | null;
  external_id?: string | null;
  name: string;
  short_name: string;
  tla: string;
  emblem_url: string;
}

export interface CanonicalPlayerReference {
  id?: number | null;
  display_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
}

export interface PlayerLookupItem {
  id: number;
  provider: string;
  external_player_id: string;
  player_name: string;
  first_name: string;
  last_name: string;
  date_of_birth?: string | null;
  nationality: string;
  primary_position: string;
  raw_position: string;
  squad_number?: number | null;
  is_active: boolean;
  team?: TeamLookupItem | null;
  canonical_player?: CanonicalPlayerReference | null;
}

export type PlayerSearchResult = PlayerLookupItem;

export interface LeagueTableRow {
  position: number;
  team: TeamReference;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
  form: string;
}

export interface CompetitionTableResponse {
  competition: CompetitionListItem;
  season_label: string;
  snapshot_label: string;
  matchday?: number | null;
  fetched_at?: string | null;
  synced_at?: string | null;
  rows: LeagueTableRow[];
}

export interface CompetitionFixtureItem {
  id: number;
  external_match_id: string;
  season_label: string;
  status: string;
  kickoff_at?: string | null;
  matchday?: number | null;
  home_team: TeamReference;
  away_team: TeamReference;
  home_score?: number | null;
  away_score?: number | null;
}

export interface CompetitionFixturesResponse {
  competition: CompetitionListItem;
  season_label: string;
  count: number;
  items: CompetitionFixtureItem[];
}

export interface CompetitionPreviousNextFixturesResponse {
  competition: CompetitionListItem;
  season_label: string;
  previous: CompetitionFixtureItem[];
  next: CompetitionFixtureItem[];
}

export interface CompetitionTopScorerItem {
  rank: number;
  external_player_id: string;
  player_name: string;
  goals: number;
  penalties?: number | null;
  team: TeamReference;
  canonical_player?: CanonicalPlayerReference | null;
}

export interface CompetitionTopScorersResponse {
  competition: CompetitionListItem;
  season_label: string;
  count: number;
  items: CompetitionTopScorerItem[];
}

export interface CompetitionTeamsResponse {
  competition: CompetitionListItem;
  season_label: string;
  count: number;
  items: TeamLookupItem[];
}

export interface TeamPlayersResponse {
  team: TeamLookupItem;
  competition: CompetitionListItem;
  season_label: string;
  count: number;
  items: PlayerLookupItem[];
}

export interface CompetitionPlayersResponse {
  competition: CompetitionListItem;
  season_label: string;
  count: number;
  items: PlayerLookupItem[];
}

export interface PlayerSearchResponse {
  query: string;
  count: number;
  items: PlayerSearchResult[];
}

export interface CompetitionTableParams {
  season?: string;
  snapshot?: string;
}

export interface CompetitionFixturesParams {
  season?: string;
  status?: string;
  matchday?: number;
  limit?: number;
}

export interface CompetitionPreviousNextFixturesParams {
  season?: string;
  previous_limit?: number;
  next_limit?: number;
}

export interface CompetitionScorersParams {
  season?: string;
  limit?: number;
}

export interface CompetitionTeamsParams {
  season?: string;
}

export interface TeamPlayersParams {
  active_only?: boolean;
}

export interface CompetitionPlayersParams {
  season?: string;
  active_only?: boolean;
}

export interface PlayerSearchParams {
  q?: string;
  competition_id?: number;
  team_id?: number;
  season?: string;
  active_only?: boolean;
  limit?: number;
}

export interface LiveFootballOverviewCta {
  label: string;
  path: string;
  query: Record<string, string | number | boolean | null | undefined>;
}

export interface LiveFootballOverviewCompetition {
  id: number;
  code: string | null;
  name: string;
  country: string | null;
  emblem_url: string | null;
}

export interface LiveFootballOverviewTeamReference {
  id: number | null;
  name: string;
  short_name: string | null;
  crest_url: string | null;
}

export interface LiveFootballOverviewPlayerReference {
  id: number | null;
  name: string;
  short_name: string | null;
  position: string | null;
  shirt_number?: number | null;
  photo_url?: string | null;
}

export interface LiveFootballLeagueSnapshotRow {
  position: number | null;
  team: LiveFootballOverviewTeamReference;
  played: number | null;
  won: number | null;
  drawn: number | null;
  lost: number | null;
  goals_for?: number | null;
  goals_against?: number | null;
  goal_difference: number | null;
  points: number | null;
  form_label?: string | null;
}

export interface LiveFootballLeagueSnapshotCard {
  competition: LiveFootballOverviewCompetition;
  synced_at: string | null;
  top_rows: LiveFootballLeagueSnapshotRow[];
  bottom_rows: LiveFootballLeagueSnapshotRow[];
  cta: LiveFootballOverviewCta;
}

export interface LiveFootballTrendTeamCard {
  rank: number | null;
  team: LiveFootballOverviewTeamReference;
  competition: LiveFootballOverviewCompetition;
  summary: string;
  metric_label: string;
  metric_value: string;
  form_label?: string | null;
  cta: LiveFootballOverviewCta;
}

export interface LiveFootballTrendPlayerCard {
  rank?: number | null;
  player: LiveFootballOverviewPlayerReference;
  team: LiveFootballOverviewTeamReference;
  competition: LiveFootballOverviewCompetition;
  summary: string;
  metric_label?: string | null;
  metric_value?: string | null;
  cta: LiveFootballOverviewCta;
}

export interface LiveFootballMatchReference {
  id: number | null;
  utc_date: string | null;
  status: string | null;
  home_team: LiveFootballOverviewTeamReference;
  away_team: LiveFootballOverviewTeamReference;
  home_score: number | null;
  away_score: number | null;
  score_line: string | null;
  venue_label: string | null;
}

export interface LiveFootballLeagueMatchPreview {
  competition: LiveFootballOverviewCompetition;
  synced_at: string | null;
  items: LiveFootballMatchReference[];
  cta: LiveFootballOverviewCta;
}

export interface LiveFootballClubSpotlightPlayer {
  team_id: number | null;
  team_name: string;
  player: LiveFootballOverviewPlayerReference;
  minutes_played: number | null;
  reason_label: string;
}

export interface LiveFootballFirstVsLastLeagueCard {
  competition: LiveFootballOverviewCompetition;
  synced_at: string | null;
  leader: LiveFootballLeagueSnapshotRow | null;
  bottom: LiveFootballLeagueSnapshotRow | null;
  spotlight_players: LiveFootballClubSpotlightPlayer[];
  cta: LiveFootballOverviewCta;
}

export interface LiveFootballStreakCard {
  competition_code: string | null;
  competition_name: string | null;
  team_name: string;
  team_id: number | null;
  crest_url: string | null;
  streak_value: number | null;
  label: string;
  summary: string;
}

export interface LiveFootballTrendTeamStrip {
  updated_at: string | null;
  items: LiveFootballTrendTeamCard[];
}

export interface LiveFootballTrendPlayerStrip {
  updated_at: string | null;
  items: LiveFootballTrendPlayerCard[];
}

export interface LiveFootballAllTimeStreaks {
  updated_at: string | null;
  all_time: LiveFootballStreakCard[];
  current: LiveFootballStreakCard[];
  cta: LiveFootballOverviewCta;
}

export interface LiveFootballOverview {
  generated_at: string;
  league_order: string[];
  league_snapshot: LiveFootballLeagueSnapshotCard[];
  top_performing_teams: LiveFootballTrendTeamStrip;
  top_performing_scorers: LiveFootballTrendPlayerStrip;
  latest_hat_tricks: LiveFootballTrendPlayerStrip;
  strikers_with_a_lull: LiveFootballTrendPlayerStrip;
  recent_matches_by_league: LiveFootballLeagueMatchPreview[];
  upcoming_matches_by_league: LiveFootballLeagueMatchPreview[];
  first_vs_last_by_league: LiveFootballFirstVsLastLeagueCard[];
  all_time_streaks: LiveFootballAllTimeStreaks;
}

export interface UnsupportedMode {
  mode: string;
  reason: string;
}

export interface CommentaryBlock {
  type: 'headline' | 'observation' | 'comparison' | 'caveat';
  text: string;
  confidence: 'high' | 'medium' | 'low';
  related_teams: string[];
}

export interface LeagueMetaItem {
  id: number;
  code: string;
  name: string;
  emblem_url: string;
  current_season_label?: string;
  available_seasons: string[];
  supported_modes: string[];
  unavailable_modes: UnsupportedMode[];
}

export interface LeaguesMetaResponse {
  leagues: LeagueMetaItem[];
}

export interface LeagueExpectedTableRow {
  team: TeamReference;
  canonical_team_name: string;
  predicted_points: number;
  predicted_position: number;
  position_probabilities: Record<string, number> | Record<number, number>;
  title_probability: number;
  top_4_probability: number;
  relegation_probability: number;
  simulated_wins: number;
  simulated_draws: number;
  simulated_losses: number;
  simulated_goals_for: number;
  simulated_goals_against: number;
}

export interface LeagueExpectedTableMetadata {
  supported_modes: string[];
  unavailable_modes: UnsupportedMode[];
  projection_window?: 'full_season' | 'to_date';
  based_on_matchweek?: number | null;
  data_cutoff_date?: string | null;
  simulation_count?: number | null;
  engine_versions: Record<string, string>;
  remaining_fixtures?: number | null;
  total_fixtures_simulated?: number | null;
  total_matchweeks?: number | null;
  actual_table_source: string;
  expected_table_source: string;
}

export interface LeagueExpectedTableResponse {
  competition: CompetitionListItem;
  season_label: string;
  mode: string;
  expected_table: LeagueExpectedTableRow[];
  commentary: CommentaryBlock[];
  metadata: LeagueExpectedTableMetadata;
}

export interface LeagueComparisonDelta {
  team: TeamReference;
  canonical_team_name: string;
  actual_position: number;
  expected_position: number;
  position_delta: number;
  actual_points: number;
  expected_points: number;
  points_delta: number;
}

export interface LeagueComparisonMetrics {
  matched_team_count: number;
  average_absolute_position_delta: number | null;
  average_absolute_points_delta: number | null;
  points_correlation: number | null;
}

export interface LeagueCompareMetadata extends LeagueExpectedTableMetadata {
  actual_snapshot_label?: string | null;
  actual_matchday?: number | null;
  actual_synced_at?: string | null;
}

export interface LeagueCompareResponse {
  competition: CompetitionListItem;
  season_label: string;
  mode: string;
  actual_table: LeagueTableRow[];
  expected_table: LeagueExpectedTableRow[];
  deltas: LeagueComparisonDelta[];
  comparison_metrics: LeagueComparisonMetrics;
  commentary: CommentaryBlock[];
  metadata: LeagueCompareMetadata;
}

export interface LeagueProjectionParams {
  season?: string;
  mode?: string;
  matchweek?: number;
  projection_window?: 'full_season' | 'to_date';
}

export interface LeagueScenarioFixture {
  fixture_key: string;
  home_team: TeamReference;
  away_team: TeamReference;
}

export interface LeagueScenarioLockedResultInput {
  fixture_key: string;
  home_goals: number;
  away_goals: number;
}

export interface LeagueScenarioLockedResult extends LeagueScenarioLockedResultInput {
  home_team: TeamReference;
  away_team: TeamReference;
}

export interface LeagueScenarioMetadata extends LeagueExpectedTableMetadata {
  remaining_fixtures_before_lock?: number | null;
  remaining_fixtures_after_lock?: number | null;
}

export interface LeagueScenarioResponse {
  competition: CompetitionListItem;
  season_label: string;
  mode: string;
  remaining_fixtures: LeagueScenarioFixture[];
  locked_results: LeagueScenarioLockedResult[];
  expected_table: LeagueExpectedTableRow[];
  commentary: CommentaryBlock[];
  metadata: LeagueScenarioMetadata;
}

export interface SavedLeagueScenarioListItem {
  id: number;
  competition_id: number;
  competition_name: string;
  title: string;
  description: string;
  season_label: string;
  mode: string;
  based_on_matchweek?: number | null;
  locked_result_count: number;
  updated_at: string;
}

export interface SavedLeagueScenarioListResponse {
  count: number;
  items: SavedLeagueScenarioListItem[];
}

export interface SavedLeagueScenarioLockedFixture {
  id: number;
  fixture_key: string;
  home_team_name: string;
  away_team_name: string;
  home_goals: number;
  away_goals: number;
}

export interface SavedLeagueScenarioDetail {
  id: number;
  competition: CompetitionListItem;
  title: string;
  description: string;
  season_label: string;
  mode: string;
  based_on_matchweek?: number | null;
  locked_results: SavedLeagueScenarioLockedFixture[];
  created_at: string;
  updated_at: string;
}

export interface CreateSavedLeagueScenarioPayload {
  title: string;
  description?: string;
  locked_results: LeagueScenarioLockedResultInput[];
}