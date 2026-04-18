import React, { useEffect, useMemo, useState } from 'react';
import CompetitionSelector from '../../components/livefootball/CompetitionSelector';
import FixturesPanel from '../../components/livefootball/FixturesPanel';
import LeagueTable from '../../components/livefootball/LeagueTable';
import TopScorersPanel from '../../components/livefootball/TopScorersPanel';
import liveFootballApi from '../../services/api/livefootballApi';
import styles from './css/LiveFootballPage.module.css';
import type {
  CompetitionListItem,
  CompetitionPreviousNextFixturesResponse,
  CompetitionTableResponse,
  CompetitionTopScorersResponse,
} from '../../types/livefootball';

const normalizeError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object') {
    const values = Object.values(error as Record<string, unknown>).flatMap((value) => {
      if (Array.isArray(value)) {
        return value.map(String);
      }

      if (value === null || value === undefined) {
        return [];
      }

      return [String(value)];
    });

    if (values.length > 0) {
      return values.join(' ');
    }
  }

  return 'Something went wrong.';
};


const LiveFootballPage: React.FC = () => {
  const [competitions, setCompetitions] = useState<CompetitionListItem[]>([]);
  const [competitionsLoading, setCompetitionsLoading] = useState(true);
  const [competitionsError, setCompetitionsError] = useState<string | null>(null);

  const [selectedCompetitionId, setSelectedCompetitionId] = useState<number | null>(null);

  const [table, setTable] = useState<CompetitionTableResponse | null>(null);
  const [tableLoading, setTableLoading] = useState(false);
  const [tableError, setTableError] = useState<string | null>(null);

  const [fixtures, setFixtures] = useState<CompetitionPreviousNextFixturesResponse | null>(null);
  const [fixturesLoading, setFixturesLoading] = useState(false);
  const [fixturesError, setFixturesError] = useState<string | null>(null);

  const [scorers, setScorers] = useState<CompetitionTopScorersResponse | null>(null);
  const [scorersLoading, setScorersLoading] = useState(false);
  const [scorersError, setScorersError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const loadCompetitions = async () => {
      try {
        setCompetitionsLoading(true);
        setCompetitionsError(null);

        const items = await liveFootballApi.getCompetitions();

        if (!isActive) {
          return;
        }

        setCompetitions(items);

        setSelectedCompetitionId((currentId) => {
          if (currentId && items.some((item) => item.id === currentId)) {
            return currentId;
          }

          return items[0]?.id ?? null;
        });
      } catch (error) {
        if (!isActive) {
          return;
        }

        setCompetitions([]);
        setCompetitionsError(normalizeError(error));
      } finally {
        if (isActive) {
          setCompetitionsLoading(false);
        }
      }
    };

    loadCompetitions();

    return () => {
      isActive = false;
    };
  }, []);

  const selectedCompetition = useMemo(
    () => competitions.find((competition) => competition.id === selectedCompetitionId) ?? null,
    [competitions, selectedCompetitionId]
  );

  useEffect(() => {
    if (!selectedCompetition) {
      setTable(null);
      setFixtures(null);
      setScorers(null);
      setTableError(null);
      setFixturesError(null);
      setScorersError(null);
      setTableLoading(false);
      setFixturesLoading(false);
      setScorersLoading(false);
      return;
    }

    let isActive = true;
    const season = selectedCompetition.current_season_label ?? undefined;

    const loadBrowseData = async () => {
      setTableLoading(true);
      setFixturesLoading(true);
      setScorersLoading(true);

      setTableError(null);
      setFixturesError(null);
      setScorersError(null);

      const [tableResult, fixturesResult, scorersResult] = await Promise.allSettled([
        liveFootballApi.getCompetitionTable(selectedCompetition.id, {
          season,
        }),
        liveFootballApi.getCompetitionPreviousNextFixtures(selectedCompetition.id, {
          season,
          previous_limit: 5,
          next_limit: 5,
        }),
        liveFootballApi.getCompetitionScorers(selectedCompetition.id, {
          season,
          limit: 10,
        }),
      ]);

      if (!isActive) {
        return;
      }

      if (tableResult.status === 'fulfilled') {
        setTable(tableResult.value);
        setTableError(null);
      } else {
        setTable(null);
        setTableError(normalizeError(tableResult.reason));
      }

      if (fixturesResult.status === 'fulfilled') {
        setFixtures(fixturesResult.value);
        setFixturesError(null);
      } else {
        setFixtures(null);
        setFixturesError(normalizeError(fixturesResult.reason));
      }

      if (scorersResult.status === 'fulfilled') {
        setScorers(scorersResult.value);
        setScorersError(null);
      } else {
        setScorers(null);
        setScorersError(normalizeError(scorersResult.reason));
      }

      setTableLoading(false);
      setFixturesLoading(false);
      setScorersLoading(false);
    };

    loadBrowseData();

    return () => {
      isActive = false;
    };
  }, [selectedCompetition]);

  const handleCompetitionChange = (competition: CompetitionListItem | null) => {
    setSelectedCompetitionId(competition?.id ?? null);
  };

  const hasCompetitions = competitions.length > 0;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Live Football</h1>
          <p className={styles.subtitle}>
            Browse league tables, recent and upcoming fixtures, and top scorers.
          </p>
        </div>

        <CompetitionSelector
          competitions={competitions}
          value={selectedCompetitionId}
          onChange={handleCompetitionChange}
          loading={competitionsLoading}
          error={competitionsError}
          helperText="Choose a competition to view its latest available table, fixtures, and scorers."
          emptyStateText="No competitions are available yet."
          className={styles.selectorCard}
        />
      </header>

      {!competitionsLoading && !hasCompetitions && !competitionsError ? (
        <section className={styles.emptyState}>
          <h2 className={styles.sectionTitle}>No competition data yet</h2>
          <p>
            Sync football-data into the backend, then refresh this page.
          </p>
        </section>
      ) : null}

      {selectedCompetition ? (
        <section className={styles.competitionSummary}>
          <h2 className={styles.sectionTitle}>{selectedCompetition.name}</h2>
          <p className={styles.metaText}>
            {selectedCompetition.area_name || 'Unknown area'}
            {selectedCompetition.current_season_label
              ? ` · ${selectedCompetition.current_season_label}`
              : ''}
          </p>
        </section>
      ) : null}

      <LeagueTable
        table={table}
        isLoading={tableLoading}
        error={tableError}
        title="League table"
        className={styles.panel}
      />

      <FixturesPanel
        fixtures={fixtures}
        isLoading={fixturesLoading}
        error={fixturesError}
        title="Fixtures"
        previousTitle="Recent results"
        nextTitle="Upcoming fixtures"
        className={styles.panel}
      />

      <TopScorersPanel
        scorers={scorers}
        isLoading={scorersLoading}
        error={scorersError}
        title="Top scorers"
        maxItems={10}
        className={styles.panel}
      />
    </div>
  );
};

export default LiveFootballPage;