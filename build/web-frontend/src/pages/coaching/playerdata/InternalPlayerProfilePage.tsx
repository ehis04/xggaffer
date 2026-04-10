import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import LeagueSelector from '../../../components/playerdiscovery/LeagueSelector';
import ClubSelector from '../../../components/playerdiscovery/ClubSelector';
import PlayerSelector from '../../../components/playerdiscovery/PlayerSelector';
import PlayerSearchInput from '../../../components/playerdiscovery/PlayerSearchInput';
import { usePlayerDiscovery } from '../../../hooks/usePlayerDiscovery';
import { playerdataApi } from '../../../services/api/playerdataApi';
import type {
  MergedProviderCoverage,
  PlayerDataFilters,
  PlayerOverview,
  PlayerOverviewMetric,
  PlayerOverviewMetricGroup,
} from '../../../types/playerdata';
import type { PlayerLookupItem } from '../../../types/livefootball';
import styles from './css/InternalPlayerProfilePage.module.css';

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

const parsePositiveInt = (value: string | null | undefined): number | null => {
  if (!value) {
    return null;
  }

  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }

  return parsed;
};

const cleanFilter = (value: string | null): string | undefined => {
  if (!value) {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
};

const formatTimestamp = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString('en-IE', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

const buildCompareUrl = (
  playerId: number,
  compareToId: number,
  options?: {
    filters?: PlayerDataFilters;
    fromClubId?: number | null;
    clubPlayerId?: number | null;
    returnToPlayerId?: number | null;
  }
): string => {
  const params = new URLSearchParams({
    player_a_id: String(playerId),
    player_b_id: String(compareToId),
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

  if (
    options?.returnToPlayerId &&
    Number.isInteger(options.returnToPlayerId) &&
    options.returnToPlayerId > 0
  ) {
    params.set('returnToPlayerId', String(options.returnToPlayerId));
  }

  return `/coaching/playerdata/compare?${params.toString()}`;
};

const buildClubPlayersUrl = (clubId: number | null): string => {
  if (clubId && Number.isInteger(clubId) && clubId > 0) {
    return `/clubs/${clubId}/players`;
  }

  return '/clubs';
};

const getPreferredMetricValue = (metric: PlayerOverviewMetric): string => {
  if (metric.formatted_value) {
    return metric.formatted_value;
  }

  if (metric.value === null || metric.value === undefined) {
    return '—';
  }

  return String(metric.value);
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

const buildLookupPlayerSummary = (player?: PlayerLookupItem | null): string => {
  if (!player) {
    return '';
  }

  return [
    player.player_name,
    player.team?.name || null,
    player.primary_position || player.raw_position || null,
    player.nationality || null,
  ]
    .filter(Boolean)
    .join(' · ');
};

const renderMetricGroup = (group: PlayerOverviewMetricGroup, groupIndex: number) => (
  <div key={`${group.key}-${groupIndex}`} className={styles.panel}>
    <div className={styles.panelHeader}>
      <h2 className={styles.panelTitle}>{group.label}</h2>
      <span className={styles.badge}>{group.metrics?.length ?? 0} metrics</span>
    </div>

    {group.metrics && group.metrics.length > 0 ? (
      <div className={styles.filterGrid}>
        {group.metrics.map((metric) => (
          <div key={metric.key} className={styles.emptyState}>
            <strong>{metric.label}</strong>
            <div>{getPreferredMetricValue(metric)}</div>
            <div>
              {[metric.source, metric.preferred_provider].filter(Boolean).join(' · ') || 'Merged metric'}
            </div>
          </div>
        ))}
      </div>
    ) : (
      <div className={styles.emptyState}>No metrics are available in this group.</div>
    )}
  </div>
);

const InternalPlayerProfilePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const routeParams = useParams<{ playerId?: string }>();

  const queryPlayerId = useMemo(
    () => parsePositiveInt(searchParams.get('playerId')),
    [searchParams]
  );

  const routePlayerId = useMemo(
    () => parsePositiveInt(routeParams.playerId ?? null),
    [routeParams.playerId]
  );

  const playerId = queryPlayerId ?? routePlayerId;

  const fromClubId = useMemo(
    () => parsePositiveInt(searchParams.get('fromClubId')),
    [searchParams]
  );

  const clubPlayerId = useMemo(
    () => parsePositiveInt(searchParams.get('clubPlayerId')),
    [searchParams]
  );

  const initialSeason = cleanFilter(searchParams.get('season')) ?? '';
  const initialProvider = cleanFilter(searchParams.get('provider')) ?? '';
  const initialCompetitionCode = cleanFilter(searchParams.get('competition_code')) ?? '';
  const initialCompetitionName = cleanFilter(searchParams.get('competition_name')) ?? '';

  const [season, setSeason] = useState(initialSeason);
  const [provider, setProvider] = useState(initialProvider);
  const [competitionCode, setCompetitionCode] = useState(initialCompetitionCode);
  const [competitionName, setCompetitionName] = useState(initialCompetitionName);

  const [overview, setOverview] = useState<PlayerOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [compareSearchQuery, setCompareSearchQuery] = useState('');
  const [compareCandidate, setCompareCandidate] = useState<PlayerLookupItem | null>(null);

  const discovery = usePlayerDiscovery();

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

  const updateProfileSearchParam = (canonicalPlayerId: number | null) => {
    const nextParams = new URLSearchParams(searchParams);

    if (canonicalPlayerId && Number.isInteger(canonicalPlayerId) && canonicalPlayerId > 0) {
      nextParams.set('playerId', String(canonicalPlayerId));
    } else {
      nextParams.delete('playerId');
    }

    setSearchParams(nextParams);
  };

  const handleDiscoveryPlayerChange = (player: PlayerLookupItem | null) => {
    discovery.setPlayer(player);

    const canonicalId = discovery.getCanonicalPlayerId(player);

    if (canonicalId) {
      updateProfileSearchParam(canonicalId);
    }
  };

  const handleOpenProfileFromSearch = (canonicalPlayerId: number, player: PlayerLookupItem) => {
    discovery.selectSearchResult(player);
    updateProfileSearchParam(canonicalPlayerId);
  };

  const handleOpenResolvedProfile = () => {
    if (discovery.resolvedCanonicalPlayerId) {
      updateProfileSearchParam(discovery.resolvedCanonicalPlayerId);
    }
  };

  const activeCompetitionId =
    discovery.selectedCompetitionId ?? overview?.context?.competition_id ?? null;

  const activeTeamId = discovery.selectedTeamId ?? null;

  useEffect(() => {
    if (!playerId) {
      setOverview(null);
      setError(null);
      setLoading(false);
      return;
    }

    let isActive = true;

    const loadOverview = async () => {
      try {
        setLoading(true);
        setError(null);

        const result = await playerdataApi.getPlayerOverview(playerId, filters);

        if (!isActive) {
          return;
        }

        setOverview(result);
      } catch (err) {
        if (!isActive) {
          return;
        }

        setOverview(null);
        setError(normalizeError(err));
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void loadOverview();

    return () => {
      isActive = false;
    };
  }, [playerId, filters]);

  const compareToId = useMemo(
    () => discovery.getCanonicalPlayerId(compareCandidate),
    [compareCandidate, discovery]
  );

  const compareUrl = useMemo(() => {
    if (!playerId || !compareToId || compareToId === playerId) {
      return null;
    }

    return buildCompareUrl(playerId, compareToId, {
      filters,
      fromClubId,
      clubPlayerId,
      returnToPlayerId: playerId,
    });
  }, [playerId, compareToId, filters, fromClubId, clubPlayerId]);

  const compareValidationMessage = useMemo(() => {
    if (!compareCandidate) {
      return null;
    }

    if (!compareToId) {
      return 'The selected compare player does not have a canonical player link yet.';
    }

    if (playerId && compareToId === playerId) {
      return 'Choose a different player for comparison.';
    }

    return null;
  }, [compareCandidate, compareToId, playerId]);

  const handleApplyFilters = (event: React.FormEvent) => {
    event.preventDefault();

    const nextParams = new URLSearchParams(searchParams);

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

  const pageTitle =
    overview?.player?.display_name ||
    overview?.player?.full_name ||
    overview?.player?.short_name ||
    'Internal Player Profile';

  const contextLine = [
    overview?.club?.name,
    overview?.context?.competition_name,
    overview?.context?.season,
  ]
    .filter(Boolean)
    .join(' · ');

  const providerBadge =
    overview?.provider_coverage?.provider ||
    overview?.context?.provider ||
    null;

  const freshnessLine = buildFreshnessLine(overview?.provider_coverage);
  const coverageLine = buildCoverageSummaryLine(overview?.provider_coverage);

  const positionLine = [
    overview?.player?.primary_position || overview?.player?.position,
    overview?.player?.nationality,
    overview?.player?.age != null ? `${overview.player.age} years old` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  const availableSourcesLine = overview?.provider_coverage?.available_sources?.length
    ? overview.provider_coverage.available_sources.join(' · ')
    : '';

  const missingSourcesLine = overview?.provider_coverage?.missing_sources?.length
    ? overview.provider_coverage.missing_sources.join(' · ')
    : '';

  const backUrl = buildClubPlayersUrl(fromClubId);

  const originLine = [
    fromClubId ? `Club ${fromClubId}` : null,
    clubPlayerId ? `Club player row ${clubPlayerId}` : null,
    playerId ? `Canonical player ${playerId}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  const selectedDiscoverySummary = buildLookupPlayerSummary(discovery.resolvedActivePlayer);

  const discoveryCanonicalStatus = discovery.resolvedActivePlayer
    ? discovery.canOpenResolvedProfile
      ? `Canonical profile available (${discovery.resolvedCanonicalPlayerId})`
      : 'No canonical player link is available for the selected discovery player yet.'
    : null;

  const compareCandidateSummary = buildLookupPlayerSummary(compareCandidate);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Internal player read surface</p>
          <h1 className={styles.title}>{pageTitle}</h1>
          <p className={styles.subtitle}>
            {playerId ? `Player ID ${playerId}` : 'Select a player from discovery or search'}
          </p>
          {contextLine && <p className={styles.subtitle}>{contextLine}</p>}
          {positionLine && <p className={styles.subtitle}>{positionLine}</p>}
          {freshnessLine && <p className={styles.subtitle}>{freshnessLine}</p>}
          {coverageLine && <p className={styles.subtitle}>{coverageLine}</p>}
        </div>

        <div className={styles.headerActions}>
          <Link to={backUrl} className={styles.secondaryButton}>
            {fromClubId ? 'Back to Club Players' : 'Back to Clubs'}
          </Link>

          {compareUrl && (
            <Link to={compareUrl} className={styles.primaryButton}>
              Compare Players
            </Link>
          )}
        </div>
      </div>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Discovery and Selection</h2>
          <span className={styles.badge}>Internal only</span>
        </div>

        <div className={styles.filterGrid}>
          <div className={styles.formGroup}>
            <LeagueSelector
              value={discovery.selectedCompetitionId}
              onChange={discovery.setCompetition}
              label="League"
              placeholder="Select a league"
            />
          </div>

          <div className={styles.formGroup}>
            <ClubSelector
              competitionId={discovery.selectedCompetitionId}
              value={discovery.selectedTeamId}
              onChange={discovery.setTeam}
              label="Club"
              placeholder="Select a club"
            />
          </div>

          <div className={styles.formGroup}>
            <PlayerSelector
              competitionId={activeCompetitionId}
              teamId={discovery.selectedTeamId}
              value={discovery.selectedPlayerDirectoryId}
              onChange={handleDiscoveryPlayerChange}
              label="Player"
              placeholder="Select a player"
            />
          </div>
        </div>

        <PlayerSearchInput
          query={discovery.searchQuery}
          onQueryChange={discovery.setSearchQuery}
          onSelectResult={discovery.selectSearchResult}
          onOpenProfile={handleOpenProfileFromSearch}
          competitionId={activeCompetitionId}
          teamId={activeTeamId}
          season={filters.season}
          activeOnly={true}
          helperText="Use direct name search when you do not want to browse by league and club first."
        />

        {selectedDiscoverySummary ? (
          <div className={styles.emptyState}>
            <strong>Selected discovery player</strong>
            <div>{selectedDiscoverySummary}</div>
            {discoveryCanonicalStatus && <div>{discoveryCanonicalStatus}</div>}
          </div>
        ) : (
          <div className={styles.emptyState}>
            Browse by league and club or search by player name to open the merged profile.
          </div>
        )}

        <div className={styles.formActions}>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={handleOpenResolvedProfile}
            disabled={!discovery.canOpenResolvedProfile}
          >
            Open Selected Profile
          </button>

          <button
            type="button"
            className={styles.secondaryButton}
            onClick={discovery.resetAll}
          >
            Clear Discovery
          </button>
        </div>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Read Context</h2>
          <span className={styles.badge}>Internal only</span>
        </div>

        {originLine ? (
          <div className={styles.emptyState}>{originLine}</div>
        ) : (
          <div className={styles.emptyState}>
            This read page is operating without club-origin context.
          </div>
        )}
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Overview Filters</h2>
          <span className={styles.badge}>Read only</span>
        </div>

        <form className={styles.filterForm} onSubmit={handleApplyFilters}>
          <div className={styles.filterGrid}>
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
          <h2 className={styles.panelTitle}>Merged Player Overview</h2>
          {providerBadge && <span className={styles.badge}>{providerBadge}</span>}
        </div>

        {loading ? (
          <div className={styles.emptyState}>Loading merged player overview…</div>
        ) : error ? (
          <div className={styles.emptyState}>{error}</div>
        ) : !playerId ? (
          <div className={styles.emptyState}>
            No player profile is open yet. Use the discovery tools above to select a player with a canonical profile link.
          </div>
        ) : !overview ? (
          <div className={styles.emptyState}>
            No merged player overview is available for this selection.
          </div>
        ) : (
          <>
            {overview.general_overview && (
              <div className={styles.emptyState}>
                {overview.general_overview.headline && (
                  <strong>{overview.general_overview.headline}</strong>
                )}
                {overview.general_overview.summary && (
                  <div>{overview.general_overview.summary}</div>
                )}
                {overview.general_overview.strengths &&
                  overview.general_overview.strengths.length > 0 && (
                    <div>Strengths: {overview.general_overview.strengths.join(' · ')}</div>
                  )}
                {overview.general_overview.watchouts &&
                  overview.general_overview.watchouts.length > 0 && (
                    <div>Watchouts: {overview.general_overview.watchouts.join(' · ')}</div>
                  )}
                {overview.general_overview.notes &&
                  overview.general_overview.notes.length > 0 && (
                    <div>Notes: {overview.general_overview.notes.join(' · ')}</div>
                  )}
              </div>
            )}

            {!overview.has_overview_data && overview.missing_reasons?.length ? (
              <div className={styles.emptyState}>{overview.missing_reasons.join(' ')}</div>
            ) : null}
          </>
        )}
      </section>

      {overview?.provider_coverage && (
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Coverage and Freshness</h2>
            <span className={styles.badge}>
              {overview.provider_coverage.coverage_status || 'unknown'}
            </span>
          </div>

          <div className={styles.filterGrid}>
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
              <div>{freshnessLine || 'Unknown'}</div>
            </div>

            <div className={styles.emptyState}>
              <strong>Coverage notes</strong>
              <div>
                {overview.provider_coverage.coverage_notes?.length
                  ? overview.provider_coverage.coverage_notes.join(' · ')
                  : 'No coverage notes available.'}
              </div>
            </div>
          </div>
        </section>
      )}

      {(overview?.metric_groups ?? []).map(renderMetricGroup)}

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Comparison Entry Point</h2>
          <span className={styles.badge}>Deterministic</span>
        </div>

        <PlayerSearchInput
          query={compareSearchQuery}
          onQueryChange={setCompareSearchQuery}
          onSelectResult={setCompareCandidate}
          competitionId={activeCompetitionId}
          season={filters.season}
          activeOnly={true}
          helperText="Select a compare target by name. The compare page still uses canonical player identities underneath."
        />

        {compareCandidateSummary ? (
          <div className={styles.emptyState}>
            <strong>Selected compare player</strong>
            <div>{compareCandidateSummary}</div>
            <div>
              {compareToId
                ? `Canonical comparison target available (${compareToId})`
                : 'No canonical comparison target is available for this player yet.'}
            </div>
          </div>
        ) : null}

        {compareValidationMessage ? (
          <div className={styles.emptyState}>{compareValidationMessage}</div>
        ) : compareUrl ? (
          <div className={styles.formActions}>
            <Link to={compareUrl} className={styles.primaryButton}>
              Open Comparison Page
            </Link>
          </div>
        ) : (
          <div className={styles.emptyState}>
            Search for another player with a canonical profile link to launch a deterministic comparison.
          </div>
        )}
      </section>
    </div>
  );
};

export default InternalPlayerProfilePage;