import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Sidebar } from '../../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';
import { clubsApi } from '../../../services/api';
import { playerdataApi } from '../../../services/api/playerdataApi';
import type { Club } from '../../../types/club';
import type {
  EnrichedPlayerListItem,
  PlayerOverview,
  PlayerOverviewMetric,
  PlayerOverviewMetricGroup,
} from '../../../types/playerdata';
import { getCurrentFootballSeason } from '../../../utils/footballSeason';
import { dedupeEnrichedPlayers, getEnrichedPlayerListKey } from './playerListUtils';
import styles from './css/InternalPlayerProfilePage.module.css';

const ALLOWED_PRO_CLUBS = [
  'Manchester United FC',
  'Paris Saint-Germain FC',
  'FC Bayern München',
  'Real Madrid CF',
  'Juventus FC',
];

const getMetricValue = (
  metric: { formatted_value?: string | null; value?: number | null },
): string => {
  if (metric.formatted_value) return metric.formatted_value;
  if (metric.value === null || metric.value === undefined) return '—';
  return String(metric.value);
};

const buildContextLine = (overview: PlayerOverview): string =>
  [
    overview.club?.name,
    overview.player.primary_position || overview.player.position,
    overview.player.nationality,
    overview.player.age != null ? `${overview.player.age} yrs` : null,
  ]
    .filter(Boolean)
    .join(' · ');

const getPriority = (group: PlayerOverviewMetricGroup): number => {
  const value = `${group.key} ${group.label}`.toLowerCase();
  if (/(overview|general|identity|summary)/.test(value)) return 0;
  if (/(attacking|chance|scoring|finishing|xg|xa)/.test(value)) return 1;
  if (/(passing|progression|possession)/.test(value)) return 2;
  if (/(defensive|duel|pressing|recovery)/.test(value)) return 3;
  return 4;
};

const renderMetricCard = (
  metric: PlayerOverviewMetric,
  className: string,
): React.ReactNode => {
  const source = metric.preferred_provider || metric.source;
  const pct =
    typeof metric.percentile === 'number'
      ? Math.max(0, Math.min(100, metric.percentile))
      : null;
  return (
    <div key={metric.key} className={className}>
      <div className={styles['ipp-metric-value']}>{getMetricValue(metric)}</div>
      <div className={styles['ipp-metric-label']}>{metric.label}</div>
      {pct !== null && (
        <div className={styles['ipp-percentile-bar-wrap']}>
          <div
            className={styles['ipp-percentile-bar-fill']}
            style={{ width: `${pct}%` }}
          />
          <span className={styles['ipp-percentile-bar-label']}>{Math.round(pct)}th</span>
        </div>
      )}
      {source && <div className={styles['ipp-metric-source']}>{source}</div>}
    </div>
  );
};

const MetricGroup: React.FC<{ group: PlayerOverviewMetricGroup }> = ({ group }) => {
  const visible = (group.metrics ?? []).filter((m) => m.is_available !== false);
  if (visible.length === 0) return null;

  const coreMetrics = visible.slice(0, 6);
  const extraMetrics = visible.slice(6);

  return (
    <div className={styles['ipp-panel']} style={{ marginBottom: '1rem' }}>
      <div className={styles['ipp-group-head']}>
        <h3 className={styles['ipp-metric-group-title']}>{group.label}</h3>
        <span className={styles['ipp-metric-count']}>{visible.length} stats</span>
      </div>
      <div className={styles['ipp-metric-grid']}>
        {coreMetrics.map((metric) => renderMetricCard(metric, styles['ipp-metric-card']))}
      </div>
      <MetricBarsChart metrics={coreMetrics} />
      {extraMetrics.length > 0 && (
        <details className={styles['ipp-details']}>
          <summary className={styles['ipp-details-summary']}>
            Show {extraMetrics.length} more stats in {group.label}
          </summary>
          <div className={styles['ipp-metric-grid']}>
            {extraMetrics.map((metric) => renderMetricCard(metric, styles['ipp-metric-card']))}
          </div>
          <MetricBarsChart metrics={extraMetrics} />
        </details>
      )}
    </div>
  );
};

