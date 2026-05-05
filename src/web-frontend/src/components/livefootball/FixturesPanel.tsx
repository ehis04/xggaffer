/**
 * FixturesPanel.tsx
 *
 * Displays previous and upcoming fixtures for a selected competition,
 * with ML win-probability chips fetched in parallel for each match.
 *
 * CSS: FixturesPanel.module.css  (prefix: lffp-)
 */

import React, { useState, useEffect } from 'react';
import type {
  CompetitionFixtureItem,
  CompetitionPreviousNextFixturesResponse,
} from '../../types/livefootball';
import { predictMatch } from '../../services/api/predictionsApi';
import {
  liveCompetitionCodeToPredictionLeague,
  parseSeasonStartYear,
} from '../../utils/footballSeason';
import MatchPredictionChip from '../predictions/MatchPredictionChip';
import styles from './css/FixturesPanel.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatKickoff = (value?: string | null): string => {
  if (!value) return 'TBC';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'TBC';
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

const formatStatus = (status?: string | null): string => {
  const value = (status || '').trim();
  if (!value) return 'Unknown';
  const knownLabels: Record<string, string> = {
    FINISHED: 'Finished',
    AWARDED: 'Awarded',
    AFTER_EXTRA_TIME: 'AET',
    PENALTY_SHOOTOUT: 'Pens',
    SCHEDULED: 'Scheduled',
    TIMED: 'Timed',
    POSTPONED: 'Postponed',
    SUSPENDED: 'Suspended',
    IN_PLAY: 'Live',
    PAUSED: 'Paused',
    LIVE: 'Live',
  };
  return knownLabels[value] ??
    value.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
};

const isLiveStatus = (status?: string | null): boolean =>
  status === 'IN_PLAY' || status === 'LIVE' || status === 'PAUSED';

const getTeamLabel = (name: {
  short_name?: string | null;
  tla?: string | null;
  name: string;
}): string => name.short_name?.trim() || name.tla?.trim() || name.name;

const hasScore = (fixture: CompetitionFixtureItem): boolean =>
  fixture.home_score !== null &&
  fixture.home_score !== undefined &&
  fixture.away_score !== null &&
  fixture.away_score !== undefined;

const renderScore = (fixture: CompetitionFixtureItem): string =>
  hasScore(fixture) ? `${fixture.home_score} - ${fixture.away_score}` : 'vs';

const fixtureKey = (fixture: CompetitionFixtureItem): string =>
  `${fixture.home_team.name}|${fixture.away_team.name}|${fixture.kickoff_at}`;

// ─── FixtureCard sub-component ───────────────────────────────────────────────

interface FixtureCardProps {
  fixture: CompetitionFixtureItem;
  probs: { home: number; draw: number; away: number } | null | undefined;
  predictionsLoading: boolean;
}

const FixtureCard: React.FC<FixtureCardProps> = ({ fixture, probs, predictionsLoading }) => {
  const live = isLiveStatus(fixture.status);
  const scored = hasScore(fixture);
  const fixtureLabel = `${getTeamLabel(fixture.home_team)} v ${getTeamLabel(fixture.away_team)}`;

  return (
    <article className={`${styles['lffp-fixture-card']} ${live ? styles['lffp-fixture-card--live'] : ''}`}>
      <div>{fixtureLabel}</div>
      {/* Status row */}
      <div className={styles['lffp-fixture-meta']}>
        <span className={`${styles['lffp-status-badge']} ${live ? styles['lffp-status-badge--live'] : ''}`}>
          {formatStatus(fixture.status)}
        </span>
        {fixture.matchday && (
          <span className={styles['lffp-matchday']}>MD {fixture.matchday}</span>
        )}
        <MatchPredictionChip
          homeProb={probs?.home ?? null}
          drawProb={probs?.draw ?? null}
          awayProb={probs?.away ?? null}
          isLoading={predictionsLoading}
        />
      </div>

      {/* Score row */}
      <div className={styles['lffp-fixture-body']}>
        {/* Home */}
        <div className={styles['lffp-team']}>
          <span className={styles['lffp-team-name']}>{getTeamLabel(fixture.home_team)}</span>
          {fixture.home_team.name !== getTeamLabel(fixture.home_team) && (
            <span className={styles['lffp-team-full']}>{fixture.home_team.name}</span>
          )}
        </div>

        {/* Score / kickoff */}
        <div className={styles['lffp-score-block']}>
          <span className={`${styles['lffp-score']} ${scored ? styles['lffp-score--result'] : ''}`}>
            {renderScore(fixture)}
          </span>
          <span className={styles['lffp-kickoff']}>{formatKickoff(fixture.kickoff_at)}</span>
        </div>

        {/* Away */}
        <div className={`${styles['lffp-team']} ${styles['lffp-team--right']}`}>
          <span className={styles['lffp-team-name']}>{getTeamLabel(fixture.away_team)}</span>
          {fixture.away_team.name !== getTeamLabel(fixture.away_team) && (
            <span className={styles['lffp-team-full']}>{fixture.away_team.name}</span>
          )}
        </div>
      </div>
    </article>
  );
};

