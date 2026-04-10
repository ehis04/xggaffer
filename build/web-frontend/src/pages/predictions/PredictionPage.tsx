import { type FormEvent, useEffect, useMemo, useState } from 'react';

import {
  getModelInfo,
  getTeams,
  predictMatch,
  PredictionsApiError,
} from '../../services/api/predictionsApi';
import type {
  ModelInfoResponse,
  PredictionLabel,
  PredictionResponse,
} from '../../types/prediction';

const DEFAULT_LEAGUE = 'EPL';
const DEFAULT_SEASON = '2024';
const DEFAULT_TOP_FACTORS = 5;

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  return value.toFixed(3);
}

function getPredictionTone(prediction: PredictionLabel): string {
  switch (prediction) {
    case 'Home':
      return 'Home edge';
    case 'Away':
      return 'Away edge';
    default:
      return 'Balanced matchup';
  }
}

export default function PredictionPage() {
  const [teams, setTeams] = useState<string[]>([]);
  const [homeTeam, setHomeTeam] = useState('');
  const [awayTeam, setAwayTeam] = useState('');
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadPageData() {
      setIsBootstrapping(true);
      setPageError(null);

      try {
        const [teamsResponse, modelResponse] = await Promise.all([
          getTeams(DEFAULT_LEAGUE, DEFAULT_SEASON),
          getModelInfo(),
        ]);

        if (!isActive) {
          return;
        }

        setTeams(teamsResponse.teams);
        setModelInfo(modelResponse);
        setHomeTeam((current) => current || teamsResponse.teams[0] || '');
        setAwayTeam((current) => {
          if (current) {
            return current;
          }
          return teamsResponse.teams.find((team) => team !== teamsResponse.teams[0]) || '';
        });
      } catch (error) {
        if (!isActive) {
          return;
        }

        setPageError(error instanceof Error ? error.message : 'Failed to load prediction demo.');
      } finally {
        if (isActive) {
          setIsBootstrapping(false);
        }
      }
    }

    void loadPageData();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (!homeTeam || !awayTeam) {
      return;
    }

    if (homeTeam === awayTeam) {
      setPageError('Please choose two different teams.');
      return;
    }

    setPageError((current) => (current === 'Please choose two different teams.' ? null : current));
  }, [awayTeam, homeTeam]);

  const canSubmit = useMemo(() => {
    return Boolean(homeTeam) && Boolean(awayTeam) && homeTeam !== awayTeam && !isSubmitting;
  }, [awayTeam, homeTeam, isSubmitting]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canSubmit) {
      if (homeTeam && awayTeam && homeTeam === awayTeam) {
        setPageError('Please choose two different teams.');
      }
      return;
    }

    setIsSubmitting(true);
    setPageError(null);

    try {
      const result = await predictMatch({
        home_team: homeTeam,
        away_team: awayTeam,
        league: DEFAULT_LEAGUE,
        season: DEFAULT_SEASON,
        top_factors: DEFAULT_TOP_FACTORS,
      });
      setPrediction(result);
    } catch (error) {
      const message =
        error instanceof PredictionsApiError || error instanceof Error
          ? error.message
          : 'Prediction failed.';
      setPageError(message);
      setPrediction(null);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '2rem' }}>
      <header style={{ marginBottom: '1.5rem' }}>
        <p style={{ margin: 0, fontSize: '0.9rem', opacity: 0.7 }}>Standalone prediction demo</p>
        <h1 style={{ margin: '0.25rem 0 0.5rem', fontSize: '2rem' }}>Match Prediction</h1>
        <p style={{ margin: 0, lineHeight: 1.5 }}>
          A focused frontend example for the logistic-regression prediction flow and deterministic
          interpretation layer.
        </p>
      </header>

      <section
        aria-label="Model overview"
        style={{ border: '1px solid #ddd', borderRadius: 12, padding: '1rem', marginBottom: '1rem' }}
      >
        <h2 style={{ marginTop: 0 }}>Model overview</h2>
        {isBootstrapping ? (
          <p>Loading model information…</p>
        ) : modelInfo ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '0.75rem',
            }}
          >
            <div>
              <strong>Model</strong>
              <div>{modelInfo.model_type}</div>
            </div>
            <div>
              <strong>Version</strong>
              <div>{modelInfo.version}</div>
            </div>
            <div>
              <strong>Accuracy</strong>
              <div>{formatMetric(modelInfo.metrics.accuracy)}</div>
            </div>
            <div>
              <strong>Brier score</strong>
              <div>{formatMetric(modelInfo.metrics.brier_score)}</div>
            </div>
            <div>
              <strong>Features</strong>
              <div>{modelInfo.feature_count}</div>
            </div>
            <div>
              <strong>League / season</strong>
              <div>
                {DEFAULT_LEAGUE} / {DEFAULT_SEASON}
              </div>
            </div>
          </div>
        ) : (
          <p>Model info is unavailable.</p>
        )}
      </section>

      <section
        aria-label="Prediction form"
        style={{ border: '1px solid #ddd', borderRadius: 12, padding: '1rem', marginBottom: '1rem' }}
      >
        <h2 style={{ marginTop: 0 }}>Try a matchup</h2>
        <form onSubmit={handleSubmit} aria-label="Prediction form">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              marginBottom: '1rem',
            }}
          >
            <label>
              <span style={{ display: 'block', marginBottom: '0.35rem' }}>Home team</span>
              <select
                aria-label="Home team"
                value={homeTeam}
                onChange={(event) => setHomeTeam(event.target.value)}
                style={{ width: '100%', padding: '0.75rem' }}
              >
                {teams.map((team) => (
                  <option key={`home-${team}`} value={team}>
                    {team}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span style={{ display: 'block', marginBottom: '0.35rem' }}>Away team</span>
              <select
                aria-label="Away team"
                value={awayTeam}
                onChange={(event) => setAwayTeam(event.target.value)}
                style={{ width: '100%', padding: '0.75rem' }}
              >
                {teams.map((team) => (
                  <option key={`away-${team}`} value={team}>
                    {team}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <button type="submit" disabled={!canSubmit || isBootstrapping} style={{ padding: '0.8rem 1.2rem' }}>
            {isSubmitting ? 'Running prediction…' : 'Predict match'}
          </button>
        </form>

        {pageError ? (
          <p role="alert" style={{ color: '#b00020', marginTop: '1rem' }}>
            {pageError}
          </p>
        ) : null}
      </section>

      <section
        aria-label="Prediction result"
        style={{ border: '1px solid #ddd', borderRadius: 12, padding: '1rem' }}
      >
        <h2 style={{ marginTop: 0 }}>Result</h2>

        {!prediction ? (
          <p>Select two teams and run a prediction to see the model output and explanation.</p>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            <div>
              <p style={{ margin: 0, opacity: 0.7 }}>{getPredictionTone(prediction.prediction)}</p>
              <h3 style={{ margin: '0.25rem 0' }}>
                {prediction.home_team} vs {prediction.away_team}: {prediction.prediction}
              </h3>
              <p style={{ margin: 0 }}>
                {prediction.league} {prediction.season} • {prediction.model_type} • {prediction.version}
              </p>
            </div>

            <div>
              <h3>Probabilities</h3>
              <div style={{ display: 'grid', gap: '0.75rem' }}>
                {[
                  { label: 'Home', value: prediction.probabilities.home },
                  { label: 'Draw', value: prediction.probabilities.draw },
                  { label: 'Away', value: prediction.probabilities.away },
                ].map((item) => (
                  <div key={item.label}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <span>{item.label}</span>
                      <strong>{formatPercent(item.value)}</strong>
                    </div>
                    <progress value={item.value} max={1} style={{ width: '100%' }} />
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3>Top factors</h3>
              <ul style={{ paddingLeft: '1.2rem', margin: 0, display: 'grid', gap: '0.75rem' }}>
                {prediction.top_factors.map((factor) => (
                  <li key={factor.feature}>
                    <strong>{factor.feature}</strong>
                    <div>{factor.description}</div>
                    <div>
                      Value: {factor.value.toFixed(3)} • Contribution: {factor.contribution.toFixed(4)}
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3>Metrics</h3>
              <p style={{ margin: 0 }}>
                Accuracy: <strong>{formatMetric(prediction.metrics.accuracy)}</strong> • Brier score:{' '}
                <strong>{formatMetric(prediction.metrics.brier_score)}</strong>
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
