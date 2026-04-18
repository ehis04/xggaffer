import React, { useMemo } from 'react';
import type { LeagueExpectedTableResponse } from '../../../types/livefootball';
import styles from './css/PredictionSummary.module.css';

interface PredictionSummaryProps {
  payload: LeagueExpectedTableResponse;
}

const formatPercent = (value: number): string => `${Math.round(value * 100)}%`;

const formatModeLabel = (mode: string): string => {
  if (mode === 'pre_season') {
    return 'Pre-season';
  }
  if (mode === 'current_expected') {
    return 'Current expected';
  }
  if (mode === 'as_of_matchweek') {
    return 'As of matchweek';
  }
  return mode;
};

const PredictionSummary: React.FC<PredictionSummaryProps> = ({ payload }) => {
  const summary = useMemo(() => {
    const rows = payload.expected_table;

    if (rows.length === 0) {
      return {
        titleFavourite: null,
        topFourFavourite: null,
        relegationRisk: null,
      };
    }

    const titleFavourite = [...rows].sort((a, b) => {
      if (b.title_probability !== a.title_probability) {
        return b.title_probability - a.title_probability;
      }
      return b.predicted_points - a.predicted_points;
    })[0] ?? null;

    const topFourFavourite = [...rows].sort((a, b) => {
      if (b.top_4_probability !== a.top_4_probability) {
        return b.top_4_probability - a.top_4_probability;
      }
      return b.predicted_points - a.predicted_points;
    })[0] ?? null;

    const relegationRisk = [...rows].sort((a, b) => {
      if (b.relegation_probability !== a.relegation_probability) {
        return b.relegation_probability - a.relegation_probability;
      }
      return a.predicted_position - b.predicted_position;
    })[0] ?? null;

    return {
      titleFavourite,
      topFourFavourite,
      relegationRisk,
    };
  }, [payload]);

  const metadataLine = [
    formatModeLabel(payload.mode),
    payload.metadata.based_on_matchweek !== null && payload.metadata.based_on_matchweek !== undefined
      ? `Based on matchweek ${payload.metadata.based_on_matchweek}`
      : null,
    payload.metadata.data_cutoff_date ? `Cut-off ${payload.metadata.data_cutoff_date}` : null,
    payload.metadata.remaining_fixtures !== null && payload.metadata.remaining_fixtures !== undefined
      ? `${payload.metadata.remaining_fixtures} remaining fixtures`
      : null,
    payload.metadata.simulation_count ? `${payload.metadata.simulation_count} simulations` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Prediction summary</h2>
          <p className={styles.meta}>{metadataLine}</p>
        </div>
      </div>

      <div className={styles.grid}>
        <article className={styles.card}>
          <span className={styles.label}>Title favourite</span>
          {summary.titleFavourite ? (
            <>
              <h3 className={styles.value}>
                {summary.titleFavourite.team.short_name || summary.titleFavourite.team.name}
              </h3>
              <p className={styles.supporting}>
                {formatPercent(summary.titleFavourite.title_probability)} title probability · projected{' '}
                {summary.titleFavourite.predicted_points.toFixed(1)} points
              </p>
            </>
          ) : (
            <p className={styles.empty}>No projection available.</p>
          )}
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Strongest top-four chance</span>
          {summary.topFourFavourite ? (
            <>
              <h3 className={styles.value}>
                {summary.topFourFavourite.team.short_name || summary.topFourFavourite.team.name}
              </h3>
              <p className={styles.supporting}>
                {formatPercent(summary.topFourFavourite.top_4_probability)} top-four probability
              </p>
            </>
          ) : (
            <p className={styles.empty}>No projection available.</p>
          )}
        </article>

        <article className={styles.card}>
          <span className={styles.label}>Highest relegation risk</span>
          {summary.relegationRisk ? (
            <>
              <h3 className={styles.value}>
                {summary.relegationRisk.team.short_name || summary.relegationRisk.team.name}
              </h3>
              <p className={styles.supporting}>
                {formatPercent(summary.relegationRisk.relegation_probability)} relegation probability
              </p>
            </>
          ) : (
            <p className={styles.empty}>No projection available.</p>
          )}
        </article>
      </div>
    </section>
  );
};

export default PredictionSummary;