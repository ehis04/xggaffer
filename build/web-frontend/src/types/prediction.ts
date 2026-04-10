export type PredictionLabel = 'Home' | 'Draw' | 'Away';

export interface PredictionProbabilities {
  home: number;
  draw: number;
  away: number;
}

export interface FeatureContribution {
  feature: string;
  value: number;
  contribution: number;
  description: string;
}

export interface PredictionMetrics {
  accuracy: number;
  brier_score: number | null;
}

export interface PredictionRequest {
  home_team: string;
  away_team: string;
  league?: string;
  season?: string;
  top_factors?: number;
}

export interface PredictionResponse {
  home_team: string;
  away_team: string;
  league: string;
  season: string;
  prediction: PredictionLabel;
  probabilities: PredictionProbabilities;
  top_factors: FeatureContribution[];
  metrics: PredictionMetrics;
  model_type: string;
  version: string;
  contract_version?: string;
}

export interface TeamsResponse {
  league: string;
  season: string;
  teams: string[];
  count: number;
}

export interface ModelInfoResponse {
  model_type: string;
  version: string;
  metrics: {
    accuracy: number;
    brier_score: number | null;
    log_loss?: number | null;
  };
  feature_count: number;
  training_info: Record<string, unknown>;
  contract_version?: string;
}
