import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import LeagueSelector from '../../../components/playerdiscovery/LeagueSelector';
import ClubSelector from '../../../components/playerdiscovery/ClubSelector';
import PlayerSelector from '../../../components/playerdiscovery/PlayerSelector';
import PlayerSearchInput from '../../../components/playerdiscovery/PlayerSearchInput';
import { playerdataApi } from '../../../services/api/playerdataApi';
import type {
  MergedProviderCoverage,
  PlayerComparisonParams,
  PlayerDataFilters,
  PlayerOverviewComparison,
  PlayerOverviewComparisonMetric,
  PlayerOverviewComparisonMetricGroup,
} from '../../../types/playerdata';
import type {
  CompetitionListItem,
  PlayerLookupItem,
  TeamLookupItem,
} from '../../../types/livefootball';
import styles from './css/InternalPlayerComparisonPage.module.css';

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

      return [String(value)];
    });

    if (values.length > 0) {
      return values.join(' ');
    }
  }

  return 'Something went wrong.';
};

const parsePositiveInt = (value: string | null): number | null => {
  if (!value) {
    return null;
  }

  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }

  return parsed;
};

const cleanFilterValue = (value: string | null): string => {
  return value?.trim() ?? '';
};

const formatTimestamp = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString('en-IE', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

const buildPlayerProfileUrl = (
  playerId: number,
  options?: {
    filters?: PlayerDataFilters;
    fromClubId?: number | null;
    clubPlayerId?: number | null;
  }
): string => {
  const params = new URLSearchParams({
    playerId: String(playerId),
  });

  if (options?.filters?.season) {
    params.set('season', options.filters.season);
  }

  if (options?.filters?.provider) {
    params.set('provider', options.filters.provider);
  }

  if (options?.filters?.competition_code) {
    params.set('competition_code', options.filters.competition_code);
  }

  if (options?.filters?.competition_name) {
    params.set('competition_name', options.filters.competition_name);
  }

  if (options?.fromClubId && Number.isInteger(options.fromClubId) && options.fromClubId > 0) {
    params.set('fromClubId', String(options.fromClubId));
  }

  if (
    options?.clubPlayerId &&
    Number.isInteger(options.clubPlayerId) &&
    options.clubPlayerId > 0
  ) {
    params.set('clubPlayerId', String(options.clubPlayerId));
  }

  return `/coaching/playerdata/player?${params.toString()}`;
};

const buildBackNavigation = (options: {
  fromClubId?: number | null;
  returnToPlayerId?: number | null;
  clubPlayerId?: number | null;
  filters?: PlayerDataFilters;
}): { to: string; label: string } => {
  const { fromClubId, returnToPlayerId, clubPlayerId, filters } = options;

  if (returnToPlayerId && Number.isInteger(returnToPlayerId) && returnToPlayerId > 0) {
    return {
      to: buildPlayerProfileUrl(returnToPlayerId, {
        filters,
        fromClubId,
        clubPlayerId,
      }),
      label: 'Back to Player Read',
    };
  }

  if (fromClubId && Number.isInteger(fromClubId) && fromClubId > 0) {
    return {
      to: `/clubs/${fromClubId}/players`,
      label: 'Back to Club Players',
    };
  }

  return {
    to: '/clubs',
    label: 'Back to Clubs',
  };
};

const getPlayerName = (
  comparison: PlayerOverviewComparison | null,
  side: 'player_a' | 'player_b'
): string | null => {
  const player = comparison?.[side]?.player;

  return (
    player?.display_name ||
    player?.full_name ||
    player?.short_name ||
    null
  );
};

const getMetricValue = (
  metric: PlayerOverviewComparisonMetric,
  side: 'player_a' | 'player_b'
): string => {
  if (side === 'player_a') {
    return metric.player_a_formatted || (metric.player_a_value != null ? String(metric.player_a_value) : '—');
  }

  return metric.player_b_formatted || (metric.player_b_value != null ? String(metric.player_b_value) : '—');
};

const getCanonicalPlayerId = (player?: PlayerLookupItem | null): number | null => {
  const id = player?.canonical_player?.id;
  return typeof id === 'number' && Number.isInteger(id) && id > 0 ? id : null;
};

const buildLookupPlayerSummary = (player?: PlayerLookupItem | null): string => {
  if (!player) {
    return '';
  }

  return [
    player.player_name,
    player.team?.name || null,
    player.primary_position || player.raw_position || null,
    player.nationality || null,
    player.squad_number ? `#${player.squad_number}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
};

const buildCoverageSummaryLine = (coverage?: MergedProviderCoverage | null): string => {
  if (!coverage) {
    return '';
  }

  return [
    coverage.coverage_status,
    coverage.matches_sampled != null ? `${coverage.matches_sampled} matches sampled` : null,
    coverage.minutes_sampled != null ? `${coverage.minutes_sampled} minutes sampled` : null,
  ]
    .filter(Boolean)
    .join(' · ');
};

const buildFreshnessLine = (coverage?: MergedProviderCoverage | null): string => {
  if (!coverage) {
    return '';
  }

  return [
    coverage.freshness_label,
    coverage.last_synced_at ? `Last synced ${formatTimestamp(coverage.last_synced_at)}` : null,
    coverage.source_updated_at ? `Updated ${formatTimestamp(coverage.source_updated_at)}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
};

const renderMetricGroup = (group: PlayerOverviewComparisonMetricGroup, index: number) => (
  <section key={`${group.key}-${index}`} className={styles.panel}>
    <div className={styles.panelHeader}>
      <h2 className={styles.panelTitle}>{group.label}</h2>
      <span className={styles.badge}>{group.metrics?.length ?? 0} metrics</span>
    </div>

    {group.metrics && group.metrics.length > 0 ? (
      <div className={styles.grid}>
        {group.metrics.map((metric) => (
          <div key={metric.key} className={styles.emptyState}>
            <strong>{metric.label}</strong>
            <div>A: {getMetricValue(metric, 'player_a')}</div>
            <div>B: {getMetricValue(metric, 'player_b')}</div>
            <div>
              {metric.winner
                ? `Winner: ${
                    metric.winner === 'player_a'
                      ? 'Player A'
                      : metric.winner === 'player_b'
                        ? 'Player B'
                        : metric.winner
                  }`
                : metric.is_tie
                  ? 'Result: Tie'
                  : 'No winner'}
            </div>
            {metric.sentence && <div>{metric.sentence}</div>}
            <div>
              {[metric.source, metric.preferred_provider].filter(Boolean).join(' · ') || 'Merged metric'}
            </div>
          </div>
        ))}
      </div>
    ) : (
      <div className={styles.emptyState}>No comparable metrics are available in this group.</div>
    )}
  </section>
);

const InternalPlayerComparisonPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const playerAId = useMemo(
    () => parsePositiveInt(searchParams.get('player_a_id')),
    [searchParams]
  );

  const playerBId = useMemo(
    () => parsePositiveInt(searchParams.get('player_b_id')),
    [searchParams]
  );

  const fromClubId = useMemo(
    () => parsePositiveInt(searchParams.get('fromClubId')),
    [searchParams]
  );

  const clubPlayerId = useMemo(
    () => parsePositiveInt(searchParams.get('clubPlayerId')),
    [searchParams]
  );

  const returnToPlayerId = useMemo(
    () => parsePositiveInt(searchParams.get('returnToPlayerId')),
    [searchParams]
  );

  const initialSeason = cleanFilterValue(searchParams.get('season'));
  const initialProvider = cleanFilterValue(searchParams.get('provider'));
  const initialCompetitionCode = cleanFilterValue(searchParams.get('competition_code'));
  const initialCompetitionName = cleanFilterValue(searchParams.get('competition_name'));

  const [season, setSeason] = useState(initialSeason);
  const [provider, setProvider] = useState(initialProvider);
  const [competitionCode, setCompetitionCode] = useState(initialCompetitionCode);
  const [competitionName, setCompetitionName] = useState(initialCompetitionName);

  const [selectedCompetition, setSelectedCompetition] = useState<CompetitionListItem | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<TeamLookupItem | null>(null);
  const [selectedPlayerA, setSelectedPlayerA] = useState<PlayerLookupItem | null>(null);
  const [selectedPlayerB, setSelectedPlayerB] = useState<PlayerLookupItem | null>(null);
  const [searchQueryA, setSearchQueryA] = useState('');
  const [searchQueryB, setSearchQueryB] = useState('');

  const [comparison, setComparison] = useState<PlayerOverviewComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSeason(initialSeason);
    setProvider(initialProvider);
    setCompetitionCode(initialCompetitionCode);
    setCompetitionName(initialCompetitionName);
  }, [initialSeason, initialProvider, initialCompetitionCode, initialCompetitionName]);

  const filters: PlayerDataFilters = useMemo(
    () => ({
      season: season.trim() || undefined,
      provider: provider.trim() || undefined,
      competition_code: competitionCode.trim() || undefined,
      competition_name: competitionName.trim() || undefined,
    }),
    [season, provider, competitionCode, competitionName]
  );

  const comparisonParams: PlayerComparisonParams | null = useMemo(() => {
    if (!playerAId || !playerBId || playerAId === playerBId) {
      return null;
    }

    return {
      player_a_id: playerAId,
      player_b_id: playerBId,
      season: filters.season,
      provider: filters.provider,
      competition_code: filters.competition_code,
      competition_name: filters.competition_name,
    };
  }, [playerAId, playerBId, filters]);

  const pageValidationMessage = useMemo(() => {
    if (!playerAId || !playerBId) {
      return 'Select two players to compare.';
    }

    if (playerAId === playerBId) {
      return 'Comparison requires two different players.';
    }

    return null;
  }, [playerAId, playerBId]);

  useEffect(() => {
    if (!comparisonParams) {
      setComparison(null);
      setError(pageValidationMessage);
      setLoading(false);
      return;
    }

    let isActive = true;

    const loadComparison = async () => {
      try {
        setLoading(true);
        setError(null);

        const result = await playerdataApi.getPlayerOverviewComparison(comparisonParams);

        if (!isActive) {
          return;
        }

        setComparison(result);
      } catch (err) {
        if (!isActive) {
          return;
        }

        setComparison(null);
        setError(normalizeError(err));
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void loadComparison();

    return () => {
      isActive = false;
    };
  }, [comparisonParams, pageValidationMessage]);

  const selectedPlayerACanonicalId = useMemo(
    () => getCanonicalPlayerId(selectedPlayerA),
    [selectedPlayerA]
  );

  const selectedPlayerBCanonicalId = useMemo(
    () => getCanonicalPlayerId(selectedPlayerB),
    [selectedPlayerB]
  );

  const resolvedPlayerAIdForApply = selectedPlayerACanonicalId ?? playerAId;
  const resolvedPlayerBIdForApply = selectedPlayerBCanonicalId ?? playerBId;

  const selectionValidationMessage = useMemo(() => {
    if (selectedPlayerA && !selectedPlayerACanonicalId) {
      return 'Player A does not have a canonical player link yet.';
    }

    if (selectedPlayerB && !selectedPlayerBCanonicalId) {
      return 'Player B does not have a canonical player link yet.';
    }

    if (resolvedPlayerAIdForApply && resolvedPlayerBIdForApply) {
      if (resolvedPlayerAIdForApply === resolvedPlayerBIdForApply) {
        return 'Choose two different players for comparison.';
      }

      return null;
    }

    if (selectedPlayerA || selectedPlayerB) {
      return 'Select both Player A and Player B before applying comparison.';
    }

    return null;
  }, [
    selectedPlayerA,
    selectedPlayerB,
    selectedPlayerACanonicalId,
    selectedPlayerBCanonicalId,
    resolvedPlayerAIdForApply,
    resolvedPlayerBIdForApply,
  ]);

  const canApplySelection = useMemo(() => {
    return Boolean(
      resolvedPlayerAIdForApply &&
      resolvedPlayerBIdForApply &&
      resolvedPlayerAIdForApply !== resolvedPlayerBIdForApply &&
      !selectionValidationMessage
    );
  }, [
    resolvedPlayerAIdForApply,
    resolvedPlayerBIdForApply,
    selectionValidationMessage,
  ]);

  const handleCompetitionChange = (competition: CompetitionListItem | null) => {
    setSelectedCompetition(competition);
    setSelectedTeam(null);
    setSelectedPlayerA(null);
    setSelectedPlayerB(null);
    setSearchQueryA('');
    setSearchQueryB('');
  };

  const handleTeamChange = (team: TeamLookupItem | null) => {
    setSelectedTeam(team);
    setSelectedPlayerA(null);
    setSelectedPlayerB(null);
    setSearchQueryA('');
    setSearchQueryB('');
  };

  const handleApplyComparison = () => {
    const nextPlayerAId = selectedPlayerACanonicalId ?? playerAId;
    const nextPlayerBId = selectedPlayerBCanonicalId ?? playerBId;

    const nextParams = new URLSearchParams(searchParams);

    if (nextPlayerAId) {
      nextParams.set('player_a_id', String(nextPlayerAId));
    } else {
      nextParams.delete('player_a_id');
    }

    if (nextPlayerBId) {
      nextParams.set('player_b_id', String(nextPlayerBId));
    } else {
      nextParams.delete('player_b_id');
    }

    if (season.trim()) {
      nextParams.set('season', season.trim());
    } else {
      nextParams.delete('season');
    }

    if (provider.trim()) {
      nextParams.set('provider', provider.trim());
    } else {
      nextParams.delete('provider');
    }

    if (competitionCode.trim()) {
      nextParams.set('competition_code', competitionCode.trim());
    } else {
      nextParams.delete('competition_code');
    }

    if (competitionName.trim()) {
      nextParams.set('competition_name', competitionName.trim());
    } else {
      nextParams.delete('competition_name');
    }

    setSearchParams(nextParams);
  };

  const handleSwapPlayers = () => {
    setSelectedPlayerA(selectedPlayerB);
    setSelectedPlayerB(selectedPlayerA);

    const nextParams = new URLSearchParams(searchParams);
    const currentA = nextParams.get('player_a_id');
    const currentB = nextParams.get('player_b_id');

    if (currentB) {
      nextParams.set('player_a_id', currentB);
    } else {
      nextParams.delete('player_a_id');
    }

    if (currentA) {
      nextParams.set('player_b_id', currentA);
    } else {
      nextParams.delete('player_b_id');
    }

    setSearchParams(nextParams);
  };

  const handleClearSelection = () => {
    setSelectedCompetition(null);
    setSelectedTeam(null);
    setSelectedPlayerA(null);
    setSelectedPlayerB(null);
  };

  const handleClearFilters = () => {
    setSeason('');
    setProvider('');
    setCompetitionCode('');
    setCompetitionName('');

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('season');
    nextParams.delete('provider');
    nextParams.delete('competition_code');
    nextParams.delete('competition_name');
    setSearchParams(nextParams);
  };

  const playerAName = getPlayerName(comparison, 'player_a');
  const playerBName = getPlayerName(comparison, 'player_b');

  const playerAProfileUrl = playerAId
    ? buildPlayerProfileUrl(playerAId, {
        filters,
        fromClubId,
        clubPlayerId: returnToPlayerId === playerAId ? clubPlayerId : null,
      })
    : null;

  const playerBProfileUrl = playerBId
    ? buildPlayerProfileUrl(playerBId, {
        filters,
        fromClubId,
        clubPlayerId: returnToPlayerId === playerBId ? clubPlayerId : null,
      })
    : null;

  const contextLine = [
    comparison?.context?.competition_name,
    comparison?.context?.season,
    comparison?.context?.provider,
  ]
    .filter(Boolean)
    .join(' · ');

  const originLine = [
    fromClubId ? `Club ${fromClubId}` : null,
    clubPlayerId ? `Club player row ${clubPlayerId}` : null,
    returnToPlayerId ? `Origin player ${returnToPlayerId}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  const backNavigation = buildBackNavigation({
    fromClubId,
    returnToPlayerId,
    clubPlayerId,
    filters,
  });

  const comparisonCoverageLine = buildCoverageSummaryLine(comparison?.provider_coverage);
  const comparisonFreshnessLine = buildFreshnessLine(comparison?.provider_coverage);

  const availableSourcesLine = comparison?.provider_coverage?.available_sources?.length
    ? comparison.provider_coverage.available_sources.join(' · ')
    : '';

  const missingSourcesLine = comparison?.provider_coverage?.missing_sources?.length
    ? comparison.provider_coverage.missing_sources.join(' · ')
    : '';

  const playerASelectionSummary = buildLookupPlayerSummary(selectedPlayerA);
  const playerBSelectionSummary = buildLookupPlayerSummary(selectedPlayerB);

  const activeCompetitionId =
    selectedCompetition?.id ?? comparison?.player_a?.context?.competition_id ?? null;

  const activeTeamId = selectedTeam?.id ?? null;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Internal comparison surface</p>
          <h1 className={styles.title}>Merged Deterministic Player Comparison</h1>
          <p className={styles.subtitle}>
            Controlled internal comparison built on the merged overview comparison API.
          </p>
          {contextLine && <p className={styles.subtitle}>{contextLine}</p>}
          {originLine && <p className={styles.subtitle}>{originLine}</p>}
          {comparisonFreshnessLine && <p className={styles.subtitle}>{comparisonFreshnessLine}</p>}
          {comparisonCoverageLine && <p className={styles.subtitle}>{comparisonCoverageLine}</p>}
        </div>

        <div className={styles.headerActions}>
          <Link to={backNavigation.to} className={styles.secondaryButton}>
            {backNavigation.label}
          </Link>
        </div>
      </div>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Comparison Selection</h2>
          <span className={styles.badge}>Internal only</span>
        </div>

        <div className={styles.grid}>
          <div className={styles.formGroup}>
            <LeagueSelector
              value={selectedCompetition?.id ?? null}
              onChange={handleCompetitionChange}
              label="League"
              placeholder="Optional league narrowing"
            />
          </div>

          <div className={styles.formGroup}>
            <ClubSelector
              competitionId={selectedCompetition?.id ?? null}
              value={selectedTeam?.id ?? null}
              onChange={handleTeamChange}
              label="Club"
              placeholder="Optional club narrowing"
              emptyStateText="Select a league first"
            />
          </div>
        </div>

        <div className={styles.grid}>
          <div className={styles.emptyState}>
            <strong>Player A</strong>

            <div className={styles.formGroup}>
              <PlayerSelector
                competitionId={activeCompetitionId}
                teamId={activeTeamId}
                value={selectedPlayerA?.id ?? null}
                onChange={setSelectedPlayerA}
                season={filters.season}
                label="Player A"
                placeholder="Select Player A"
                emptyStateText="Select a league above, or search by name below"
              />
            </div>

            <div className={styles.formGroup}>
              <PlayerSearchInput
                query={searchQueryA}
                onQueryChange={setSearchQueryA}
                onSelectResult={setSelectedPlayerA}
                competitionId={activeCompetitionId}
                teamId={activeTeamId}
                season={filters.season}
                helperText="Search by name to find players without selecting a league"
              />
            </div>

            {playerASelectionSummary ? (
              <>
                <div>{playerASelectionSummary}</div>
                <div>
                  {selectedPlayerACanonicalId
                    ? `Canonical profile available (${selectedPlayerACanonicalId})`
                    : 'No canonical player link available yet'}
                </div>
              </>
            ) : playerAName ? (
              <>
                <div>{playerAName}</div>
                <div>Current comparison Player A</div>
              </>
            ) : (
              <div>No player selected for side A yet.</div>
            )}
          </div>

          <div className={styles.emptyState}>
            <strong>Player B</strong>

            <div className={styles.formGroup}>
              <PlayerSelector
                competitionId={activeCompetitionId}
                teamId={activeTeamId}
                value={selectedPlayerB?.id ?? null}
                onChange={setSelectedPlayerB}
                season={filters.season}
                label="Player B"
                placeholder="Select Player B"
                emptyStateText="Select a league above, or search by name below"
              />
            </div>

            <div className={styles.formGroup}>
              <PlayerSearchInput
                query={searchQueryB}
                onQueryChange={setSearchQueryB}
                onSelectResult={setSelectedPlayerB}
                competitionId={activeCompetitionId}
                teamId={activeTeamId}
                season={filters.season}
                helperText="Search by name to find players without selecting a league"
              />
            </div>

            {playerBSelectionSummary ? (
              <>
                <div>{playerBSelectionSummary}</div>
                <div>
                  {selectedPlayerBCanonicalId
                    ? `Canonical profile available (${selectedPlayerBCanonicalId})`
                    : 'No canonical player link available yet'}
                </div>
              </>
            ) : playerBName ? (
              <>
                <div>{playerBName}</div>
                <div>Current comparison Player B</div>
              </>
            ) : (
              <div>No player selected for side B yet.</div>
            )}
          </div>
        </div>

        {selectionValidationMessage ? (
          <div className={styles.emptyState}>{selectionValidationMessage}</div>
        ) : null}

        <div className={styles.formActions}>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={handleApplyComparison}
            disabled={!canApplySelection}
          >
            Compare Selected Players
          </button>

          <button
            type="button"
            className={styles.secondaryButton}
            onClick={handleSwapPlayers}
          >
            Swap Players
          </button>

          <button
            type="button"
            className={styles.secondaryButton}
            onClick={handleClearSelection}
          >
            Clear Selection
          </button>
        </div>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Comparison Filters</h2>
          <span className={styles.badge}>Read only</span>
        </div>

        <form
          className={styles.form}
          onSubmit={(event) => {
            event.preventDefault();
            handleApplyComparison();
          }}
        >
          <div className={styles.grid}>
            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor="season">
                Season
              </label>
              <input
                id="season"
                className={styles.input}
                value={season}
                onChange={(event) => setSeason(event.target.value)}
                placeholder="e.g. 2024/2025"
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor="provider">
                Provider
              </label>
              <input
                id="provider"
                className={styles.input}
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
                placeholder="e.g. understat"
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor="competition_code">
                Competition Code
              </label>
              <input
                id="competition_code"
                className={styles.input}
                value={competitionCode}
                onChange={(event) => setCompetitionCode(event.target.value)}
                placeholder="e.g. EPL"
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor="competition_name">
                Competition Name
              </label>
              <input
                id="competition_name"
                className={styles.input}
                value={competitionName}
                onChange={(event) => setCompetitionName(event.target.value)}
                placeholder="e.g. Premier League"
              />
            </div>
          </div>

          <div className={styles.formActions}>
            <button type="submit" className={styles.primaryButton}>
              Apply Filters
            </button>

            <button
              type="button"
              className={styles.secondaryButton}
              onClick={handleClearFilters}
            >
              Clear Filters
            </button>
          </div>
        </form>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Merged Comparison Overview</h2>
          {comparison?.context?.season && (
            <span className={styles.badge}>{comparison.context.season}</span>
          )}
        </div>

        {loading ? (
          <div className={styles.emptyState}>Loading merged comparison…</div>
        ) : error ? (
          <div className={styles.emptyState}>{error}</div>
        ) : !comparison ? (
          <div className={styles.emptyState}>
            No merged deterministic comparison is available for the current player selection and filters.
          </div>
        ) : (
          <>
            <div className={styles.grid}>
              <div className={styles.emptyState}>
                <strong>Player A</strong>
                <div>{playerAName || 'Unknown player'}</div>
                <div>
                  {[
                    comparison.player_a.player.primary_position || comparison.player_a.player.position,
                    comparison.player_a.club?.name,
                  ]
                    .filter(Boolean)
                    .join(' · ') || 'No overview context'}
                </div>
              </div>

              <div className={styles.emptyState}>
                <strong>Player B</strong>
                <div>{playerBName || 'Unknown player'}</div>
                <div>
                  {[
                    comparison.player_b.player.primary_position || comparison.player_b.player.position,
                    comparison.player_b.club?.name,
                  ]
                    .filter(Boolean)
                    .join(' · ') || 'No overview context'}
                </div>
              </div>

              <div className={styles.emptyState}>
                <strong>Overall winner</strong>
                <div>
                  {comparison.overall_winner?.winner === 'player_a'
                    ? playerAName || 'Player A'
                    : comparison.overall_winner?.winner === 'player_b'
                      ? playerBName || 'Player B'
                      : comparison.overall_winner?.winner || 'No winner'}
                </div>
                <div>{comparison.overall_winner?.reason || 'No overall winner reason available.'}</div>
              </div>
            </div>

            {comparison.general_overview && (
              <div className={styles.emptyState}>
                {comparison.general_overview.headline && (
                  <strong>{comparison.general_overview.headline}</strong>
                )}
                {comparison.general_overview.summary && (
                  <div>{comparison.general_overview.summary}</div>
                )}
                {comparison.general_overview.strengths &&
                  comparison.general_overview.strengths.length > 0 && (
                    <div>Strengths: {comparison.general_overview.strengths.join(' · ')}</div>
                  )}
                {comparison.general_overview.watchouts &&
                  comparison.general_overview.watchouts.length > 0 && (
                    <div>Watchouts: {comparison.general_overview.watchouts.join(' · ')}</div>
                  )}
                {comparison.general_overview.notes &&
                  comparison.general_overview.notes.length > 0 && (
                    <div>Notes: {comparison.general_overview.notes.join(' · ')}</div>
                  )}
              </div>
            )}

            {comparison.summary_lines && comparison.summary_lines.length > 0 && (
              <div className={styles.emptyState}>
                <strong>Summary lines</strong>
                <div>{comparison.summary_lines.join(' · ')}</div>
              </div>
            )}

            {!comparison.has_comparison_data && comparison.missing_reasons?.length ? (
              <div className={styles.emptyState}>{comparison.missing_reasons.join(' ')}</div>
            ) : null}
          </>
        )}
      </section>

      {comparison?.provider_coverage && (
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Coverage and Freshness</h2>
            <span className={styles.badge}>
              {comparison.provider_coverage.coverage_status || 'unknown'}
            </span>
          </div>

          <div className={styles.grid}>
            <div className={styles.emptyState}>
              <strong>Available sources</strong>
              <div>{availableSourcesLine || 'None'}</div>
            </div>

            <div className={styles.emptyState}>
              <strong>Missing sources</strong>
              <div>{missingSourcesLine || 'None'}</div>
            </div>

            <div className={styles.emptyState}>
              <strong>Freshness</strong>
              <div>{comparisonFreshnessLine || 'Unknown'}</div>
            </div>

            <div className={styles.emptyState}>
              <strong>Coverage notes</strong>
              <div>
                {comparison.provider_coverage.coverage_notes?.length
                  ? comparison.provider_coverage.coverage_notes.join(' · ')
                  : 'No coverage notes available.'}
              </div>
            </div>
          </div>
        </section>
      )}

      {(comparison?.metric_groups ?? []).map(renderMetricGroup)}

      {(playerAProfileUrl || playerBProfileUrl) && (
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Related Navigation</h2>
          </div>

          {pageValidationMessage ? (
            <div className={styles.emptyState}>{pageValidationMessage}</div>
          ) : (
            <div className={styles.linksRow}>
              {playerAProfileUrl && (
                <Link to={playerAProfileUrl} className={styles.secondaryButton}>
                  {playerAName ? `Open ${playerAName}` : 'Open Player A'}
                </Link>
              )}

              {playerBProfileUrl && (
                <Link to={playerBProfileUrl} className={styles.secondaryButton}>
                  {playerBName ? `Open ${playerBName}` : 'Open Player B'}
                </Link>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
};

export default InternalPlayerComparisonPage;