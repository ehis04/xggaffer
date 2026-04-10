import React from 'react';
import type {
  CompetitionFixtureItem,
  CompetitionPreviousNextFixturesResponse,
} from '../../types/livefootball';

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

interface FixtureListSectionProps {
  title: string;
  fixtures: CompetitionFixtureItem[];
  emptyMessage: string;
}

const FixtureListSection: React.FC<FixtureListSectionProps> = ({
  title,
  fixtures,
  emptyMessage,
}) => {
  return (
    <section>
      <h3>{title}</h3>

      {fixtures.length === 0 ? (
        <div>{emptyMessage}</div>
      ) : (
        <div>
          {fixtures.map((fixture) => (
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
                  gap: '0.75rem',
                  flexWrap: 'wrap',
                  marginBottom: '0.5rem',
                }}
              >
                <strong>
                  {getTeamLabel(fixture.home_team)} v {getTeamLabel(fixture.away_team)}
                </strong>

                <span>{formatStatus(fixture.status)}</span>
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
          ))}
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
          />

          <FixtureListSection
            title={nextTitle}
            fixtures={fixtures.next}
            emptyMessage="No upcoming fixtures found."
          />
        </div>
      )}
    </section>
  );
};

export default FixturesPanel;