// ─── FixtureListSection sub-component ────────────────────────────────────────

interface FixtureListSectionProps {
  title: string;
  fixtures: CompetitionFixtureItem[];
  emptyMessage: string;
  predictions: Map<string, { home: number; draw: number; away: number } | null>;
  predictionsLoading: boolean;
}

const FixtureListSection: React.FC<FixtureListSectionProps> = ({
  title,
  fixtures,
  emptyMessage,
  predictions,
  predictionsLoading,
}) => (
  <section className={styles['lffp-list-section']}>
    <h3 className={styles['lffp-list-section-title']}>{title}</h3>
    {fixtures.length === 0 ? (
      <div className={styles['lffp-empty']}>{emptyMessage}</div>
    ) : (
      <div className={styles['lffp-fixture-list']}>
        {fixtures.map((fixture) => (
          <FixtureCard
            key={fixture.id || fixture.external_match_id || fixtureKey(fixture)}
            fixture={fixture}
            probs={predictions.get(fixtureKey(fixture))}
            predictionsLoading={predictionsLoading}
          />
        ))}
      </div>
    )}
  </section>
);

// ─── FixturesPanel (public component) ────────────────────────────────────────

export interface FixturesPanelProps {
  fixtures: CompetitionPreviousNextFixturesResponse | null;
  isLoading?: boolean;
  error?: string | null;
  title?: string;
  previousTitle?: string;
  nextTitle?: string;
  className?: string;
}

const FixturesPanel: React.FC<FixturesPanelProps> = ({
  fixtures,
  isLoading = false,
  error = null,
  title = 'Fixtures',
  previousTitle = 'Previous fixtures',
  nextTitle = 'Upcoming fixtures',
  className,
}) => {
  const [predictions, setPredictions] = useState<
    Map<string, { home: number; draw: number; away: number } | null>
  >(new Map());
  const [predictionsLoading, setPredictionsLoading] = useState(false);

  useEffect(() => {
    if (!fixtures) return;
    const allFixtures = [...fixtures.previous, ...fixtures.next];
    if (allFixtures.length === 0) return;

    setPredictionsLoading(true);
    const league = liveCompetitionCodeToPredictionLeague(fixtures.competition.code);

    const requests = allFixtures.map((fixture) => {
      if (!league) return Promise.resolve({ key: fixtureKey(fixture), probs: null });
      const season = parseSeasonStartYear(fixture.season_label);
      return predictMatch({
        home_team: fixture.home_team.name,
        away_team: fixture.away_team.name,
        league,
        season,
      })
        .then((result) => ({ key: fixtureKey(fixture), probs: result.probabilities }))
        .catch(() => ({ key: fixtureKey(fixture), probs: null }));
    });

    Promise.allSettled(requests).then((results) => {
      const map = new Map<string, { home: number; draw: number; away: number } | null>();
      results.forEach((result) => {
        if (result.status === 'fulfilled') map.set(result.value.key, result.value.probs);
      });
      setPredictions(map);
      setPredictionsLoading(false);
    });
  }, [fixtures]);

  // ── State variants ──
  if (isLoading) {
    return (
      <section className={`${styles['lffp-root']} ${className ?? ''}`}>
        <h2 className={styles['lffp-title']}>{title}</h2>
        <div className={styles['lffp-state']}>Loading fixtures…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className={`${styles['lffp-root']} ${className ?? ''}`}>
        <h2 className={styles['lffp-title']}>{title}</h2>
        <div className={styles['lffp-state-error']} role="alert">{error}</div>
      </section>
    );
  }

  if (!fixtures) {
    return (
      <section className={`${styles['lffp-root']} ${className ?? ''}`}>
        <h2 className={styles['lffp-title']}>{title}</h2>
        <div className={styles['lffp-state']}>Select a competition to view fixtures.</div>
      </section>
    );
  }

  const hasAnyFixtures = fixtures.previous.length > 0 || fixtures.next.length > 0;

  return (
    <section className={`${styles['lffp-root']} ${className ?? ''}`}>
      {/* Panel header */}
      <div className={styles['lffp-panel-header']}>
        <h2 className={styles['lffp-title']}>{title}</h2>
        <p className={styles['lffp-competition-meta']}>
          {fixtures.competition.name}
          {fixtures.competition.area_name ? ` · ${fixtures.competition.area_name}` : ''}
          {fixtures.season_label ? ` · ${fixtures.season_label}` : ''}
        </p>
      </div>

      {!hasAnyFixtures ? (
        <div className={styles['lffp-state']}>
          No fixtures are available for this competition yet.
        </div>
      ) : (
        <div className={styles['lffp-columns']}>
          <FixtureListSection
            title={previousTitle}
            fixtures={fixtures.previous}
            emptyMessage="No previous fixtures found."
            predictions={predictions}
            predictionsLoading={predictionsLoading}
          />
          <FixtureListSection
            title={nextTitle}
            fixtures={fixtures.next}
            emptyMessage="No upcoming fixtures found."
            predictions={predictions}
            predictionsLoading={predictionsLoading}
          />
        </div>
      )}
    </section>
  );
};

export default FixturesPanel;
