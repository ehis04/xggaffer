import type {
  ModelInfoResponse,
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