const ProviderCoveragePanel: React.FC<{ overview: PlayerOverview }> = ({ overview }) => {
  const sourceDetails = overview.provider_coverage?.source_details ?? null;
  if (!sourceDetails) return null;

  const rows = Object.entries(sourceDetails);
  if (!rows.length) return null;

  return (
    <div className={styles['ipp-panel']}>
      <h3 className={styles['ipp-metric-group-title']}>Source Coverage</h3>
      <div className={styles['ipp-source-grid']}>
        {rows.map(([name, detail]) => {
          const hasData = detail?.has_data !== false;
          const minutes = detail?.minutes_sampled ?? null;
          const matches = detail?.matches_sampled ?? null;
          return (
            <div key={name} className={styles['ipp-source-card']}>
              <div className={styles['ipp-source-head']}>
                <div className={styles['ipp-source-name']}>{name}</div>
                <span
                  className={`${styles['ipp-source-badge']} ${
                    hasData ? styles['ipp-source-badge--ok'] : styles['ipp-source-badge--off']
                  }`}
                >
                  {hasData ? 'available' : 'missing'}
                </span>
              </div>
              <div className={styles['ipp-source-meta']}>
                {detail?.freshness_label || 'Freshness not provided'}
              </div>
              <div className={styles['ipp-source-meta']}>
                {matches != null ? `${matches} matches` : 'matches n/a'} ·{' '}
                {minutes != null ? `${minutes} mins` : 'mins n/a'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const MetricBarsChart: React.FC<{ metrics: PlayerOverviewMetric[] }> = ({ metrics }) => {
  const withPct = metrics.filter(
    (m) => m.is_available !== false && typeof m.percentile === 'number' && Number.isFinite(m.percentile),
  );
  if (withPct.length < 2) return null;

  const barH = 18;
  const gap = 10;
  const labelW = 110;
  const barMaxW = 200;
  const pctLabelW = 30;
  const svgW = labelW + barMaxW + pctLabelW;
  const svgH = withPct.length * (barH + gap) - gap;

  return (
    <div className={styles['ipp-bars-wrap']}>
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        className={styles['ipp-bars-svg']}
        role="img"
        aria-label="Percentile bars"
      >
        {withPct.map((metric, i) => {
          const pct = Math.max(0, Math.min(100, metric.percentile ?? 0));
          const y = i * (barH + gap);
          const fillW = (pct / 100) * barMaxW;
          return (
            <g key={metric.key}>
              <text x={labelW - 6} y={y + barH / 2 + 4} textAnchor="end" className={styles['ipp-bars-label']}>
                {metric.label.length > 16 ? `${metric.label.slice(0, 14)}…` : metric.label}
              </text>
              <rect x={labelW} y={y} width={barMaxW} height={barH} rx={4} className={styles['ipp-bars-bg']} />
              <rect x={labelW} y={y} width={fillW} height={barH} rx={4} className={styles['ipp-bars-fill']} />
              <text x={labelW + fillW + 4} y={y + barH / 2 + 4} className={styles['ipp-bars-pct']}>
                {Math.round(pct)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

const PlayerRadar: React.FC<{ metricGroups: PlayerOverviewMetricGroup[] }> = ({ metricGroups }) => {
  const candidates = metricGroups
    .flatMap((group) => group.metrics ?? [])
    .filter(
      (metric) =>
        metric.is_available !== false &&
        typeof metric.percentile === 'number' &&
        Number.isFinite(metric.percentile),
    )
    .slice(0, 8);

  if (candidates.length < 2) return null;

  const cx = 120;
  const cy = 120;
  const radius = 80;

  const rings = [1, 0.66, 0.33];

  const getXY = (index: number, scale: number) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / candidates.length;
    return {
      x: cx + Math.cos(angle) * radius * scale,
      y: cy + Math.sin(angle) * radius * scale,
    };
  };

  const shapePoints = candidates
    .map((metric, i) => {
      const { x, y } = getXY(i, Math.max(0, Math.min(100, metric.percentile ?? 0)) / 100);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');

  return (
    <div className={styles['ipp-panel']}>
      <h3 className={styles['ipp-metric-group-title']}>Profile Shape (Percentiles)</h3>
      <div className={styles['ipp-radar-wrap']}>
        <svg viewBox="0 0 240 240" className={styles['ipp-radar-svg']} role="img" aria-label="Player percentile radar">
          {rings.map((r) => (
            <circle key={r} cx={cx} cy={cy} r={radius * r} className={styles['ipp-radar-ring']} />
          ))}
          {candidates.map((_, i) => {
            const outer = getXY(i, 1);
            return (
              <line
                key={i}
                x1={cx}
                y1={cy}
                x2={outer.x.toFixed(2)}
                y2={outer.y.toFixed(2)}
                className={styles['ipp-radar-spoke']}
              />
            );
          })}
          <polygon points={shapePoints} className={styles['ipp-radar-shape']} />
          {candidates.map((metric, i) => {
            const pos = getXY(i, 1.22);
            return (
              <text key={metric.key} x={pos.x.toFixed(2)} y={pos.y.toFixed(2)} textAnchor="middle" className={styles['ipp-radar-axis-label']}>
                {metric.label.length > 10 ? `${metric.label.slice(0, 9)}…` : metric.label}
              </text>
            );
          })}
        </svg>
        <div className={styles['ipp-radar-legend']}>
          {candidates.map((metric) => (
            <div key={metric.key} className={styles['ipp-radar-legend-row']}>
              <span>{metric.label}</span>
              <strong>{Math.round(metric.percentile ?? 0)}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const InternalPlayerProfilePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const season = searchParams.get('season') || getCurrentFootballSeason();
  const provider = searchParams.get('provider') || undefined;
  const [proClubs, setProClubs]         = useState<Club[]>([]);
  const [clubsLoading, setClubsLoading] = useState(true);

  const [selectedClub, setSelectedClub]   = useState<Club | null>(null);
  const [searchQuery, setSearchQuery]     = useState('');

  const [players, setPlayers]             = useState<EnrichedPlayerListItem[]>([]);
  const [playersLoading, setPlayersLoading] = useState(false);

  const [selectedPlayer, setSelectedPlayer] = useState<EnrichedPlayerListItem | null>(null);
  const [overview, setOverview]             = useState<PlayerOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewError, setOverviewError]   = useState<string | null>(null);
  const [showAdvancedGroups, setShowAdvancedGroups] = useState(false);

  // Auto-select player from URL params
  useEffect(() => {
    const playerIdParam = searchParams.get('playerId');
    if (playerIdParam && players.length > 0) {
      const playerId = Number(playerIdParam);
      const found = players.find(p => p.player?.id === playerId);
      if (found) {
        setSelectedPlayer(found);
      }
    }
  }, [searchParams, players]);

  // Filter to only show these specific clubs (matching exact names from database)
  useEffect(() => {
    const load = async () => {
      try {
        const clubs = await clubsApi.browse();
        setProClubs(
          clubs.filter((club) => 
            club.club_type === 'system_professional' && 
            ALLOWED_PRO_CLUBS.includes(club.name)
          ),
        );
      } catch {
        setProClubs([]);
      } finally {
        setClubsLoading(false);
      }
    };
    void load();
  }, []);

  useEffect(() => {
    // Load players when a club is selected OR when there's a search query
    if (!selectedClub && !searchQuery.trim()) {
      setPlayers([]);
      return;
    }
    let active = true;
    const load = async () => {
      try {
        setPlayersLoading(true);
        const result = await playerdataApi.listEnrichedPlayers({
          // Search across all allowed clubs when no club is selected
          club_id: selectedClub?.id,
          search: searchQuery.trim() || undefined,
          season,
          provider,
          limit: 80,
        });
        if (active) setPlayers(dedupeEnrichedPlayers(result.data?.results ?? []));
      } catch {
        if (active) setPlayers([]);
      } finally {
        if (active) setPlayersLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [selectedClub, searchQuery, season, provider]);

  useEffect(() => {
    const canonicalId = selectedPlayer?.player?.id;
    if (!canonicalId) {
      setOverview(null);
      setOverviewError(null);
      return;
    }
    let active = true;
    const load = async () => {
      try {
        setOverviewLoading(true);
        setOverviewError(null);
        const result = await playerdataApi.getPlayerOverview(canonicalId, {
          season,
          provider,
        });
        if (active) setOverview(result.data ?? null);
      } catch (err) {
        if (active) {
          setOverview(null);
          setOverviewError(
            err instanceof Error ? err.message : 'Could not load player data.',
          );
        }
      } finally {
        if (active) setOverviewLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [selectedPlayer, season, provider]);

  const handleSelectClub = (club: Club) => {
    setSelectedClub(selectedClub?.id === club.id ? null : club);
    setSelectedPlayer(null);
    setOverview(null);
    setSearchQuery('');
    setShowAdvancedGroups(false);
  };

  const handleClearAll = () => {
    setSearchQuery('');
    setSelectedClub(null);
    setSelectedPlayer(null);
    setOverview(null);
    setShowAdvancedGroups(false);
  };

  const metricGroups = useMemo(
    () =>
      (overview?.metric_groups ?? []).filter(
        (g) => (g.metrics ?? []).some((m) => m.is_available !== false),
      ).sort((a, b) => getPriority(a) - getPriority(b)),
    [overview],
  );

  const featuredGroups = metricGroups.slice(0, 2);
  const advancedGroups = metricGroups.slice(2);

  const playerDisplayName =
    overview?.player.display_name ||
    overview?.player.full_name ||
    overview?.player.short_name ||
    selectedPlayer?.player.display_name ||
    selectedPlayer?.player.full_name ||
    '';

  const contextLine  = overview ? buildContextLine(overview) : '';
  const canonicalId  = selectedPlayer?.player?.id ?? null;

  return (
    <div className={styles['ipp-root']}>
      <div className={styles['ipp-sidebar-section']}>
        <Sidebar />
      </div>

      <div className={styles['ipp-main']}>

        <header className={styles['ipp-header']}>
          <div className={styles['ipp-header-left']}>Player Data</div>
          <div className={styles['ipp-header-mid']} />
          <div className={styles['ipp-header-right']}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles['ipp-content']}>

          <section className={styles['ipp-hero']}>
            <h1 className={styles['ipp-title']}>Player Data</h1>
            <p className={styles['ipp-subtitle']}>
              Select a club below, then choose a player to view their season stats.
              You can also search by name across all clubs.
            </p>
          </section>

          {clubsLoading ? (
            <div className={styles['ipp-loading']}>Loading clubs…</div>
          ) : (
            <div className={styles['ipp-club-grid']}>
              {proClubs.map((club) => (
                <button
                  key={club.id}
                  type="button"
                  className={`${styles['ipp-club-card']} ${selectedClub?.id === club.id ? styles['ipp-club-card--active'] : ''}`}
                  onClick={() => handleSelectClub(club)}
                >
                  <div className={styles['ipp-club-card-name']}>{club.name}</div>
                  <div className={styles['ipp-club-card-league']}>{club.division || club.city}</div>
                </button>
              ))}
            </div>
          )}

          <div className={styles['ipp-search-bar']}>
            <input
              className={styles['ipp-search-input']}
              type="text"
              placeholder={
                selectedClub
                  ? `Search players in ${selectedClub.name}…`
                  : 'Search by player name…'
              }
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {(searchQuery || selectedClub) && (
              <button
                type="button"
                className={styles['ipp-clear-btn']}
                onClick={handleClearAll}
              >
                Clear
              </button>
            )}
          </div>

          {playersLoading ? (
            <div className={styles['ipp-loading']}>Loading players…</div>
          ) : players.length > 0 ? (
            <div className={styles['ipp-player-list']}>
              {players.map((item) => {
                const name =
                  item.player.display_name ||
                  item.player.full_name ||
                  `Player ${item.player.id}`;
                const meta = [item.player.position, item.player.nationality]
                  .filter(Boolean)
                  .join(' · ');
                const isActive = selectedPlayer?.player?.id === item.player.id;
                return (
                  <button
                    key={getEnrichedPlayerListKey(item)}
                    type="button"
                    className={`${styles['ipp-player-row']} ${isActive ? styles['ipp-player-row--active'] : ''}`}
                    onClick={() => setSelectedPlayer(item)}
                  >
                    <div>
                      <div className={styles['ipp-player-name']}>{name}</div>
                      {meta && <div className={styles['ipp-player-meta']}>{meta}</div>}
                    </div>
                    <span className={styles['ipp-player-arrow']}>→</span>
                  </button>
                );
              })}
            </div>
          ) : (selectedClub || searchQuery.trim()) && !playersLoading ? (
            <div className={styles['ipp-empty']}>
              No players found. Try a different search term or club.
            </div>
          ) : null}

          {selectedPlayer && (
            <>
              {overviewLoading && (
                <div className={styles['ipp-loading']}>Loading player data…</div>
              )}
              {overviewError && (
                <div className={styles['ipp-error']}>{overviewError}</div>
              )}

              {overview && !overviewLoading && (
                <>
                  <div className={styles['ipp-panel']}>
                    <div className={styles['ipp-panel-header']}>
                      <div>
                        <h2 className={styles['ipp-player-full-name']}>
                          {playerDisplayName}
                        </h2>
                        {contextLine && (
                          <p className={styles['ipp-player-context']}>{contextLine}</p>
                        )}
                      </div>
                      <div className={styles['ipp-panel-actions']}>
                        {canonicalId && (
                          <Link
                            to={`/coaching/playerdata/compare?player_a_id=${canonicalId}`}
                            className={styles['ipp-compare-btn']}
                          >
                            Compare
                          </Link>
                        )}
                      </div>
                    </div>

                    {!overview.has_overview_data && (
                      <div className={styles['ipp-notice']}>
                        {overview.missing_reasons?.join(' ') ||
                          'No enrichment data is available for this player yet.'}
                      </div>
                    )}

                    {overview.general_overview?.summary && (
                      <p className={styles['ipp-summary']}>
                        {overview.general_overview.summary}
                      </p>
                    )}
                  </div>

                  <PlayerRadar metricGroups={metricGroups} />
                  <ProviderCoveragePanel overview={overview} />

                  {featuredGroups.map((group) => (
                    <MetricGroup key={group.key} group={group} />
                  ))}

                  {advancedGroups.length > 0 && (
                    <div className={styles['ipp-panel']}>
                      <div className={styles['ipp-advanced-header']}>
                        <h3 className={styles['ipp-metric-group-title']}>Advanced Stat Groups</h3>
                        <button
                          type="button"
                          className={styles['ipp-toggle-btn']}
                          onClick={() => setShowAdvancedGroups((value) => !value)}
                        >
                          {showAdvancedGroups
                            ? 'Hide advanced stats'
                            : `Show ${advancedGroups.length} more groups`}
                        </button>
                      </div>
                      {!showAdvancedGroups && (
                        <p className={styles['ipp-summary']}>
                          Core groups are shown first. Open advanced groups for deeper provider-level detail.
                        </p>
                      )}
                    </div>
                  )}

                  {showAdvancedGroups && advancedGroups.map((group) => (
                    <MetricGroup key={group.key} group={group} />
                  ))}

                  {metricGroups.length === 0 && overview.has_overview_data && (
                    <div className={styles['ipp-empty']}>
                      Stats are available but not yet organised into display groups.
                    </div>
                  )}
                </>
              )}
            </>
          )}

          {!selectedPlayer && !selectedClub && !searchQuery.trim() && (
            <div className={styles['ipp-empty']}>
              Select a club above or search by name to browse players.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InternalPlayerProfilePage;
