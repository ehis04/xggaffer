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
  LeagueScenarioFixture,
  LeagueScenarioLockedResultInput,
  LeagueScenarioResponse,
  LeagueMetaItem,
  LeaguesMetaResponse,
  LeagueTableRow,
  SavedLeagueScenarioDetail,
  SavedLeagueScenarioListItem,
  TeamReference,
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

interface MatchupGroup {
  opponent: TeamReference;
  homeFixture: LeagueScenarioFixture | null;
  awayFixture: LeagueScenarioFixture | null;
}

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
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);

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

    // For past/completed seasons prefer pre_season — current_expected returns 0 remaining fixtures
    if (seasonAllowsAsOfMatchweek && supported.includes('pre_season')) {
      return 'pre_season';
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

  // All teams in the league, sorted alphabetically, from the expected table (always complete)
  const allTeams = useMemo<TeamReference[]>(() => {
    if (!scenario) return [];
    return [...scenario.expected_table.map((row) => row.team)].sort((a, b) =>
      a.name.localeCompare(b.name)
    );
  }, [scenario]);

  // For the selected team: group opponents with their home and away fixtures
  const matchupGroups = useMemo<MatchupGroup[]>(() => {
    if (!selectedTeam || !scenario) return [];

    const groups = new Map<string, MatchupGroup>();

    // Pre-populate all other teams so we show cards even without remaining fixtures
    for (const row of scenario.expected_table) {
      if (row.team.name !== selectedTeam) {
        groups.set(row.team.name, { opponent: row.team, homeFixture: null, awayFixture: null });
      }
    }

    // Map remaining fixtures onto the groups
    for (const fixture of scenario.remaining_fixtures) {
      if (fixture.home_team.name === selectedTeam) {
        const g = groups.get(fixture.away_team.name);
        if (g) g.homeFixture = fixture;
      } else if (fixture.away_team.name === selectedTeam) {
        const g = groups.get(fixture.home_team.name);
        if (g) g.awayFixture = fixture;
      }
    }

    return [...groups.values()].sort((a, b) => a.opponent.name.localeCompare(b.opponent.name));
  }, [selectedTeam, scenario]);

  // Number of fixtures that have valid custom scores (both goals set)
  // Number of fixtures that have valid custom scores (both goals set)
  const lockedCount = useMemo<number>(() => {
    return Object.values(scoreInputs).filter((v) => {
      const h = Number(v.home_goals);
      const a = Number(v.away_goals);
      return (
        v.home_goals !== '' &&
        v.away_goals !== '' &&
        Number.isInteger(h) &&
        Number.isInteger(a) &&
        h >= 0 &&
        a >= 0
      );
    }).length;
  }, [scoreInputs]);

  // Auto-lock all fixtures when a team is selected
  useEffect(() => {
    if (!selectedTeam || matchupGroups.length === 0) return;

    const nextInputs: ScoreInputState = { ...scoreInputs };
    let hasChanges = false;

    for (const { homeFixture, awayFixture } of matchupGroups) {
      if (homeFixture && !scoreInputs[homeFixture.fixture_key]) {
        nextInputs[homeFixture.fixture_key] = { home_goals: '', away_goals: '' };
        hasChanges = true;
      }
      if (awayFixture && !scoreInputs[awayFixture.fixture_key]) {
        nextInputs[awayFixture.fixture_key] = { home_goals: '', away_goals: '' };
        hasChanges = true;
      }
    }

    if (hasChanges) {
      setScoreInputs(nextInputs);
    }
  }, [selectedTeam, matchupGroups, scoreInputs]);

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
    setSelectedTeam(null);
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
    const isPast = Boolean(
      nextLeague && nextSeason && nextSeason !== (nextLeague.current_season_label ?? '')
    );

    const supportedModes = MODE_ORDER.filter((mode) => {
      if (!(nextLeague?.supported_modes ?? []).includes(mode)) return false;
      if (mode === 'as_of_matchweek' && !isPast) return false;
      return true;
    });

    // For past seasons prefer pre_season to avoid 0 remaining fixtures
    const nextMode = (isPast && supportedModes.includes('pre_season'))
      ? 'pre_season'
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
      nextParams.set('matchweek', '1');
    } else {
      nextParams.delete('matchweek');
    }

    setSelectedTeam(null);
    setScoreInputs({});
    setSearchParams(nextParams);
  };

  const handleSeasonChange = (season: string): void => {
    setSelectedTeam(null);
    setScoreInputs({});

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('season', season);

    const isPast = selectedLeague ? season !== (selectedLeague.current_season_label ?? '') : false;
    const currentMode = nextParams.get('mode') as ProjectionMode | null;

    if (currentMode === 'as_of_matchweek' && !isPast) {
      // as_of_matchweek requires a completed season
      nextParams.set('mode', 'current_expected');
      nextParams.delete('matchweek');
    } else if (currentMode === 'current_expected' && isPast) {
      // Switching to a past season — prefer pre_season to avoid 0 remaining fixtures
      nextParams.set('mode', 'pre_season');
    }

    setSearchParams(nextParams);
  };

  const handleModeChange = (mode: ProjectionMode): void => {
    setSelectedTeam(null);
    setScoreInputs({});

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

  const handleTeamSelect = (teamName: string): void => {
    setSelectedTeam((prev) => (prev === teamName ? null : teamName));
  };

  const handleAutoScoreChange = (
    fixtureKey: string,
    side: 'home_goals' | 'away_goals',
    value: string
  ): void => {
    setScoreInputs((prev) => {
      const current = prev[fixtureKey] ?? { home_goals: '', away_goals: '' };
      const updated = { ...current, [side]: value };
      if (updated.home_goals === '' && updated.away_goals === '') {
        const { [fixtureKey]: _removed, ...rest } = prev;
        return rest;
      }
      return { ...prev, [fixtureKey]: updated };
    });
  };

  const handleClearFixture = (fixtureKey: string): void => {
    setScoreInputs((prev) => {
      const { [fixtureKey]: _removed, ...rest } = prev;
      return rest;
    });
  };

  const handleApplyScenario = async (): Promise<void> => {
    await loadScenario(buildLockedResults());
  };

  const handleResetScenario = async (): Promise<void> => {
    setScoreInputs({});
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
      detail.locked_results.forEach((item) => {
        nextInputs[item.fixture_key] = {
          home_goals: String(item.home_goals),
          away_goals: String(item.away_goals),
        };
      });

      setScoreInputs(nextInputs);
      setSelectedTeam(null);

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
  const remainingCount = (scenario?.remaining_fixtures.length ?? 0) - lockedCount;

  return (
    <main className={pageStyles.page}>
      <header className={pageStyles.header}>
        <div className={pageStyles.titleBlock}>
          <h1 className={pageStyles.title}>Custom league scenario</h1>
          <p className={pageStyles.subtitle}>
            Pick a team, override any fixture scoreline, and rerun the expected table to explore what-if scenarios.
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
          <h2 className={pageStyles.stateTitle}>Loading</h2>
          <p className={pageStyles.stateText}>Fetching leagues and available seasons.</p>
        </section>
      ) : null}

      {!metaLoading && metaError ? (
        <section className={pageStyles.stateCard}>
          <h2 className={pageStyles.stateTitle}>Unavailable</h2>
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
          {/* ── Fixture builder ── */}
          <section className={styles.builderCard}>
            <div className={styles.builderHeader}>
              <div>
                <h2 className={styles.builderTitle}>Fixture builder</h2>
                <p className={styles.builderText}>
                  {lockedCount > 0
                    ? `${lockedCount} fixture${lockedCount === 1 ? '' : 's'} with custom scores · ${remainingCount} following model`
                    : 'Select a team to view their fixtures and override any scoreline.'}
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
                  disabled={scenarioLoading || lockedCount === 0}
                >
                  Reset all
                </button>
              </div>
            </div>

            {scenarioLoading && !scenario ? (
              <div className={styles.emptyState}>Loading fixtures…</div>
            ) : null}

            {!scenarioLoading && scenario && scenario.remaining_fixtures.length === 0 ? (
              <div className={styles.emptyState}>
                No fixtures are available for this league, season, and mode.
                {seasonAllowsAsOfMatchweek ? ' Try switching to Pre-season mode to see all season fixtures.' : ''}
              </div>
            ) : null}

            {scenario && allTeams.length > 0 ? (
              <>
                {/* Step 1 or step 2 header */}
                {selectedTeam ? (
                  <div className={styles.teamHeader}>
                    <span className={styles.teamHeaderLabel}>
                      Fixtures for <strong>{selectedTeam}</strong> — type a score to override the model prediction
                    </span>
                    <button
                      type="button"
                      className={styles.changeTeamButton}
                      onClick={() => setSelectedTeam(null)}
                    >
                      ← Change team
                    </button>
                  </div>
                ) : (
                  <p className={styles.teamPickerPrompt}>
                    Select a team to view and override their fixture scorelines:
                  </p>
                )}

                {/* Step 1: 4-column team grid */}
                {!selectedTeam ? (
                  <div className={styles.teamGrid}>
                    {allTeams.map((team) => (
                      <button
                        key={team.name}
                        type="button"
                        className={styles.teamCard}
                        onClick={() => handleTeamSelect(team.name)}
                      >
                        {team.emblem_url ? (
                          <img
                            src={team.emblem_url}
                            alt=""
                            className={styles.teamBadge}
                          />
                        ) : null}
                        <span className={styles.teamCardName}>
                          {team.short_name || team.tla || team.name}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  /* Step 2: opponent cards with inline score inputs */
                  <div className={styles.opponentGrid}>
                    {matchupGroups.map(({ opponent, homeFixture, awayFixture }) => {
                      const homeScored = homeFixture ? Boolean(scoreInputs[homeFixture.fixture_key]) : false;
                      const awayScored = awayFixture ? Boolean(scoreInputs[awayFixture.fixture_key]) : false;
                      const isOverridden = homeScored || awayScored;

                      return (
                        <div
                          key={opponent.name}
                          className={`${styles.opponentCard} ${isOverridden ? styles.opponentCardActive : ''}`}
                        >
                          <div className={styles.opponentHeader}>
                            {opponent.emblem_url ? (
                              <img
                                src={opponent.emblem_url}
                                alt=""
                                className={styles.opponentBadge}
                              />
                            ) : null}
                            <span className={styles.opponentName}>
                              {opponent.short_name || opponent.tla || opponent.name}
                            </span>
                          </div>

                          {homeFixture ? (
                            <div className={styles.fixtureRow}>
                              <span className={styles.fixtureLabel} title="Home fixture">H</span>
                              <input
                                type="number"
                                min={0}
                                step={1}
                                className={styles.scoreInput}
                                value={scoreInputs[homeFixture.fixture_key]?.home_goals ?? ''}
                                onChange={(e) =>
                                  handleAutoScoreChange(homeFixture.fixture_key, 'home_goals', e.target.value)
                                }
                                placeholder="—"
                              />
                              <span className={styles.scoreDivider}>–</span>
                              <input
                                type="number"
                                min={0}
                                step={1}
                                className={styles.scoreInput}
                                value={scoreInputs[homeFixture.fixture_key]?.away_goals ?? ''}
                                onChange={(e) =>
                                  handleAutoScoreChange(homeFixture.fixture_key, 'away_goals', e.target.value)
                                }
                                placeholder="—"
                              />
                              {scoreInputs[homeFixture.fixture_key] ? (
                                <button
                                  type="button"
                                  className={styles.clearButton}
                                  onClick={() => handleClearFixture(homeFixture.fixture_key)}
                                  title="Clear score"
                                >
                                  ×
                                </button>
                              ) : null}
                            </div>
                          ) : null}

                          {awayFixture ? (
                            <div className={styles.fixtureRow}>
                              <span className={`${styles.fixtureLabel} ${styles.fixtureLabelAway}`} title="Away fixture">A</span>
                              <input
                                type="number"
                                min={0}
                                step={1}
                                className={styles.scoreInput}
                                value={scoreInputs[awayFixture.fixture_key]?.home_goals ?? ''}
                                onChange={(e) =>
                                  handleAutoScoreChange(awayFixture.fixture_key, 'home_goals', e.target.value)
                                }
                                placeholder="—"
                              />
                              <span className={styles.scoreDivider}>–</span>
                              <input
                                type="number"
                                min={0}
                                step={1}
                                className={styles.scoreInput}
                                value={scoreInputs[awayFixture.fixture_key]?.away_goals ?? ''}
                                onChange={(e) =>
                                  handleAutoScoreChange(awayFixture.fixture_key, 'away_goals', e.target.value)
                                }
                                placeholder="—"
                              />
                              {scoreInputs[awayFixture.fixture_key] ? (
                                <button
                                  type="button"
                                  className={styles.clearButton}
                                  onClick={() => handleClearFixture(awayFixture.fixture_key)}
                                  title="Clear score"
                                >
                                  ×
                                </button>
                              ) : null}
                            </div>
                          ) : null}

                          {!homeFixture && !awayFixture ? (
                            <span className={styles.noFixtures}>All played</span>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            ) : null}
          </section>

          {/* ── Save scenario ── */}
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

          {/* ── Saved scenarios ── */}
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