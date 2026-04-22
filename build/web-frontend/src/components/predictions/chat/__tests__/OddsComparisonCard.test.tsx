import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { OddsComparisonEngineData } from '../../../../types/prediction';
import OddsComparisonCard from '../OddsComparisonCard';

const buildOddsEngineData = (
  overrides: Partial<OddsComparisonEngineData> = {},
): OddsComparisonEngineData => ({
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
  ...overrides,
});

describe('OddsComparisonCard', () => {
    it('renders the fixture, bookmaker rows, benchmark context, and wellbeing block', () => {
    render(
        <OddsComparisonCard
        engineData={buildOddsEngineData()}
        partial={false}
        error={null}
        />,
    );

    expect(screen.getByText('Arsenal vs Chelsea')).toBeInTheDocument();
    expect(screen.getByText('Comparison summary')).toBeInTheDocument();
    expect(screen.getByText('Paddy Power')).toBeInTheDocument();
    expect(screen.getByText('Bet365')).toBeInTheDocument();
    expect(
        screen.getByText('The model is slightly more bullish on the home win than the market.'),
    ).toBeInTheDocument();

    expect(screen.getByText('Historical benchmark')).toBeInTheDocument();
    expect(screen.getByText('Sample size')).toBeInTheDocument();
    expect(screen.getByText('360 rows')).toBeInTheDocument();
    expect(screen.getByText('Model accuracy on benchmark sample')).toBeInTheDocument();
    expect(screen.getByText('Market favourite accuracy on benchmark sample')).toBeInTheDocument();
    expect(screen.getByText('engine4_backtest_results.csv')).toBeInTheDocument();
    expect(screen.getByText('Support and wellbeing')).toBeInTheDocument();
    expect(screen.getByText('Problem Gambling Ireland')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Market consensus' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Largest model-market gap')).toBeInTheDocument();
    });

  it('renders a graceful fallback when benchmark is null', () => {
    render(
      <OddsComparisonCard
        engineData={buildOddsEngineData({ benchmark: null })}
        partial={false}
        error={null}
      />,
    );

  expect(
    screen.getByText('Benchmark unavailable for this response.'),
  ).toBeInTheDocument();
  expect(screen.getByText('Support and wellbeing')).toBeInTheDocument();
  });

  it('renders partial note and error note while keeping support visible', () => {
    render(
      <OddsComparisonCard
        engineData={buildOddsEngineData()}
        partial
        error="Live market snapshot is still loading."
      />,
    );

    expect(
      screen.getByText(
        'Odds data is partially available, so some sections may still be pending.',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Live market snapshot is still loading.'),
    ).toBeInTheDocument();
    expect(screen.getByText('GamCare')).toBeInTheDocument();
  });

  it('shows Data pending when market favourite accuracy is null', () => {
    render(
      <OddsComparisonCard
        engineData={buildOddsEngineData({
          benchmark: {
            sample_size: 360,
            model_accuracy: 0.555,
            market_favourite_accuracy: null,
            model_brier_score: 0.612,
            market_brier_score: 0.634,
            evaluation_scope: 'Engine 4 historical benchmark',
            source_label: 'engine4_backtest_results.csv',
          },
        })}
        partial={false}
        error={null}
      />,
    );

  expect(
    screen.getByText('Market favourite accuracy on benchmark sample'),
    ).toBeInTheDocument();
  expect(screen.getByText('Data pending')).toBeInTheDocument();
  });

  it('renders a fallback message when bookmaker rows are empty', () => {
    render(
      <OddsComparisonCard
        engineData={buildOddsEngineData({ bookmakers: [] })}
        partial={false}
        error={null}
      />,
    );

    expect(
      screen.getByText('No bookmaker rows available yet.'),
    ).toBeInTheDocument();
  });
  it('renders sparse bookmaker rows without crashing when last_seen_at is null', () => {
    render(
        <OddsComparisonCard
        engineData={buildOddsEngineData({
            bookmakers: [
            {
                bookmaker: 'Paddy Power',
                home_odds: 1.95,
                draw_odds: 3.5,
                away_odds: 4.1,
                devig_home: 0.5,
                devig_draw: 0.27,
                devig_away: 0.23,
                last_seen_at: null,
            },
            ],
        })}
        partial={false}
        error={null}
        />,
    );

    expect(screen.getByText('Paddy Power')).toBeInTheDocument();
    expect(screen.queryByText(/Last seen:/)).not.toBeInTheDocument();
    expect(screen.getByText('Support and wellbeing')).toBeInTheDocument();
    });
    
    it('keeps the support block visible for a partial response with benchmark unavailable', () => {
    render(
        <OddsComparisonCard
        engineData={buildOddsEngineData({ benchmark: null })}
        partial
        error={null}
        />,
    );

    expect(
        screen.getByText(
        'Odds data is partially available, so some sections may still be pending.',
        ),
    ).toBeInTheDocument();
    expect(
        screen.getByText('Benchmark unavailable for this response.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Support and wellbeing')).toBeInTheDocument();
    });
});