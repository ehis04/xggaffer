import apiClient from './client';
import { isEnvelope, type ApiEnvelope } from '../../common/types/response';
import type { FreshnessPayload } from '../../common/types/freshness';

export interface WidgetFreshness extends FreshnessPayload {
  cascade_degraded: boolean;
  cascade_reason: string | null;
}

export interface WidgetConfidence {
  score: number;
  band: 'high' | 'medium' | 'low';
}

export interface MatchPredictionData {
  home_team: string;
  away_team: string;
  home_prob: number;
  draw_prob: number;
  away_prob: number;
  prediction: string;
  top_drivers: unknown[];
  elo_home: number | null;
  elo_away: number | null;
}

export interface MatchPredictionWidgetPayload {
  widget_type: string;
  data: MatchPredictionData | null;
  explanation: Record<string, unknown>;
  confidence: WidgetConfidence;
  freshness: WidgetFreshness;
  summary: Record<string, unknown>;
}

export interface ScorelineData {
  matrix: number[][];
  top_3_scorelines: Array<{ scoreline: string; prob: number }>;
  over_under_probs: { over_2_5: number; under_2_5: number };
  btts_prob: number;
}

export interface ScorelineWidgetPayload {
  widget_type: string;
  data: ScorelineData | null;
  explanation: Record<string, unknown>;
  confidence: WidgetConfidence;
  freshness: WidgetFreshness;
  summary: Record<string, unknown>;
}

export interface TeamProjection {
  team_name: string;
  expected_position: number;
  projected_points_median: number;
  projected_points_p10: number | null;
  projected_points_p90: number | null;
  title_prob: number;
  top4_prob: number;
  relegation_prob: number;
  position_distribution: Record<string, number>;
}

export interface ProjectedTableData {
  league_code: string;
  season: string | number;
  teams: TeamProjection[];
}

export interface ProjectedTableWidgetPayload {
  widget_type: string;
  data: ProjectedTableData | null;
  explanation: Record<string, unknown>;
  confidence: WidgetConfidence;
  freshness: WidgetFreshness;
  summary: Record<string, unknown>;
}

export interface WhatIfAdjustment {
  fixture_id: string;
  home_team: string;
  away_team: string;
  selected_outcome: 'home' | 'draw' | 'away' | null;
}

export interface PlayerAvailability {
  name: string;
  availability_prob: number;
  risk_level: 'unavailable' | 'at_risk' | 'available';
  return_date_estimate: string | null;
}

export interface AvailabilityData {
  team: string;
  fixture_date: string;
  players: PlayerAvailability[];
  summary: {
    available_count: number;
    high_risk_count: number;
    unavailable_count: number;
  };
}

export interface AvailabilityWidgetPayload {
  widget_type: string;
  data: AvailabilityData | null;
  explanation: Record<string, unknown>;
  confidence: WidgetConfidence;
  freshness: WidgetFreshness;
  summary: Record<string, unknown>;
}

export interface PredictedPlayer {
  name: string;
  position: string;
  start_prob: number;
  stable_id: string | null;
}

export interface LineupData {
  team: string;
  fixture_date: string;
  formation: string | null;
  predicted_xi: PredictedPlayer[];
  bench_candidates: PredictedPlayer[];
}

export interface LineupWidgetPayload {
  widget_type: string;
  data: LineupData | null;
  explanation: Record<string, unknown>;
  confidence: WidgetConfidence;
  freshness: WidgetFreshness;
  summary: Record<string, unknown>;
}

const WIDGET_BASE = '/predictions/widget';

type WidgetResponse<T> = ApiEnvelope<T> | T;

function normalizeWidgetResponse<T extends { freshness: WidgetFreshness }>(
  payload: WidgetResponse<T>,
): ApiEnvelope<T> {
  if (isEnvelope<T>(payload)) {
    return payload;
  }

  return {
    data: payload,
    freshness: payload.freshness,
    version: 'widget-v1',
    warnings: [],
    generated_at: new Date().toISOString(),
  };
}

export async function fetchMatchPredictionWidget(
  homeTeam: string,
  awayTeam: string,
  league?: string,
  season?: string,
): Promise<ApiEnvelope<MatchPredictionWidgetPayload>> {
  const response = await apiClient.get<WidgetResponse<MatchPredictionWidgetPayload>>(
    `${WIDGET_BASE}/match-prediction/`,
    {
      home_team: homeTeam,
      away_team: awayTeam,
      ...(league && { league }),
      ...(season && { season }),
    },
  );
  return normalizeWidgetResponse(response);
}

export async function fetchScorelineWidget(
  homeTeam: string,
  awayTeam: string,
  league?: string,
  season?: string,
): Promise<ApiEnvelope<ScorelineWidgetPayload>> {
  const response = await apiClient.get<WidgetResponse<ScorelineWidgetPayload>>(
    `${WIDGET_BASE}/scoreline/`,
    {
      home_team: homeTeam,
      away_team: awayTeam,
      ...(league && { league }),
      ...(season && { season }),
    },
  );
  return normalizeWidgetResponse(response);
}

