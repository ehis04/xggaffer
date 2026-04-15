import React, { useState, useEffect } from 'react';
import type {
  CompetitionFixtureItem,
  CompetitionPreviousNextFixturesResponse,
} from '../../types/livefootball';
import { predictMatch } from '../../services/api/predictionsApi';
import MatchPredictionChip from '../predictions/MatchPredictionChip';

const COMPETITION_CODE_TO_LEAGUE: Record<string, string> = {
  PL:  'EPL',
  PD:  'La_Liga',
  BL1: 'Bundesliga',
  SA:  'Serie_A',
  FL1: 'Ligue_1',
};

const parseSeasonYear = (label: string): string =>
  label.match(/\d{4}/)?.[0] ?? '2024';

const formatKickoff = (value?: string | null): string => {
  if (!value) {
    return 'Kick-off not available';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Kick-off not available';
  }

  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

const formatStatus = (status?: string | null): string => {
  const value = (status || '').trim();

  if (!value) {
    return 'Unknown';
  }

  const knownLabels: Record<string, string> = {
    FINISHED: 'Finished',
    AWARDED: 'Awarded',
    AFTER_EXTRA_TIME: 'After extra time',
    PENALTY_SHOOTOUT: 'Penalties',
    SCHEDULED: 'Scheduled',
    TIMED: 'Timed',
    POSTPONED: 'Postponed',
    SUSPENDED: 'Suspended',
    IN_PLAY: 'In play',
    PAUSED: 'Paused',
    LIVE: 'Live',
  };

  return knownLabels[value] ?? value.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
};

const getTeamLabel = (name: {
  short_name?: string | null;
  tla?: string | null;
  name: string;
}): string => {
  if (name.short_name?.trim()) {
    return name.short_name.trim();
  }

  if (name.tla?.trim()) {
    return name.tla.trim();
  }

  return name.name;
};

const hasScore = (fixture: CompetitionFixtureItem): boolean =>
  fixture.home_score !== null &&
  fixture.home_score !== undefined &&
  fixture.away_score !== null &&
  fixture.away_score !== undefined;

const renderScore = (fixture: CompetitionFixtureItem): string => {
  if (!hasScore(fixture)) {
    return '—';
  }

  return `${fixture.home_score} - ${fixture.away_score}`;
};

const fixtureKey = (fixture: CompetitionFixtureItem): string =>
  `${fixture.home_team.name}|${fixture.away_team.name}|${fixture.kickoff_at}`;

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
}) => {
  return (
    <section>
      <h3>{title}</h3>

      {fixtures.length === 0 ? (
        <div>{emptyMessage}</div>
      ) : (
        <div>
          {fixtures.map((fixture) => {
            const key = fixtureKey(fixture);
            const probs = predictions.get(key);

            return (
              <article
                key={fixture.id || fixture.external_match_id}
                style={{
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '12px',
                  padding: '0.9rem',
                  marginBottom: '0.75rem',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '0.75rem',
                    flexWrap: 'wrap',
                    marginBottom: '0.5rem',
                  }}
                >
                  <strong>
                    {getTeamLabel(fixture.home_team)} v {getTeamLabel(fixture.away_team)}
                  </strong>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <MatchPredictionChip
                      homeProb={probs?.home ?? null}
                      drawProb={probs?.draw ?? null}
                      awayProb={probs?.away ?? null}
                      isLoading={predictionsLoading}
                    />
                    <span>{formatStatus(fixture.status)}</span>
                  </div>
                </div>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr auto 1fr',
                    gap: '0.75rem',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div>
                      <strong>{getTeamLabel(fixture.home_team)}</strong>
                    </div>
                    {fixture.home_team.name !== getTeamLabel(fixture.home_team) ? (
                      <small>{fixture.home_team.name}</small>
                    ) : null}
                  </div>

                  <div style={{ textAlign: 'center' }}>
                    <div>
                      <strong>{renderScore(fixture)}</strong>
                    </div>
                    <small>{formatKickoff(fixture.kickoff_at)}</small>
                    {fixture.matchday ? (
                      <div>
                        <small>MD {fixture.matchday}</small>
                      </div>
                    ) : null}
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div>
                      <strong>{getTeamLabel(fixture.away_team)}</strong>
                    </div>
                    {fixture.away_team.name !== getTeamLabel(fixture.away_team) ? (
                      <small>{fixture.away_team.name}</small>
                    ) : null}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};

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

    const league = COMPETITION_CODE_TO_LEAGUE[fixtures.competition.code ?? ''] ?? null;

    const requests = allFixtures.map((fixture) => {
      if (!league) {
        return Promise.resolve({ key: fixtureKey(fixture), probs: null });
      }
      const season = parseSeasonYear(fixture.season_label);
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
        if (result.status === 'fulfilled') {
          map.set(result.value.key, result.value.probs);
        }
      });
      setPredictions(map);
      setPredictionsLoading(false);
    });
  }, [fixtures]);

  if (isLoading) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div>Loading fixtures…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div role="alert">{error}</div>
      </section>
    );
  }

  if (!fixtures) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div>Select a competition to view fixtures.</div>
      </section>
    );
  }

  const hasAnyFixtures = fixtures.previous.length > 0 || fixtures.next.length > 0;

  return (
    <section className={className}>
      <div style={{ marginBottom: '1rem' }}>
        <h2>{title}</h2>
        <p>
          {fixtures.competition.name}
          {fixtures.competition.area_name ? ` · ${fixtures.competition.area_name}` : ''}
          {fixtures.season_label ? ` · ${fixtures.season_label}` : ''}
        </p>
      </div>

      {!hasAnyFixtures ? (
        <div>No fixtures are available for this competition yet.</div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1rem',
          }}
        >
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