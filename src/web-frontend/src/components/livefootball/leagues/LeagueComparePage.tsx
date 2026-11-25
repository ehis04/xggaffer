import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import CommentaryPanel from './CommentaryPanel';
import ComparisonMetrics from './ComparisonMetrics';
import ComparisonTable from './ComparisonTable';
import LeagueSelector from './LeagueSelector';
import SeasonSelector from './SeasonSelector';
import liveFootballApi from '../../../services/api/livefootballApi';
import type {
  LeagueCompareResponse,
  LeagueMetaItem,
  LeaguesMetaResponse,
} from '../../../types/livefootball';
import styles from './css/LeagueComparePage.module.css';

type ProjectionMode = 'current_expected' | 'pre_season';

const MODE_LABELS: Record<ProjectionMode, string> = {
  current_expected: 'Current expected',
  pre_season: 'Pre-season',
};

const MODE_ORDER: ProjectionMode[] = ['current_expected', 'pre_season'];
type UnavailableMode = LeagueMetaItem['unavailable_modes'][number];

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

const LeagueComparePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [meta, setMeta] = useState<LeaguesMetaResponse | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);

  const [comparison, setComparison] = useState<LeagueCompareResponse | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const loadMeta = async (): Promise<void> => {
      try {
        setMetaLoading(true);
        setMetaError(null);

        const envelope = await liveFootballApi.getLeaguesMeta();

        if (!isActive) {
          return;
        }

        const payload = envelope.data;
        if (!payload) {
          throw new Error('No league metadata available.');
        }

        setMeta(payload);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setMeta(null);
        setMetaError(normalizeError(error));
      } finally {
        if (isActive) {
          setMetaLoading(false);
        }
      }
    };

    void loadMeta();

    return () => {
      isActive = false;
    };
  }, []);

  const leagues = useMemo(() => meta?.leagues ?? [], [meta?.leagues]);

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

  const selectedMode = useMemo<ProjectionMode | null>(() => {
    if (!selectedLeague) {
      return null;
    }

    const unavailableMap = new Map(
      selectedLeague.unavailable_modes.map((item: UnavailableMode) => [item.mode, item.reason])
    );

    const supported = MODE_ORDER.filter(
      (mode) => selectedLeague.supported_modes.includes(mode) && !unavailableMap.has(mode)
    );

    if (supported.length === 0) {
      return null;
    }

    const modeParam = searchParams.get('mode') as ProjectionMode | null;
    if (modeParam && supported.includes(modeParam)) {
      return modeParam;
    }

    if (supported.includes('current_expected')) {
      return 'current_expected';
    }

    return supported[0];
  }, [selectedLeague, searchParams]);

  useEffect(() => {
    if (!selectedLeague || !selectedSeason || !selectedMode) {
      return;
    }

    const currentCompetition = searchParams.get('competition');
    const currentSeason = searchParams.get('season');
    const currentMode = searchParams.get('mode');

    if (
      currentCompetition === String(selectedLeague.id) &&
      currentSeason === selectedSeason &&
      currentMode === selectedMode
    ) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('competition', String(selectedLeague.id));
    nextParams.set('season', selectedSeason);
    nextParams.set('mode', selectedMode);
    setSearchParams(nextParams, { replace: true });
  }, [searchParams, selectedLeague, selectedSeason, selectedMode, setSearchParams]);

  useEffect(() => {
    if (!selectedLeague || !selectedSeason || !selectedMode) {
      setComparison(null);
      setComparisonError(null);
      setComparisonLoading(false);
      return;
    }

    let isActive = true;

    const loadComparison = async (): Promise<void> => {
      try {
        setComparisonLoading(true);
        setComparisonError(null);

        const envelope = await liveFootballApi.getLeagueComparison(selectedLeague.id, {
          season: selectedSeason,
          mode: selectedMode,
        });

        const payload = envelope.data;
        if (!payload) {
          throw new Error('No league comparison data available.');
        }

        if (!isActive) {
          return;
        }

        setComparison(payload);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setComparison(null);
        setComparisonError(normalizeError(error));
      } finally {
        if (isActive) {
          setComparisonLoading(false);
        }
      }
    };

    void loadComparison();

    return () => {
      isActive = false;
    };
  }, [selectedLeague, selectedSeason, selectedMode]);

  const handleLeagueChange = (competitionId: number): void => {
    const nextLeague = leagues.find((league: LeagueMetaItem) => league.id === competitionId);
    const nextSeason = nextLeague?.available_seasons[0] ?? '';

    const supportedModes = nextLeague?.supported_modes ?? [];
    const nextMode = supportedModes.includes('current_expected')
      ? 'current_expected'
      : supportedModes[0] ?? '';

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('competition', String(competitionId));

    if (nextSeason) {
      nextParams.set('season', nextSeason);
    } else {
      nextParams.delete('season');
    }

    if (nextMode) {
      nextParams.set('mode', nextMode);
    } else {
      nextParams.delete('mode');
    }

    setSearchParams(nextParams);
  };

  const handleSeasonChange = (season: string): void => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('season', season);
    setSearchParams(nextParams);
  };

  const handleModeChange = (mode: ProjectionMode): void => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('mode', mode);
    setSearchParams(nextParams);
  };

  const unavailableModeReasons = useMemo(() => {
    return new Map(
      (selectedLeague?.unavailable_modes ?? []).map((item: UnavailableMode) => [item.mode, item.reason])
    );
  }, [selectedLeague]);

  const filtersReady = Boolean(selectedLeague && selectedSeason && selectedMode);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleBlock}>
          <h1 className={styles.title}>League comparison</h1>
          <p className={styles.subtitle}>
            Compare actual standings against the model’s expected table and inspect the key deltas.
          </p>
        </div>

        <div className={styles.actions}>
          <Link
            to={
              selectedLeague && selectedSeason
                ? `/livefootball/leagues?competition=${selectedLeague.id}&season=${selectedSeason}`
                : '/livefootball/leagues'
            }
            className={styles.secondaryLink}
          >
            Back to leagues
          </Link>

          <button
            type="button"
            className={styles.disabledButton}
            disabled
            title="Saved scenarios are planned for Release 2."
          >
            Save scenario
          </button>
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

        <div className={styles.modeBlock}>
          <span className={styles.modeLabel}>Prediction mode</span>

          <div className={styles.modeButtons}>
            {MODE_ORDER.map((mode) => {
              const isSupported = selectedLeague?.supported_modes.includes(mode) ?? false;
              const reason = unavailableModeReasons.get(mode);
              const disabled = !isSupported || Boolean(reason);

              return (
                <button
                  key={mode}
                  type="button"
                  className={`${styles.modeButton} ${selectedMode === mode ? styles.modeButtonActive : ''}`}
                  onClick={() => handleModeChange(mode)}
                  disabled={disabled}
                  title={reason || (disabled ? 'This mode is unavailable for this league.' : '')}
                >
                  {MODE_LABELS[mode]}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {metaLoading ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>Loading comparison</h2>
          <p className={styles.stateText}>Fetching leagues and available seasons.</p>
        </section>
      ) : null}

      {!metaLoading && metaError ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>Comparison unavailable</h2>
          <p className={styles.stateText}>{metaError}</p>
        </section>
      ) : null}

      {!metaLoading && !metaError && !filtersReady ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>No comparison options available</h2>
          <p className={styles.stateText}>
            No supported league, season, and mode combination is currently available.
          </p>
        </section>
      ) : null}

      {!metaLoading && !metaError && filtersReady ? (
        <>
          {comparisonLoading ? (
            <section className={styles.stateCard}>
              <h2 className={styles.stateTitle}>Loading model comparison</h2>
              <p className={styles.stateText}>Fetching actual and expected tables.</p>
            </section>
          ) : null}

          {!comparisonLoading && comparisonError ? (
            <section className={styles.stateCard}>
              <h2 className={styles.stateTitle}>Could not load comparison</h2>
              <p className={styles.stateText}>{comparisonError}</p>
            </section>
          ) : null}

          {!comparisonLoading && !comparisonError && comparison ? (
            <>
              <ComparisonTable
                actualRows={comparison.actual_table}
                expectedRows={comparison.expected_table}
                mode={comparison.mode}
                metadata={comparison.metadata}
              />

              <ComparisonMetrics
                deltas={comparison.deltas}
                comparisonMetrics={comparison.comparison_metrics}
              />

              <CommentaryPanel commentary={comparison.commentary} />
            </>
          ) : null}
        </>
      ) : null}
    </main>
  );
};

export default LeagueComparePage;
