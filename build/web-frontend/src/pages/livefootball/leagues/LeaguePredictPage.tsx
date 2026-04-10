import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import CommentaryPanel from '../../../components/livefootball/leagues/CommentaryPanel';
import LeagueSelector from '../../../components/livefootball/leagues/LeagueSelector';
import MatchweekSelector from '../../../components/livefootball/leagues/MatchweekSelector';
import PredictionSummary from '../../../components/livefootball/leagues/PredictionSummary';
import SeasonSelector from '../../../components/livefootball/leagues/SeasonSelector';
import liveFootballApi from '../../../services/api/livefootballApi';
import type {
  LeagueExpectedTableResponse,
  LeagueMetaItem,
  LeaguesMetaResponse,
} from '../../../types/livefootball';
import styles from './css/LeagueComparePage.module.css';

type ProjectionMode = 'current_expected' | 'pre_season' | 'as_of_matchweek';

const MODE_LABELS: Record<ProjectionMode, string> = {
  current_expected: 'Current expected',
  pre_season: 'Pre-season',
  as_of_matchweek: 'As of matchweek',
};

const MODE_ORDER: ProjectionMode[] = ['current_expected', 'pre_season', 'as_of_matchweek'];
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

const parsePositiveInteger = (value: string | null): number | null => {
  if (!value) {
    return null;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }

  return parsed;
};

const LeaguePredictPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [meta, setMeta] = useState<LeaguesMetaResponse | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);

  const [prediction, setPrediction] = useState<LeagueExpectedTableResponse | null>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const loadMeta = async (): Promise<void> => {
      try {
        setMetaLoading(true);
        setMetaError(null);

        const payload = await liveFootballApi.getLeaguesMeta();

        if (!isActive) {
          return;
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

  const selectedMode = useMemo<ProjectionMode | null>(() => {
    if (!selectedLeague || !selectedSeason) {
      return null;
    }

    const unavailableMap = new Map(
      selectedLeague.unavailable_modes.map((item: UnavailableMode) => [item.mode, item.reason])
    );

    const supported = MODE_ORDER.filter((mode) => {
      if (!selectedLeague.supported_modes.includes(mode)) {
        return false;
      }

      if (unavailableMap.has(mode)) {
        return false;
      }

      return true;
    });

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
  }, [selectedLeague, selectedSeason, searchParams]);

  const selectedMatchweek = useMemo<number>(() => {
    const parsed = parsePositiveInteger(searchParams.get('matchweek'));
    return parsed ?? 1;
  }, [searchParams]);

  useEffect(() => {
    if (!selectedLeague || !selectedSeason || !selectedMode) {
      return;
    }

    const currentCompetition = searchParams.get('competition');
    const currentSeason = searchParams.get('season');
    const currentMode = searchParams.get('mode');
    const currentMatchweek = searchParams.get('matchweek');

    const expectedMatchweek =
      selectedMode === 'as_of_matchweek' ? String(selectedMatchweek) : null;

    if (
      currentCompetition === String(selectedLeague.id) &&
      currentSeason === selectedSeason &&
      currentMode === selectedMode &&
      currentMatchweek === expectedMatchweek
    ) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('competition', String(selectedLeague.id));
    nextParams.set('season', selectedSeason);
    nextParams.set('mode', selectedMode);

    if (selectedMode === 'as_of_matchweek') {
      nextParams.set('matchweek', String(selectedMatchweek));
    } else {
      nextParams.delete('matchweek');
    }

    setSearchParams(nextParams, { replace: true });
  }, [searchParams, selectedLeague, selectedSeason, selectedMode, selectedMatchweek, setSearchParams]);

  useEffect(() => {
    if (!selectedLeague || !selectedSeason || !selectedMode) {
      setPrediction(null);
      setPredictionError(null);
      setPredictionLoading(false);
      return;
    }

    let isActive = true;

    const loadPrediction = async (): Promise<void> => {
      try {
        setPredictionLoading(true);
        setPredictionError(null);

        const payload = await liveFootballApi.getLeagueExpectedTable(selectedLeague.id, {
          season: selectedSeason,
          mode: selectedMode,
          matchweek: selectedMode === 'as_of_matchweek' ? selectedMatchweek : undefined,
        });

        if (!isActive) {
          return;
        }

        setPrediction(payload);
      } catch (error) {
        if (!isActive) {
          return;
        }

        setPrediction(null);
        setPredictionError(normalizeError(error));
      } finally {
        if (isActive) {
          setPredictionLoading(false);
        }
      }
    };

    void loadPrediction();

    return () => {
      isActive = false;
    };
  }, [selectedLeague, selectedSeason, selectedMode, selectedMatchweek]);

  const handleLeagueChange = (competitionId: number): void => {
    const nextLeague = leagues.find((league: LeagueMetaItem) => league.id === competitionId);
    const currentSeasonParam = searchParams.get('season');
    const nextSeason =
      currentSeasonParam && nextLeague?.available_seasons.includes(currentSeasonParam)
        ? currentSeasonParam
        : nextLeague?.available_seasons[0] ?? '';
    const unavailableMap = new Map(
      (nextLeague?.unavailable_modes ?? []).map((item: UnavailableMode) => [item.mode, item.reason])
    );

    const supportedModes = MODE_ORDER.filter((mode) => {
      if (!(nextLeague?.supported_modes ?? []).includes(mode)) {
        return false;
      }

      if (unavailableMap.has(mode)) {
        return false;
      }

      return true;
    });

    const currentModeParam = searchParams.get('mode') as ProjectionMode | null;
    const nextMode =
      currentModeParam && supportedModes.includes(currentModeParam)
        ? currentModeParam
        : supportedModes.includes('current_expected')
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

    if (nextMode === 'as_of_matchweek') {
      nextParams.set('matchweek', searchParams.get('matchweek') ?? '1');
    } else {
      nextParams.delete('matchweek');
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

    if (mode === 'as_of_matchweek') {
      if (!nextParams.get('matchweek')) {
        nextParams.set('matchweek', '1');
      }
    } else {
      nextParams.delete('matchweek');
    }

    setSearchParams(nextParams);
  };

  const handleMatchweekChange = (matchweek: number): void => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('matchweek', String(matchweek));
    setSearchParams(nextParams);
  };

  const unavailableModeReasons = useMemo(() => {
    return new Map(
      (selectedLeague?.unavailable_modes ?? []).map((item: UnavailableMode) => [item.mode, item.reason])
    );
  }, [selectedLeague]);

  const filtersReady = Boolean(selectedLeague && selectedSeason && selectedMode);
  const totalMatchweeks = prediction?.metadata.total_matchweeks ?? null;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleBlock}>
          <h1 className={styles.title}>League predictions</h1>
          <p className={styles.subtitle}>
            Explore expected league outcomes, probabilities, and deterministic commentary for a selected league and season.
          </p>
        </div>

        <div className={styles.actions}>
          <Link
            to={
              selectedLeague && selectedSeason
                ? `/livefootball/leagues/compare?competition=${selectedLeague.id}&season=${selectedSeason}&mode=${selectedMode ?? 'current_expected'}`
                : '/livefootball/leagues/compare'
            }
            className={styles.secondaryLink}
          >
            Open comparison page
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

          {selectedMode === 'as_of_matchweek' ? (
            <MatchweekSelector
              value={selectedMatchweek}
              onChange={handleMatchweekChange}
              disabled={metaLoading || !selectedLeague}
              maxMatchweek={totalMatchweeks}
            />
          ) : null}
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

          {selectedMode === 'as_of_matchweek' ? (
            <p className={styles.stateText}>
              {totalMatchweeks
                ? `Select a historical cut-point between matchweek 1 and ${totalMatchweeks}.`
                : 'Select a historical matchweek cut-point for this completed season.'}
            </p>
          ) : null}
        </div>
      </section>

      {metaLoading ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>Loading predictions</h2>
          <p className={styles.stateText}>Fetching leagues and available seasons.</p>
        </section>
      ) : null}

      {!metaLoading && metaError ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>Predictions unavailable</h2>
          <p className={styles.stateText}>{metaError}</p>
        </section>
      ) : null}

      {!metaLoading && !metaError && !filtersReady ? (
        <section className={styles.stateCard}>
          <h2 className={styles.stateTitle}>No prediction options available</h2>
          <p className={styles.stateText}>
            No supported league, season, and mode combination is currently available.
          </p>
        </section>
      ) : null}

      {!metaLoading && !metaError && filtersReady ? (
        <>
          {predictionLoading ? (
            <section className={styles.stateCard}>
              <h2 className={styles.stateTitle}>Loading expected table</h2>
              <p className={styles.stateText}>Running the projection and loading commentary.</p>
            </section>
          ) : null}

          {!predictionLoading && predictionError ? (
            <section className={styles.stateCard}>
              <h2 className={styles.stateTitle}>Could not load prediction</h2>
              <p className={styles.stateText}>{predictionError}</p>
            </section>
          ) : null}

          {!predictionLoading && !predictionError && prediction ? (
            <>
              <PredictionSummary payload={prediction} />
              <CommentaryPanel commentary={prediction.commentary} />
            </>
          ) : null}
        </>
      ) : null}
    </main>
  );
};

export default LeaguePredictPage;