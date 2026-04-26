import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { OddsComparisonEngineData } from '../../../../types/prediction';
import StructuredResponseBlock from '../StructuredResponseBlock';

const mockOddsEngineData: OddsComparisonEngineData = {
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
      away: 0.2,
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
      devig_home: 0.5,
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

describe('StructuredResponseBlock', () => {
  it('renders OddsComparisonCard when queryType is ODDS_COMPARISON', () => {
    render(
      <StructuredResponseBlock
        queryType="ODDS_COMPARISON"
        engineData={mockOddsEngineData as unknown as Record<string, unknown>}
        partial={false}
        error={null}
      />,
    );

    expect(screen.getByText('Arsenal vs Chelsea')).toBeInTheDocument();
    expect(screen.getByText('Paddy Power')).toBeInTheDocument();
    expect(screen.getByText('Support and wellbeing')).toBeInTheDocument();
    expect(screen.getByText('Historical benchmark')).toBeInTheDocument();
    expect(screen.getByText('engine4_backtest_results.csv')).toBeInTheDocument();
  });

  it('renders the partial empty-state message when partial is true and engineData is empty', () => {
    render(
      <StructuredResponseBlock
        queryType="ODDS_COMPARISON"
        engineData={{}}
        partial
        error={null}
      />,
    );

    expect(
      screen.getByText('Detailed analytics data is unavailable for this query.'),
    ).toBeInTheDocument();
  });

  it('still renders an existing non-odds query type correctly', () => {
    render(
      <StructuredResponseBlock
        queryType="GLOSSARY"
        engineData={{
          term: 'xG',
          definition: 'Expected goals is a shot-quality metric.',
        }}
        partial={false}
        error={null}
      />,
    );

    expect(screen.getByText('XG')).toBeInTheDocument();
    expect(
      screen.getByText('Expected goals is a shot-quality metric.'),
    ).toBeInTheDocument();
  });

  it('still renders MATCH_PREDICTION content correctly', () => {
    render(
      <StructuredResponseBlock
        queryType="MATCH_PREDICTION"
        engineData={{
          probabilities: {
            home: 0.61,
            draw: 0.22,
            away: 0.17,
          },
          top_factors: [
            {
              feature: 'home_xg',
              value: 1.7,
              contribution: 0.22,
              description: 'Home attacking output is stronger than average.',
            },
          ],
          metrics: {
            accuracy: 0.555,
          },
        }}
        partial={false}
        error={null}
      />,
    );

    expect(screen.getByText(/Model accuracy: 56%/)).toBeInTheDocument();
    expect(
      screen.getByText('Home attacking output is stronger than average.'),
    ).toBeInTheDocument();
  });
});