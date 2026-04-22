import type {
  ModelInfoResponse,
  OddsComparisonRequest,
  OddsComparisonResponse,
  PredictionRequest,
  PredictionResponse,
  TeamsResponse,
} from '../../../types/prediction';

export const mockTeamsResponse: TeamsResponse = {
  league: 'EPL',
  season: '2024',
  teams: ['Arsenal', 'Chelsea', 'Liverpool', 'Manchester City'],
  count: 4,
};

export const mockModelInfoResponse: ModelInfoResponse = {
  model_type: 'logistic_regression',
  version: 'v2',
  metrics: {
    accuracy: 0.555,
    brier_score: 0.612,
    log_loss: 1.01,
  },
  feature_count: 42,
  training_info: {
    trained_on_leagues: ['EPL'],
    trained_on_seasons: ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024'],
  },
  contract_version: 'v1',
};

export const mockPredictionRequest: PredictionRequest = {
  home_team: 'Arsenal',
  away_team: 'Chelsea',
  league: 'EPL',
  season: '2024',
  top_factors: 5,
};

export const mockPredictionResponse: PredictionResponse = {
  home_team: 'Arsenal',
  away_team: 'Chelsea',
  league: 'EPL',
  season: '2024',
  prediction: 'Home',
  probabilities: {
    home: 0.61,
    draw: 0.23,
    away: 0.16,
  },
  top_factors: [
    {
      feature: 'npxgd_diff',
      value: 0.72,
      contribution: 0.4312,
      description: 'Home team has the edge in non-penalty expected goal difference (+0.72)',
    },
    {
      feature: 'xgd_diff',
      value: 0.51,
      contribution: 0.3174,
      description: 'Home team has the edge in expected goal difference (+0.51)',
    },
    {
      feature: 'ppda_diff',
      value: -1.04,
      contribution: -0.1928,
      description: 'Away team has the edge in passes per defensive action (-1.04)',
    },
  ],
  metrics: {
    accuracy: 0.555,
    brier_score: 0.612,
  },
  model_type: 'logistic_regression',
  version: 'v2',
  contract_version: 'v1',
};

export const mockOddsComparisonRequest: OddsComparisonRequest = {
  home_team: 'Arsenal',
  away_team: 'Chelsea',
  league: 'EPL',
  season: '2024',
  bookmakers: ['paddypower', 'bet365'],
  use_cached: true,
};

export const mockOddsComparisonResponse: OddsComparisonResponse = {
  home_team: 'Arsenal',
  away_team: 'Chelsea',
  league: 'EPL',
  season: '2024',
  kickoff: '2026-04-20T19:00:00Z',
  source: 'the_odds_api',
  model: {
    probabilities: {
      home: 0.56,
      draw: 0.24,
      away: 0.20,
    },
    prediction: 'Home',
    version: 'v2',
    model_type: 'logistic_regression',
  },
  market: {
    devig_home: 0.51,
    devig_draw: 0.26,
    devig_away: 0.23,
    overround: 1.07,
    favourite: 'Home',
    source_label: 'Market consensus',
  },
  bookmakers: [
    {
      bookmaker: 'Paddy Power',
      home_odds: 1.95,
      draw_odds: 3.5,
      away_odds: 4.1,
      devig_home: 0.50,
      devig_draw: 0.27,
      devig_away: 0.23,
      last_seen_at: '2026-04-17T09:30:00Z',
    },
    {
      bookmaker: 'Bet365',
      home_odds: 2.0,
      draw_odds: 3.4,
      away_odds: 4.0,
      devig_home: 0.51,
      devig_draw: 0.26,
      devig_away: 0.23,
      last_seen_at: '2026-04-17T09:32:00Z',
    },
  ],
  comparison: {
    model_favourite: 'Home',
    market_favourite: 'Home',
    biggest_edge_side: 'Home',
    biggest_edge_points: 5,
    agreement: true,
    summary: 'The model is slightly more bullish on the home win than the market.',
  },
  benchmark: {
    sample_size: 360,
    model_accuracy: 0.555,
    market_favourite_accuracy: 0.531,
    model_brier_score: 0.612,
    market_brier_score: 0.634,
    evaluation_scope: 'Engine 4 historical benchmark',
    source_label: 'engine4_backtest_results.csv',
  },
  support: {
    warning: 'Odds reflect probabilities, not certainty. Do not treat this as betting advice.',
    resources: [
      {
        label: 'Problem Gambling Ireland',
        region: 'Ireland',
        support_type: 'helpline',
      },
      {
        label: 'GamCare',
        region: 'UK',
        support_type: 'support',
      },
    ],
  },
};