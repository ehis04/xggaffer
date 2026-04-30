import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../../../common/query/queryKeys';
import { STALE_TIME_STANDARD } from '../../../common/query/queryClient';
import { Link, useSearchParams } from 'react-router-dom';
import LeagueSelector from '../../../components/livefootball/leagues/LeagueSelector';
import LeagueTable from '../../../components/livefootball/leagues/LeagueTable';
import SeasonSelector from '../../../components/livefootball/leagues/SeasonSelector';
import liveFootballApi from '../../../services/api/livefootballApi';
import type {
  CompetitionTableResponse,
  LeagueMetaItem,
} from '../../../types/livefootball';
import styles from './css/LeaguesPage.module.css';
import { FreshnessBadge } from '../../../common/components/FreshnessBadge';

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

const LeaguesPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const { data: metaEnvelope, isPending: metaLoading, isError: metaErrored } = useQuery({
    queryKey: queryKeys.livefootball.leaguesMeta(),
    queryFn: () => liveFootballApi.getLeaguesMeta(),
    staleTime: STALE_TIME_STANDARD,
  });
  const meta = metaEnvelope?.data ?? null;

  const [table, setTable] = useState<CompetitionTableResponse | null>(null);
  const [tableLoading, setTableLoading] = useState(false);
  const [tableError, setTableError] = useState<string | null>(null);

  const leagues = meta?.leagues ?? [];

  const selectedLeague = useMemo<LeagueMetaItem | null>(() => {
    if (leagues.length === 0) {
      return null;
    }

    const competitionParam = Number(searchParams.get('competition'));
    if (Number.isFinite(competitionParam)) {
      const match = leagues.find((league: LeagueMetaItem) => league.id === competitionParam);
      if (match) {
        return match;
      }
    }

    return leagues[0];
  }, [leagues, searchParams]);

  const selectedSeason = useMemo<string | null>(() => {
    if (!selectedLeague) {
      return null;
    }

    const seasonParam = searchParams.get('season');
    if (seasonParam && selectedLeague.available_seasons.includes(seasonParam)) {
      return seasonParam;
    }

    return selectedLeague.available_seasons[0] ?? null;
  }, [selectedLeague, searchParams]);

  useEffect(() => {
    if (!selectedLeague || !selectedSeason) {
      return;
    }

    const currentCompetition = searchParams.get('competition');
    const currentSeason = searchParams.get('season');

    if (
      currentCompetition === String(selectedLeague.id) &&
      currentSeason === selectedSeason
    ) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('competition', String(selectedLeague.id));
    nextParams.set('season', selectedSeason);
    setSearchParams(nextParams, { replace: true });
  }, [searchParams, selectedLeague, selectedSeason, setSearchParams]);

  useEffect(() => {
    if (!selectedLeague || !selectedSeason) {
      setTable(null);
      setTableError(null);
      setTableLoading(false);
      return;
    }

    let isActive = true;

    const loadTable = async (): Promise<void> => {
      try {
        setTableLoading(true);
        setTableError(null);

        const payload = await liveFootballApi.getCompetitionTable(selectedLeague.id, {
          season: selectedSeason,
        });

        if (!isActive) {
          return;
        }

        setTable(payload);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setTable(null);
        setTableError(normalizeError(error));
      } finally {
        if (isActive) {
          setTableLoading(false);
        }
      }
    };

    void loadTable();

    return () => {
      isActive = false;
    };
  }, [selectedLeague, selectedSeason]);

  const handleLeagueChange = (competitionId: number): void => {
    const nextLeague = leagues.find((league: LeagueMetaItem) => league.id === competitionId);
    const currentSeasonParam = searchParams.get('season');
    const nextSeason =
      currentSeasonParam && nextLeague?.available_seasons.includes(currentSeasonParam)
        ? currentSeasonParam
        : nextLeague?.available_seasons[0] ?? '';

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('competition', String(competitionId));

    if (nextSeason) {
      nextParams.set('season', nextSeason);
    } else {
      nextParams.delete('season');
    }

    setSearchParams(nextParams);
  };

  const handleSeasonChange = (season: string): void => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('season', season);
    setSearchParams(nextParams);
  };

  const compareHref =
    selectedLeague && selectedSeason
      ? `/livefootball/leagues/compare?competition=${selectedLeague.id}&season=${selectedSeason}&mode=current_expected`
      : '/livefootball/leagues/compare';

  const metaLabel = [
    table?.season_label ?? selectedSeason,
    table?.matchday ? `Matchday ${table.matchday}` : null,
    table?.synced_at ? `Updated ${new Date(table.synced_at).toLocaleString()}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  const predictHref =
    selectedLeague && selectedSeason
      ? `/livefootball/leagues/predict?competition=${selectedLeague.id}&season=${selectedSeason}&mode=current_expected`
      : '/livefootball/leagues/predict';

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleBlock}>
          <h1 className={styles.title}>Leagues</h1>
          <p className={styles.subtitle}>
            Browse current and historical tables across the five supported leagues.
          </p>
        </div>
        <FreshnessBadge freshness={metaEnvelope?.freshness} />

        <div className={styles.actions}>
          <Link to={predictHref} className={styles.compareButton}>
            Open predictions
          </Link>
          <Link to={compareHref} className={styles.compareButton}>
            Compare with predictions
          </Link>
        </div>
      </header>

      <section className={styles.filtersCard}>
        <div className={styles.filtersRow}>
          <LeagueSelector
            leagues={leagues}
            value={selectedLeague?.id ?? null}
            onChange={handleLeagueChange}
            disabled={metaLoading || leagues.length === 0}
          />

          <SeasonSelector
            seasons={selectedLeague?.available_seasons ?? []}
            value={selectedSeason}
            onChange={handleSeasonChange}
            disabled={metaLoading || !selectedLeague}
          />
        </div>

        {selectedLeague ? (
          <p className={styles.helperText}>
            Available seasons for {selectedLeague.name}: {selectedLeague.available_seasons.join(', ')}
          </p>
        ) : null}
      </section>

      {metaLoading ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>Loading leagues</h2>
          <p className={styles.stateText}>
            Fetching the available leagues and seasons.
          </p>
        </section>
      ) : null}

      {!metaLoading && metaErrored ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>Leagues unavailable</h2>
          <p className={styles.stateText}>Failed to load league metadata.</p>
        </section>
      ) : null}

      {!metaLoading && !metaErrored && leagues.length === 0 ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>No leagues available</h2>
          <p className={styles.stateText}>
            No synced league metadata is available yet.
          </p>
        </section>
      ) : null}

      {!metaLoading && !metaErrored && selectedLeague ? (
        <section className={styles.tableCard}>
          <div className={styles.tableHeader}>
            <div>
              <h2 className={styles.tableTitle}>{selectedLeague.name}</h2>
              <p className={styles.tableMeta}>{metaLabel || 'No season metadata available.'}</p>
            </div>
          </div>

          {tableLoading ? (
            <div className={styles.stateInline}>Loading league table…</div>
          ) : null}

          {!tableLoading && tableError ? (
            <div className={styles.stateInline}>{tableError}</div>
          ) : null}

          {!tableLoading && !tableError ? (
            <LeagueTable
              rows={table?.rows ?? []}
              title="League table"
              emptyMessage="No table rows are available for this league and season."
            />
          ) : null}
        </section>
      ) : null}
    </main>
  );
};

export default LeaguesPage;