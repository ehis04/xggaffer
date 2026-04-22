import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';
import { clubsApi } from '../../../services/api';
import { playerdataApi } from '../../../services/api/playerdataApi';
import type { Club } from '../../../types/club';
import type {
  EnrichedPlayerListItem,
  PlayerOverview,
  PlayerOverviewMetricGroup,
} from '../../../types/playerdata';
import styles from './css/InternalPlayerProfilePage.module.css';

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

const MetricGroup: React.FC<{ group: PlayerOverviewMetricGroup }> = ({ group }) => {
  const visible = (group.metrics ?? []).filter((m) => m.is_available !== false);
  if (visible.length === 0) return null;

  return (
    <div className={styles['ipp-panel']} style={{ marginBottom: '1rem' }}>
      <h3 className={styles['ipp-metric-group-title']}>{group.label}</h3>
      <div className={styles['ipp-metric-grid']}>
        {visible.map((metric) => (
          <div key={metric.key} className={styles['ipp-metric-card']}>
            <div className={styles['ipp-metric-value']}>{getMetricValue(metric)}</div>
            <div className={styles['ipp-metric-label']}>{metric.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

const InternalPlayerProfilePage: React.FC = () => {
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

  useEffect(() => {
    const load = async () => {
      try {
        const clubs = await clubsApi.browse();
        setProClubs(clubs.filter((c) => c.club_type === 'system_professional'));
      } catch {
      } finally {
        setClubsLoading(false);
      }
    };
    void load();
  }, []);

  useEffect(() => {
    if (!selectedClub && !searchQuery.trim()) {
      setPlayers([]);
      return;
    }
    let active = true;
    const load = async () => {
      try {
        setPlayersLoading(true);
        const result = await playerdataApi.listEnrichedPlayers({
          club_id: selectedClub?.id,
          search: searchQuery.trim() || undefined,
          season: '2024',
          provider: 'understat',
          limit: 80,
        });
        if (active) setPlayers(result.data?.results ?? []);
      } catch {
        if (active) setPlayers([]);
      } finally {
        if (active) setPlayersLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [selectedClub, searchQuery]);

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
          season: '2024',
          provider: 'understat',
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
  }, [selectedPlayer]);

  const handleSelectClub = (club: Club) => {
    setSelectedClub(selectedClub?.id === club.id ? null : club);
    setSelectedPlayer(null);
    setOverview(null);
    setSearchQuery('');
  };

  const handleClearAll = () => {
    setSearchQuery('');
    setSelectedClub(null);
    setSelectedPlayer(null);
    setOverview(null);
  };

  const metricGroups = useMemo(
    () =>
      (overview?.metric_groups ?? []).filter(
        (g) => (g.metrics ?? []).some((m) => m.is_available !== false),
      ),
    [overview],
  );

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
                    key={item.player.id}
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

                  {metricGroups.map((group) => (
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