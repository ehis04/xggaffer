export interface PlayerDataContext {
  provider?: string | null;
  season?: string | null;
  competition_code?: string | null;
  competition_name?: string | null;
}

export interface ProviderCoverage {
  provider?: string | null;
  has_data?: boolean;
  coverage_status?: string | null;
  freshness_label?: string | null;
  source_updated_at?: string | null;
  last_synced_at?: string | null;
  matches_sampled?: number | null;
  minutes_sampled?: number | null;
  coverage_notes?: string[];
}

export interface PlayerDataExplanation {
  headline?: string | null;
  summary?: string | null;
  strengths?: string[];
  watchouts?: string[];
  notes?: string[];
}

export interface PlayerDataMetric {
  key: string;
  label: string;
  value?: number | null;
  formatted_value?: string | null;
  unit?: string | null;
  rank?: number | null;
  percentile?: number | null;
  sample_size?: number | null;
  is_available?: boolean;
}

export interface PlayerIdentityBasic {
  id: number;
  full_name?: string | null;
  display_name?: string | null;
  short_name?: string | null;
  position?: string | null;
  nationality?: string | null;
  age?: number | null;
  photo_url?: string | null;
}

export interface ClubIdentityBasic {
  id: number | null;
  name?: string | null;
  short_name?: string | null;
  crest_url?: string | null;
}

export interface PlayerSeasonSummary {
  player: PlayerIdentityBasic;
  club?: ClubIdentityBasic | null;
  context?: PlayerDataContext | null;
  metrics?: PlayerDataMetric[];
  explanation?: PlayerDataExplanation | null;
  provider_coverage?: ProviderCoverage | null;
  has_summary_data?: boolean;
  missing_reasons?: string[];
}

export interface ClubSeasonSummary {
  club: ClubIdentityBasic;
  context?: PlayerDataContext | null;
  metrics?: PlayerDataMetric[];
  explanation?: PlayerDataExplanation | null;
  provider_coverage?: ProviderCoverage | null;
  has_summary_data?: boolean;
  missing_reasons?: string[];
}

export interface PlayerComparisonSide {
  player: PlayerIdentityBasic;
  club?: ClubIdentityBasic | null;
}

export interface PlayerComparisonMetric {
  key: string;
  label: string;
  player_a_value?: number | null;
  player_a_formatted?: string | null;
  player_b_value?: number | null;
  player_b_formatted?: string | null;
  delta?: number | null;
  formatted_delta?: string | null;
  unit?: string | null;
  winner?: string | null;
  is_tie?: boolean;
}

export interface ComparisonWinner {
  winner?: string | null;
  winner_player_id?: number | null;
  reason?: string | null;
}

export interface PlayerComparisonResult {
  player_a: PlayerComparisonSide;
  player_b: PlayerComparisonSide;
  context?: PlayerDataContext | null;
  metrics?: PlayerComparisonMetric[];
  overall_winner?: ComparisonWinner | null;
  explanation?: PlayerDataExplanation | null;
  provider_coverage?: ProviderCoverage | null;
  has_comparison_data?: boolean;
  missing_reasons?: string[];
}

export interface EnrichedPlayerListItem {
  player: PlayerIdentityBasic;
  club?: ClubIdentityBasic | null;
  context?: PlayerDataContext | null;
  key_metrics?: PlayerDataMetric[];
  explanation_snippet?: string | null;
  provider_coverage?: ProviderCoverage | null;
  has_enrichment_data?: boolean;
}

export interface EnrichedPlayerListResponse {
  count: number;
  results: EnrichedPlayerListItem[];
}

export interface PlayerDataFilters {
  provider?: string;
  season?: string;
  competition_code?: string;
  competition_name?: string;
}

export interface PlayerComparisonParams extends PlayerDataFilters {
  player_a_id: number;
  player_b_id: number;
}

export interface EnrichedPlayerListFilters extends PlayerDataFilters {
  club_id?: number;
  position?: string;
  search?: string;
  ordering?: string;
  limit?: number;
  include_unavailable?: boolean;
}

export interface MetricSourcePreference {
  concept?: string | null;
  primary_source?: string | null;
  preferred_provider?: string | null;
  reason?: string | null;
}

export interface PlayerOverviewMetric {
  key: string;
  label: string;
  value?: number | null;
  formatted_value?: string | null;
  unit?: string | null;
  rank?: number | null;
  percentile?: number | null;
  sample_size?: number | null;
  is_available?: boolean;
  source?: string | null;
  preferred_provider?: string | null;
  source_preference?: MetricSourcePreference | null;
}

export interface PlayerOverviewMetricGroup {
  key: string;
  label: string;
  metrics?: PlayerOverviewMetric[];
}

export interface PlayerOverviewIdentity extends PlayerIdentityBasic {
  primary_position?: string | null;
  secondary_positions?: string[] | null;
  first_name?: string | null;
  last_name?: string | null;
}

export interface PlayerOverviewClub extends ClubIdentityBasic {
  source?: string | null;
}

export interface PlayerOverviewContext {
  provider?: string | null;
  season?: string | null;
  competition_code?: string | null;
  competition_name?: string | null;
  competition_id?: number | null;
  team_id?: number | null;
  team_name?: string | null;
  livefootball_source?: string | null;
}

export interface PlayerOverviewExplanation extends PlayerDataExplanation {
  sentences?: string[];
}

