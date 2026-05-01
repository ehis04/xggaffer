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

export interface OddsComparisonRequest {
  home_team: string;
  away_team: string;
  league?: string;
  season?: string;
  bookmakers?: string[];
  use_cached?: boolean;
}

export interface BookmakerQuote {
  bookmaker: string;
  home_odds: number;
  draw_odds: number;
  away_odds: number;
  devig_home: number;
  devig_draw: number;
  devig_away: number;
  last_seen_at: string | null;
}

export interface MarketProbabilities {
  devig_home: number;
  devig_draw: number;
  devig_away: number;
  overround: number;
  favourite: string;
  source_label: string;
}

export interface OddsComparisonModelBlock {
  probabilities: PredictionProbabilities;
  prediction: PredictionLabel;
  version: string;
  model_type: string;
}

export interface OddsComparisonComparison {
  model_favourite: string;
  market_favourite: string;
  biggest_edge_side: string;
  biggest_edge_points: number;
  agreement: boolean;
  summary: string;
}

export interface BenchmarkSummary {
  sample_size: number;
  model_accuracy: number;
  market_favourite_accuracy: number | null;
  model_brier_score: number | null;
  market_brier_score: number | null;
  evaluation_scope: string;
  source_label: string;
}

export interface SupportResource {
  label: string;
  region: string;
  support_type: string;
}

export interface WellbeingBlock {
  warning: string;
  resources: SupportResource[];
}

export interface OddsComparisonResponse {
  home_team: string;
  away_team: string;
  league: string;
  season: string;
  kickoff: string | null;
  source: string;
  model: OddsComparisonModelBlock;
  market: MarketProbabilities;
  bookmakers: BookmakerQuote[];
  comparison: OddsComparisonComparison;
  benchmark: BenchmarkSummary | null;
  support: WellbeingBlock;
}

export type OddsComparisonEngineData = OddsComparisonResponse;

export interface OddsConsensus {
  devig_home: number;
  devig_draw: number;
  devig_away: number;
  overround: number;
  favourite: string;
  source_label: string;
}

export interface FixtureResult {
  home_goals: number;
  away_goals: number;
  outcome: 'H' | 'D' | 'A';
  score: string;
}

export interface OddsFixtureItem {
  home_team: string;
  away_team: string;
  league: string;
  season: string;
  commence_time: string;
  fetched_at: string;
  bookmakers: BookmakerQuote[];
  consensus: OddsConsensus | null;
  result: FixtureResult | null;
}

export interface OddsFixtureListResponse {
  league: string;
  season: string;
  view: 'past' | 'future';
  count: number;
  fixtures: OddsFixtureItem[];
}

export interface OddsTeamsResponse {
  league: string;
  teams: string[];
}

export interface ChatEntities {
  home_team: string | null;
  away_team: string | null;
  team: string | null;
  player_name: string | null;
  league: string | null;
  season: string | null;
}

export interface ChatStructuredData {
  intent: string;
  entities: ChatEntities;
  engine_data: Record<string, unknown>;
  partial: boolean;
  error: string | null;
  timestamp: string;
  capabilities?: Record<string, unknown>;
}

export interface ChatResponse {
  prose: string;
  structured_data: ChatStructuredData;
  intent: string;
  entities: ChatEntities;
  used_fallback: boolean;
  query_type: string;
}