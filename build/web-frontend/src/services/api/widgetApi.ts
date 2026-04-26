import apiClient from './client';
import type { ApiEnvelope } from '../../common/types/response';
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

const WIDGET_BASE = '/predictions/widget';

export async function fetchMatchPredictionWidget(
  homeTeam: string,
  awayTeam: string,
): Promise<ApiEnvelope<MatchPredictionWidgetPayload>> {
  return apiClient.get<ApiEnvelope<MatchPredictionWidgetPayload>>(
    `${WIDGET_BASE}/match-prediction/`,
    { home_team: homeTeam, away_team: awayTeam },
  );
}

export async function fetchScorelineWidget(
  homeTeam: string,
  awayTeam: string,
): Promise<ApiEnvelope<ScorelineWidgetPayload>> {
  return apiClient.get<ApiEnvelope<ScorelineWidgetPayload>>(
    `${WIDGET_BASE}/scoreline/`,
    { home_team: homeTeam, away_team: awayTeam },
  );
}

export async function fetchProjectedTableWidget(
  leagueCode: string,
): Promise<ApiEnvelope<ProjectedTableWidgetPayload>> {
  return apiClient.get<ApiEnvelope<ProjectedTableWidgetPayload>>(
    `${WIDGET_BASE}/projected-table/`,
    { league_code: leagueCode },
  );
}