export interface SourceDetail {
  source?: string | null;
  provider?: string | null;
  providers?: string[] | null;
  has_data?: boolean;
  coverage_status?: string | null;
  freshness_label?: string | null;
  source_updated_at?: string | null;
  last_synced_at?: string | null;
  matches_sampled?: number | null;
  minutes_sampled?: number | null;
  coverage_notes?: string[];
  team?: Record<string, unknown> | null;
  competition?: Record<string, unknown> | null;
  season_label?: string | null;
  record_count?: number | null;
  seasons?: string[] | null;
  competitions?: string[] | null;
  items?: Record<string, unknown>[] | null;
}

export interface MergedProviderCoverage extends ProviderCoverage {
  available_sources?: string[];
  missing_sources?: string[];
  source_count?: number | null;
  available_source_count?: number | null;
  missing_source_count?: number | null;
  source_details?: Record<string, SourceDetail> | null;
  player_a?: Record<string, unknown> | null;
  player_b?: Record<string, unknown> | null;
}

export interface SourcePreferenceRule {
  key?: string | null;
  primary_source?: string | null;
  preferred_provider?: string | null;
  reason?: string | null;
}

export interface SourcePreferenceBlock {
  available_sources?: string[];
  rules?: SourcePreferenceRule[];
  metric_rules?: SourcePreferenceRule[];
}

export interface PlayerOverview {
  player: PlayerOverviewIdentity;
  club?: PlayerOverviewClub | null;
  context?: PlayerOverviewContext | null;
  general_overview?: PlayerOverviewExplanation | null;
  metric_groups?: PlayerOverviewMetricGroup[];
  provider_coverage?: MergedProviderCoverage | null;
  source_preferences?: SourcePreferenceBlock | null;
  livefootball_context?: Record<string, unknown> | null;
  playerdata_context?: Record<string, unknown> | null;
  has_overview_data?: boolean;
  missing_reasons?: string[];
}

/**
 * Phase 7 / 8 constrained deterministic insight layer
 */

export type SupportedInsightIntent =
  | 'season_summary'
  | 'attacking_output'
  | 'minutes_usage'
  | 'provider_coverage'
  | 'freshness'
  | 'comparison_handoff'
  | 'club_season_summary';

export interface SupportedInsightOption {
  intent: SupportedInsightIntent;
  label: string;
  description?: string;
  disabled?: boolean;
}

export interface InternalPlayerNavigationContext {
  fromClubId?: number | null;
  clubPlayerId?: number | null;
  returnToPlayerId?: number | null;
}

export interface InsightResponseAction {
  label: string;
  to?: string;
}

export interface InsightUnsupportedResponse {
  code?: string | null;
  message: string;
  requested_intent?: string | null;
}

export interface BaseInsightResponse {
  title: string;
  body: string;
  bullets?: string[];
  meta?: string[];
  action?: InsightResponseAction | null;
  is_unavailable?: boolean;
  unsupported?: InsightUnsupportedResponse | null;
}

export interface InsightResponseBlockData {
  title: string;
  body: string;
  bullets?: string[];
  meta?: string[];
  action?: InsightResponseAction | null;
  isUnavailable?: boolean;
}

export interface PlayerInsightResponse extends BaseInsightResponse {
  intent: SupportedInsightIntent;
  player_id?: number | null;
  player?: PlayerIdentityBasic | null;
  club?: ClubIdentityBasic | null;
  context?: PlayerDataContext | null;
  provider_coverage?: ProviderCoverage | null;
}

export interface ClubInsightResponse extends BaseInsightResponse {
  intent: SupportedInsightIntent;
  club_id?: number | null;
  club?: ClubIdentityBasic | null;
  context?: PlayerDataContext | null;
  provider_coverage?: ProviderCoverage | null;
}

export interface ComparisonOverviewContext {
  provider?: string | null;
  season?: string | null;
  competition_code?: string | null;
  competition_name?: string | null;
  same_provider?: boolean;
  same_season?: boolean;
  same_competition?: boolean;
  left_last_synced_at?: string | null;
  right_last_synced_at?: string | null;
  sentence?: string | null;
}

export interface PlayerOverviewComparisonMetric {
  key: string;
  label: string;
  player_a_value?: number | null;
  player_a_formatted?: string | null;
  player_b_value?: number | null;
  player_b_formatted?: string | null;
  delta?: number | null;
  formatted_delta?: string | null;
  unit?: string | null;
  winner?: string | null;
  is_tie?: boolean;
  is_comparable?: boolean;
  sentence?: string | null;
  source?: string | null;
  preferred_provider?: string | null;
  source_preference?: MetricSourcePreference | null;
}

export interface PlayerOverviewComparisonMetricGroup {
  key: string;
  label: string;
  metrics?: PlayerOverviewComparisonMetric[];
}

export interface PlayerOverviewComparison {
  player_a: PlayerOverview;
  player_b: PlayerOverview;
  context?: ComparisonOverviewContext | null;
  general_overview?: PlayerOverviewExplanation | null;
  metric_groups?: PlayerOverviewComparisonMetricGroup[];
  summary_lines?: string[];
  overall_winner?: ComparisonWinner | null;
  provider_coverage?: MergedProviderCoverage | null;
  source_preferences?: SourcePreferenceBlock | null;
  has_comparison_data?: boolean;
  missing_reasons?: string[];
}