export async function fetchProjectedTableWidget(
  leagueCode: string,
): Promise<ApiEnvelope<ProjectedTableWidgetPayload>> {
  const response = await apiClient.get<WidgetResponse<ProjectedTableWidgetPayload>>(
    `${WIDGET_BASE}/projected-table/`,
    { league_code: leagueCode },
  );
  return normalizeWidgetResponse(response);
}

export async function fetchAvailabilityWidget(
  team: string,
  fixtureDate: string,
  league?: string,
  season?: string,
): Promise<ApiEnvelope<AvailabilityWidgetPayload>> {
  const response = await apiClient.get<WidgetResponse<AvailabilityWidgetPayload>>(
    `${WIDGET_BASE}/availability/`,
    {
      team,
      fixture_date: fixtureDate,
      ...(league && { league }),
      ...(season && { season }),
    },
  );
  return normalizeWidgetResponse(response);
}

export async function fetchLineupWidget(
  team: string,
  fixtureDate: string,
  league?: string,
  season?: string,
): Promise<ApiEnvelope<LineupWidgetPayload>> {
  const response = await apiClient.get<WidgetResponse<LineupWidgetPayload>>(
    `${WIDGET_BASE}/predicted-lineup/`,
    {
      team,
      fixture_date: fixtureDate,
      ...(league && { league }),
      ...(season && { season }),
    },
  );
  return normalizeWidgetResponse(response);
}

export interface ZoneProfile {
  zone_name: string;
  pass_success_rate: number;
  pressure_rate: number | null;
  strength_flag: 'strength' | 'weakness' | 'neutral';
}

export interface StyleCluster {
  id: number | string;
  label: string;
  similar_teams: string[];
}

export interface TacticalData {
  team: string;
  style_cluster: StyleCluster;
  zone_profiles: ZoneProfile[];
}

export interface TacticalWidgetPayload {
  widget_type: string;
  data: TacticalData | null;
  explanation: Record<string, unknown>;
  confidence: WidgetConfidence;
  freshness: WidgetFreshness;
  summary: Record<string, unknown>;
}

export async function fetchTacticalWidget(
  team: string,
): Promise<ApiEnvelope<TacticalWidgetPayload>> {
  const response = await apiClient.get<WidgetResponse<TacticalWidgetPayload>>(
    `${WIDGET_BASE}/tactical-summary/`,
    { team },
  );
  return normalizeWidgetResponse(response);
}

export interface ConfidenceBucketAccuracy {
  band: 'high' | 'medium' | 'low';
  total: number;
  correct_count: number;
  accuracy: number | null;
}

export interface BiggestMiss {
  home_team: string;
  away_team: string;
  predicted_outcome: string;
  actual_result: string;
  confidence_band: string;
  predicted_at: string;
  predicted_home_prob: number;
  predicted_draw_prob: number;
  predicted_away_prob: number;
  max_confidence: number;
  actual_outcome_prob: number;
  off_by: number;
}

export interface BiggestHit {
  home_team: string;
  away_team: string;
  predicted_outcome: string;
  actual_result: string;
  confidence_band: string;
  predicted_at: string;
  predicted_home_prob: number;
  predicted_draw_prob: number;
  predicted_away_prob: number;
  max_confidence: number;
  actual_outcome_prob: number;
  off_by: number;
}

export interface MarketComparison {
  market_accuracy: number | null;
  model_accuracy_vs_market: number | null;
  total_evaluated: number;
}

export interface ConfidenceDistributionBucket {
  bucket_min: number;
  bucket_max: number;
  total: number;
  correct_count: number;
  accuracy: number | null;
}

export interface CalibrationFactor {
  key: 'accuracy' | 'confidence' | 'brier_score' | 'log_loss';
  label: string;
  higher_is_better: boolean;
}

export interface CalibrationFactorSeries {
  key: 'random' | 'market' | 'model';
  label: string;
  color: 'grey' | 'red' | 'green';
  values: {
    accuracy: number | null;
    confidence: number | null;
    brier_score: number | null;
    log_loss: number | null;
  };
}

export interface CalibrationFactorPlot {
  factors: CalibrationFactor[];
  series: CalibrationFactorSeries[];
}

export interface ModelTrustData {
  overall_accuracy: number;
  total_resolved: number;
  accuracy_by_band: ConfidenceBucketAccuracy[];
  accuracy_by_league: Array<{
    league_code: string;
    total: number;
    correct_count: number;
    accuracy: number;
  }>;
  recent_form: {
    count: number;
    accuracy: number;
  };
  biggest_misses: BiggestMiss[];
  biggest_hits: BiggestHit[];
  market_comparison: MarketComparison;
  calibration_factor_plot: CalibrationFactorPlot;
  confidence_distribution: ConfidenceDistributionBucket[];
}

export interface ModelTrustWidgetPayload {
  widget_type: string;
  data: ModelTrustData | null;
  explanation: Record<string, unknown>;
  confidence: WidgetConfidence;
  freshness: WidgetFreshness;
  summary: Record<string, unknown>;
}

export async function fetchModelTrustWidget(
  leagueCode?: string,
): Promise<ModelTrustWidgetPayload> {
  return apiClient.get<ModelTrustWidgetPayload>(
    `${WIDGET_BASE}/model-trust/`,
    leagueCode ? { league_code: leagueCode } : undefined,
  );
}