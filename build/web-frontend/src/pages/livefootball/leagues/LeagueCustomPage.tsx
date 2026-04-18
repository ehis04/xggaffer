import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import CommentaryPanel from '../../../components/livefootball/leagues/CommentaryPanel';
import LeagueSelector from '../../../components/livefootball/leagues/LeagueSelector';
import LeagueTable from '../../../components/livefootball/leagues/LeagueTable';
import MatchweekSelector from '../../../components/livefootball/leagues/MatchweekSelector';
import PredictionSummary from '../../../components/livefootball/leagues/PredictionSummary';
import SeasonSelector from '../../../components/livefootball/leagues/SeasonSelector';
import liveFootballApi from '../../../services/api/livefootballApi';
import type {
  CreateSavedLeagueScenarioPayload,
  LeagueScenarioLockedResultInput,
  LeagueScenarioResponse,
  LeagueMetaItem,
  LeaguesMetaResponse,
  LeagueTableRow,
  SavedLeagueScenarioDetail,
  SavedLeagueScenarioListItem,
} from '../../../types/livefootball';
import pageStyles from './css/LeagueComparePage.module.css';
import styles from './css/LeagueCustomPage.module.css';

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

type ScoreInputState = Record<
  string,
  {
    home_goals: string;
    away_goals: string;
  }
>;

const toExpectedLeagueRows = (payload: LeagueScenarioResponse | null): LeagueTableRow[] => {
  if (!payload) {
    return [];
  }

  return payload.expected_table.map((row) => {
    const played = Math.round(row.simulated_wins + row.simulated_draws + row.simulated_losses);
    const goalsFor = Math.round(row.simulated_goals_for);
    const goalsAgainst = Math.round(row.simulated_goals_against);

    return {
      position: row.predicted_position,
      team: row.team,
      played,
      won: Math.round(row.simulated_wins),
      drawn: Math.round(row.simulated_draws),
      lost: Math.round(row.simulated_losses),
      goals_for: goalsFor,
      goals_against: goalsAgainst,
      goal_difference: goalsFor - goalsAgainst,
      points: Math.round(row.predicted_points),
      form: '',
    };
  });
};

const LeagueCustomPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [meta, setMeta] = useState<LeaguesMetaResponse | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);

  const [scenario, setScenario] = useState<LeagueScenarioResponse | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [savedScenarios, setSavedScenarios] = useState<SavedLeagueScenarioListItem[]>([]);
  const [savedScenariosLoading, setSavedScenariosLoading] = useState(false);
  const [savedScenariosError, setSavedScenariosError] = useState<string | null>(null);
  const [saveTitle, setSaveTitle] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const [saveSubmitting, setSaveSubmitting] = useState(false);
  const [savedScenarioActionId, setSavedScenarioActionId] = useState<number | null>(null);

  const [scoreInputs, setScoreInputs] = useState<ScoreInputState>({});
  const [selectedTeamName, setSelectedTeamName] = useState<string | null>(null);

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

  const seasonAllowsAsOfMatchweek = useMemo<boolean>(() => {
    if (!selectedLeague || !selectedSeason) {
      return false;
    }

    return selectedSeason !== (selectedLeague.current_season_label ?? '');
  }, [selectedLeague, selectedSeason]);

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

      if (mode === 'as_of_matchweek' && !seasonAllowsAsOfMatchweek) {
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
  }, [selectedLeague, selectedSeason, searchParams, seasonAllowsAsOfMatchweek]);

  const selectedMatchweek = useMemo<number>(() => {
    const parsed = parsePositiveInteger(searchParams.get('matchweek'));
    return parsed ?? 1;
  }, [searchParams]);

  const handleRemoveScore = useCallback((fixtureKey: string): void => {
    setScoreInputs((current) => {
      const { [fixtureKey]: _removed, ...rest } = current;
      return rest;
    });
  }, []);

  const buildLockedResults = useCallback((): LeagueScenarioLockedResultInput[] => {
    return Object.entries(scoreInputs).flatMap(([fixture_key, values]) => {
      const home_goals = values.home_goals.trim();
      const away_goals = values.away_goals.trim();

      if (home_goals === '' || away_goals === '') {
        return [];
      }

      const parsedHome = Number(home_goals);
      const parsedAway = Number(away_goals);

      if (!Number.isInteger(parsedHome) || !Number.isInteger(parsedAway) || parsedHome < 0 || parsedAway < 0) {
        return [];
      }

      return [{ fixture_key, home_goals: parsedHome, away_goals: parsedAway }];
    });
  }, [scoreInputs]);

  const loadScenario = useCallback(
    async (lockedResults: LeagueScenarioLockedResultInput[] = []): Promise<void> => {
      if (!selectedLeague || !selectedSeason || !selectedMode) {
        return;
      }

      setScenarioLoading(true);
      setScenarioError(null);

      try {
        const payload = await liveFootballApi.runLeagueScenario(
          selectedLeague.id,
          {
            season: selectedSeason,
            mode: selectedMode,
            matchweek: selectedMode === 'as_of_matchweek' ? selectedMatchweek : undefined,
          },
          lockedResults
        );

        setScenario(payload);
      } catch (error) {
        setScenario(null);
        setScenarioError(normalizeError(error));
      } finally {
        setScenarioLoading(false);
      }
    },
    [selectedLeague, selectedSeason, selectedMode, selectedMatchweek]
  );

  const loadSavedScenarios = useCallback(async (): Promise<void> => {
    if (!selectedLeague || !selectedSeason || !selectedMode) {
      setSavedScenarios([]);
      return;
    }

    setSavedScenariosLoading(true);
    setSavedScenariosError(null);

    try {
      const payload = await liveFootballApi.listSavedLeagueScenarios(selectedLeague.id, {
        season: selectedSeason,
        mode: selectedMode,
        matchweek: selectedMode === 'as_of_matchweek' ? selectedMatchweek : undefined,
      });

      setSavedScenarios(payload.items);
    } catch (error) {
      setSavedScenarios([]);
      setSavedScenariosError(normalizeError(error));
    } finally {
      setSavedScenariosLoading(false);
    }
  }, [selectedLeague, selectedSeason, selectedMode, selectedMatchweek]);

  useEffect(() => {
    if (!selectedLeague || !selectedSeason || !selectedMode) {
      setScenario(null);
      setScenarioError(null);
      setScenarioLoading(false);
      return;
    }

    setScoreInputs({});
    setSelectedTeamName(null);
    void loadScenario([]);
    void loadSavedScenarios();
  }, [selectedLeague, selectedSeason, selectedMode, selectedMatchweek, loadScenario]);

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

  const handleLeagueChange = (competitionId: number): void => {
    const nextLeague = leagues.find((league: LeagueMetaItem) => league.id === competitionId);
    const nextSeason = nextLeague?.available_seasons[0] ?? '';
    const nextSeasonAllowsAsOf = Boolean(
      nextLeague &&
      nextSeason &&
      nextSeason !== (nextLeague.current_season_label ?? '')
    );

    const supportedModes = MODE_ORDER.filter((mode) => {
      if (!(nextLeague?.supported_modes ?? []).includes(mode)) {
        return false;
      }

      if (mode === 'as_of_matchweek' && !nextSeasonAllowsAsOf) {
        return false;
      }

      return true;
    });

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

    if (nextMode === 'as_of_matchweek') {
      nextParams.set('matchweek', '1');
    } else {
      nextParams.delete('matchweek');
    }

    setSearchParams(nextParams);
  };

  const handleSeasonChange = (season: string): void => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('season', season);

    const allowsAsOf = selectedLeague && season !== (selectedLeague.current_season_label ?? '');
    const currentMode = nextParams.get('mode') as ProjectionMode | null;

    if (currentMode === 'as_of_matchweek' && !allowsAsOf) {
      nextParams.set('mode', 'current_expected');
      nextParams.delete('matchweek');
    }

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

  const handleScoreInputChange = (
    fixtureKey: string,
    side: 'home_goals' | 'away_goals',
    value: string
  ): void => {
    setScoreInputs((current) => ({
      ...current,
      [fixtureKey]: {
        home_goals: current[fixtureKey]?.home_goals ?? '',
        away_goals: current[fixtureKey]?.away_goals ?? '',
        [side]: value,
      },
    }));
  };

  const handleApplyScenario = async (): Promise<void> => {
    await loadScenario(buildLockedResults());
  };

  const handleResetScenario = async (): Promise<void> => {
    setScoreInputs({});
    setSelectedFixtureKeys(new Set());
    await loadScenario([]);
  };

    const handleSaveScenario = async (): Promise<void> => {
    if (!selectedLeague || !selectedSeason || !selectedMode || !saveTitle.trim()) {
      return;
    }

    const payload: CreateSavedLeagueScenarioPayload = {
      title: saveTitle.trim(),
      description: saveDescription.trim(),
      locked_results: buildLockedResults(),
    };

    setSaveSubmitting(true);
    setSavedScenariosError(null);

    try {
      await liveFootballApi.createSavedLeagueScenario(
        selectedLeague.id,
        payload,
        {
          season: selectedSeason,
          mode: selectedMode,
          matchweek: selectedMode === 'as_of_matchweek' ? selectedMatchweek : undefined,
        }
      );

      setSaveTitle('');
      setSaveDescription('');
      await loadSavedScenarios();
    } catch (error) {
      setSavedScenariosError(normalizeError(error));
    } finally {
      setSaveSubmitting(false);
    }
  };

  const handleLoadSavedScenario = async (scenarioId: number): Promise<void> => {
    setSavedScenarioActionId(scenarioId);
    setSavedScenariosError(null);

    try {
      const detail: SavedLeagueScenarioDetail = await liveFootballApi.getSavedLeagueScenario(scenarioId);

      const nextInputs: ScoreInputState = {};
      const nextSelected = new Set<string>();
      detail.locked_results.forEach((item) => {
        nextInputs[item.fixture_key] = {
          home_goals: String(item.home_goals),
          away_goals: String(item.away_goals),
        };
        nextSelected.add(item.fixture_key);
      });

      setScoreInputs(nextInputs);
      setSelectedFixtureKeys(nextSelected);

      await loadScenario(
        detail.locked_results.map((item) => ({
          fixture_key: item.fixture_key,
          home_goals: item.home_goals,
          away_goals: item.away_goals,
        }))
      );
    } catch (error) {
      setSavedScenariosError(normalizeError(error));
    } finally {
      setSavedScenarioActionId(null);
    }
  };

  const handleDeleteSavedScenario = async (scenarioId: number): Promise<void> => {
    setSavedScenarioActionId(scenarioId);
    setSavedScenariosError(null);

    try {
      await liveFootballApi.deleteSavedLeagueScenario(scenarioId);
      await loadSavedScenarios();
    } catch (error) {
      setSavedScenariosError(normalizeError(error));
    } finally {
      setSavedScenarioActionId(null);
    }
  };

  const unavailableModeReasons = useMemo(() => {
    const baseReasons = new Map(
      (selectedLeague?.unavailable_modes ?? []).map((item: UnavailableMode) => [item.mode, item.reason])
    );

    if (!seasonAllowsAsOfMatchweek) {
      baseReasons.set(
        'as_of_matchweek',
        'As-of-matchweek is only available for completed seasons. Use current expected for the current season.'
      );
    }

    return baseReasons;
  }, [selectedLeague, seasonAllowsAsOfMatchweek]);

  const filtersReady = Boolean(selectedLeague && selectedSeason && selectedMode);
  const totalMatchweeks = scenario?.metadata.total_matchweeks ?? null;
  const expectedRows = useMemo(() => toExpectedLeagueRows(scenario), [scenario]);

  return (
    <main className={pageStyles.page}>
      <header className={pageStyles.header}>
        <div className={pageStyles.titleBlock}>
          <h1 className={pageStyles.title}>Custom league scenario</h1>
          <p className={pageStyles.subtitle}>
            Lock hypothetical scorelines for remaining fixtures and rerun the expected table without saving the scenario yet.
          </p>
        </div>

        <div className={pageStyles.actions}>
          <Link
            to={
              selectedLeague && selectedSeason
                ? `/livefootball/leagues/predict?competition=${selectedLeague.id}&season=${selectedSeason}&mode=${selectedMode ?? 'current_expected'}`
                : '/livefootball/leagues/predict'
            }
            className={pageStyles.secondaryLink}
          >
            Open prediction page
          </Link>
        </div>
      </header>

      <section className={pageStyles.filtersCard}>
        <div className={pageStyles.filtersRow}>
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

        <div className={pageStyles.modeBlock}>
          <span className={pageStyles.modeLabel}>Prediction mode</span>

          <div className={pageStyles.modeButtons}>
            {MODE_ORDER.map((mode) => {
              const isSupported = selectedLeague?.supported_modes.includes(mode) ?? false;
              const reason = unavailableModeReasons.get(mode);
              const disabled = !isSupported || Boolean(reason);

              return (
                <button
                  key={mode}
                  type="button"
                  className={`${pageStyles.modeButton} ${selectedMode === mode ? pageStyles.modeButtonActive : ''}`}
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
        <section className={pageStyles.stateCard}>
          <h2 className={pageStyles.stateTitle}>Loading scenario tools</h2>
          <p className={pageStyles.stateText}>Fetching leagues and available seasons.</p>
        </section>
      ) : null}

      {!metaLoading && metaError ? (
        <section className={pageStyles.stateCard}>
          <h2 className={pageStyles.stateTitle}>Scenario tools unavailable</h2>
          <p className={pageStyles.stateText}>{metaError}</p>
        </section>
      ) : null}

      {!metaLoading && !metaError && !filtersReady ? (
        <section className={pageStyles.stateCard}>
          <h2 className={pageStyles.stateTitle}>No scenario options available</h2>
          <p className={pageStyles.stateText}>
            No supported league, season, and mode combination is currently available.
          </p>
        </section>
      ) : null}

      {!metaLoading && !metaError && filtersReady ? (
        <>
          <section className={styles.builderCard}>
            <div className={styles.builderHeader}>
              <div>
                <h2 className={styles.builderTitle}>Fixture locks</h2>
                <p className={styles.builderText}>
                  Enter scorelines for any remaining fixtures you want to lock into the simulation.
                </p>
              </div>

              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={handleApplyScenario}
                  disabled={scenarioLoading}
                >
                  {scenarioLoading ? 'Running…' : 'Apply scenario'}
                </button>

                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={handleResetScenario}
                  disabled={scenarioLoading}
                >
                  Reset
                </button>
              </div>
            </div>

            <p className={styles.helperText}>
              {selectedFixtureKeys.size} fixture{selectedFixtureKeys.size === 1 ? '' : 's'} locked · {(scenario?.remaining_fixtures.length ?? 0) - selectedFixtureKeys.size} following model. Click a fixture to lock a score.
            </p>

            {scenario && scenario.remaining_fixtures.length === 0 ? (
              <div className={styles.emptyState}>
                No remaining fixtures are available for this league, season, and mode selection.
              </div>
            ) : null}

            {scenario && scenario.remaining_fixtures.length > 0 ? (
              <div className={styles.fixtureList}>
                {scenario.remaining_fixtures.map((fixture) => {
                  const isLocked = selectedFixtureKeys.has(fixture.fixture_key);
                  return (
                    <article
                      key={fixture.fixture_key}
                      className={`${styles.fixtureCard} ${isLocked ? styles.fixtureCardLocked : styles.fixtureCardOpen}`}
                    >
                      <div className={styles.fixtureTeams}>
                        <span className={styles.fixtureName}>
                          {fixture.home_team.short_name || fixture.home_team.name} vs{' '}
                          {fixture.away_team.short_name || fixture.away_team.name}
                        </span>
                        {!isLocked && (
                          <span className={styles.fixturePredicted}>Model predicted</span>
                        )}
                      </div>

                      {isLocked ? (
                        <div className={styles.scoreRow}>
                          <input
                            type="number"
                            min={0}
                            className={styles.scoreInput}
                            value={scoreInputs[fixture.fixture_key]?.home_goals ?? ''}
                            onChange={(event) =>
                              handleScoreInputChange(fixture.fixture_key, 'home_goals', event.target.value)
                            }
                            placeholder="H"
                          />
                          <span className={styles.scoreDivider}>-</span>
                          <input
                            type="number"
                            min={0}
                            className={styles.scoreInput}
                            value={scoreInputs[fixture.fixture_key]?.away_goals ?? ''}
                            onChange={(event) =>
                              handleScoreInputChange(fixture.fixture_key, 'away_goals', event.target.value)
                            }
                            placeholder="A"
                          />
                          <button
                            type="button"
                            className={styles.unlockButton}
                            onClick={() => handleToggleFixture(fixture.fixture_key)}
                            title="Remove lock"
                          >
                            ×
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className={styles.lockButton}
                          onClick={() => handleToggleFixture(fixture.fixture_key)}
                        >
                          Lock score
                        </button>
                      )}
                    </article>
                  );
                })}
              </div>
            ) : null}
          </section>
                    <section className={styles.builderCard}>
            <div className={styles.builderHeader}>
              <div>
                <h2 className={styles.builderTitle}>Save scenario</h2>
                <p className={styles.builderText}>
                  Save the current locked results so you can reload them later for the same league selection.
                </p>
              </div>

              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={handleSaveScenario}
                  disabled={saveSubmitting || !saveTitle.trim()}
                >
                  {saveSubmitting ? 'Saving…' : 'Save scenario'}
                </button>
              </div>
            </div>

            <input
              type="text"
              className={styles.textInput}
              value={saveTitle}
              onChange={(event) => setSaveTitle(event.target.value)}
              placeholder="Scenario title"
            />

            <textarea
              className={styles.textArea}
              value={saveDescription}
              onChange={(event) => setSaveDescription(event.target.value)}
              placeholder="Optional description"
            />
          </section>

          <section className={styles.builderCard}>
            <div className={styles.builderHeader}>
              <div>
                <h2 className={styles.builderTitle}>Saved scenarios</h2>
                <p className={styles.builderText}>
                  Reload or delete previously saved scenarios for this league, season, and mode.
                </p>
              </div>
            </div>

            {savedScenariosLoading ? (
              <div className={styles.emptyState}>Loading saved scenarios…</div>
            ) : null}

            {!savedScenariosLoading && savedScenariosError ? (
              <div className={styles.emptyState}>{savedScenariosError}</div>
            ) : null}

            {!savedScenariosLoading && !savedScenariosError && savedScenarios.length === 0 ? (
              <div className={styles.emptyState}>No saved scenarios yet for this selection.</div>
            ) : null}

            {!savedScenariosLoading && !savedScenariosError && savedScenarios.length > 0 ? (
              <div className={styles.savedList}>
                {savedScenarios.map((item) => (
                  <article key={item.id} className={styles.savedCard}>
                    <div className={styles.savedMeta}>
                      <span className={styles.savedTitle}>{item.title}</span>
                      <span className={styles.savedSubtitle}>
                        {item.locked_result_count} locked result{item.locked_result_count === 1 ? '' : 's'} · updated{' '}
                        {new Date(item.updated_at).toLocaleString()}
                      </span>
                      {item.description ? (
                        <span className={styles.savedSubtitle}>{item.description}</span>
                      ) : null}
                    </div>

                    <div className={styles.savedActions}>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => handleLoadSavedScenario(item.id)}
                        disabled={savedScenarioActionId === item.id}
                      >
                        Load
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => handleDeleteSavedScenario(item.id)}
                        disabled={savedScenarioActionId === item.id}
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : null}
          </section>

          {scenarioLoading ? (
            <section className={pageStyles.stateCard}>
              <h2 className={pageStyles.stateTitle}>Running scenario</h2>
              <p className={pageStyles.stateText}>Recomputing the expected table.</p>
            </section>
          ) : null}

          {!scenarioLoading && scenarioError ? (
            <section className={pageStyles.stateCard}>
              <h2 className={pageStyles.stateTitle}>Could not run scenario</h2>
              <p className={pageStyles.stateText}>{scenarioError}</p>
            </section>
          ) : null}

          {!scenarioLoading && !scenarioError && scenario ? (
            <>
              <PredictionSummary payload={scenario} />

              <section className={styles.section}>
                <LeagueTable
                  rows={expectedRows}
                  title="Scenario expected table"
                  emptyMessage="No expected table is available for this scenario."
                />
              </section>

              <CommentaryPanel commentary={scenario.commentary} />
            </>
          ) : null}
        </>
      ) : null}
    </main>
  );
};

export default LeagueCustomPage;