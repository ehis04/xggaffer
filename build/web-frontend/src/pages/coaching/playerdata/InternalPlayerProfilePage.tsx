import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { clubsApi } from '../../../services/api';
import { playerdataApi } from '../../../services/api/playerdataApi';
import type { Club } from '../../../types/club';
import type {
  EnrichedPlayerListItem,
  PlayerOverview,
  PlayerOverviewMetricGroup,
} from '../../../types/playerdata';
import styles from './css/InternalPlayerProfilePage.module.css';

const getMetricValue = (metric: { formatted_value?: string | null; value?: number | null }): string => {
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

// ── Metric group panel ──────────────────────────────────────────────────────

const MetricGroup: React.FC<{ group: PlayerOverviewMetricGroup }> = ({ group }) => {
  const visible = (group.metrics ?? []).filter((m) => m.is_available !== false);
  if (visible.length === 0) return null;

  return (
    <div className={styles.panel} style={{ marginBottom: '1rem' }}>
      <h3 className={styles.metricGroupTitle}>{group.label}</h3>
      <div className={styles.metricGrid}>
        {visible.map((metric) => (
          <div key={metric.key} className={styles.metricCard}>
            <div className={styles.metricValue}>{getMetricValue(metric)}</div>
            <div className={styles.metricLabel}>{metric.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ── Page ────────────────────────────────────────────────────────────────────

const InternalPlayerProfilePage: React.FC = () => {
  const [proClubs, setProClubs] = useState<Club[]>([]);
  const [clubsLoading, setClubsLoading] = useState(true);

  const [selectedClub, setSelectedClub] = useState<Club | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const [players, setPlayers] = useState<EnrichedPlayerListItem[]>([]);
  const [playersLoading, setPlayersLoading] = useState(false);

  const [selectedPlayer, setSelectedPlayer] = useState<EnrichedPlayerListItem | null>(null);
  const [overview, setOverview] = useState<PlayerOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // Load professional clubs on mount
  useEffect(() => {
    const load = async () => {
      try {
        const clubs = await clubsApi.browse();
        setProClubs(clubs.filter((c) => c.club_type === 'system_professional'));
      } catch {
        // non-fatal
      } finally {
        setClubsLoading(false);
      }
    };
    void load();
  }, []);

  // Load enriched players when club or search changes
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
        if (active) setPlayers(result.results);
      } catch {
        if (active) setPlayers([]);
      } finally {
        if (active) setPlayersLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [selectedClub, searchQuery]);

  // Load overview when player selected
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
        if (active) setOverview(result);
      } catch (err) {
        if (active) {
          setOverview(null);
          setOverviewError(err instanceof Error ? err.message : 'Could not load player data.');
        }
      } finally {
        if (active) setOverviewLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [selectedPlayer]);

  const handleSelectClub = (club: Club) => {
    if (selectedClub?.id === club.id) {
      setSelectedClub(null);
    } else {
      setSelectedClub(club);
    }
    setSelectedPlayer(null);
    setOverview(null);
    setSearchQuery('');
  };

  const handleSelectPlayer = (item: EnrichedPlayerListItem) => {
    setSelectedPlayer(item);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
  };

  const metricGroups = useMemo(
    () => (overview?.metric_groups ?? []).filter((g) => (g.metrics ?? []).some((m) => m.is_available !== false)),
    [overview]
  );

  const playerDisplayName =
    overview?.player.display_name ||
    overview?.player.full_name ||
    overview?.player.short_name ||
    selectedPlayer?.player.display_name ||
    selectedPlayer?.player.full_name ||
    '';

  const contextLine = overview ? buildContextLine(overview) : '';
  const canonicalId = selectedPlayer?.player?.id ?? null;

  return (
    <div className={styles.container}>
      {/* Hero */}
      <section className={styles.hero}>
        <div>
          <h1 className={styles.title}>Player Data</h1>
          <p className={styles.subtitle}>
            Select a club below, then choose a player to view their career stats. You can also search by name across all clubs.
          </p>
        </div>
      </section>

      {/* Club picker */}
      {clubsLoading ? (
        <div className={styles.loading}>Loading clubs…</div>
      ) : (
        <div className={styles.clubGrid}>
          {proClubs.map((club) => (
            <button
              key={club.id}
              type="button"
              className={`${styles.clubCard} ${selectedClub?.id === club.id ? styles.clubCardActive : ''}`}
              onClick={() => handleSelectClub(club)}
            >
              <div className={styles.clubCardName}>{club.name}</div>
              <div className={styles.clubCardLeague}>{club.division || club.city}</div>
            </button>
          ))}
        </div>
      )}

      {/* Search */}
      <div className={styles.searchBar}>
        <input
          className={styles.searchInput}
          type="text"
          placeholder={selectedClub ? `Search players in ${selectedClub.name}…` : 'Search by player name…'}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {(searchQuery || selectedClub) && (
          <button
            type="button"
            className={styles.clearButton}
            onClick={() => {
              handleClearSearch();
              setSelectedClub(null);
              setSelectedPlayer(null);
              setOverview(null);
            }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Player list */}
      {playersLoading ? (
        <div className={styles.loading}>Loading players…</div>
      ) : players.length > 0 ? (
        <div className={styles.playerList}>
          {players.map((item) => {
            const name = item.player.display_name || item.player.full_name || `Player ${item.player.id}`;
            const meta = [item.player.position, item.player.nationality].filter(Boolean).join(' · ');
            const isActive = selectedPlayer?.player?.id === item.player.id;
            return (
              <button
                key={item.player.id}
                type="button"
                className={`${styles.playerRow} ${isActive ? styles.playerRowActive : ''}`}
                onClick={() => handleSelectPlayer(item)}
              >
                <div>
                  <div className={styles.playerName}>{name}</div>
                  {meta && <div className={styles.playerMeta}>{meta}</div>}
                </div>
                <span className={styles.playerRowArrow}>→</span>
              </button>
            );
          })}
        </div>
      ) : (selectedClub || searchQuery.trim()) && !playersLoading ? (
        <div className={styles.empty}>
          No players found. Try a different search term or club.
        </div>
      ) : null}

      {/* Player overview */}
      {selectedPlayer && (
        <>
          {overviewLoading && <div className={styles.loading}>Loading player data…</div>}
          {overviewError && <div className={styles.error}>{overviewError}</div>}

          {overview && !overviewLoading && (
            <>
              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <h2 className={styles.playerFullName}>{playerDisplayName}</h2>
                    {contextLine && <p className={styles.playerContext}>{contextLine}</p>}
                  </div>
                  <div className={styles.panelActions}>
                    {canonicalId && (
                      <Link
                        to={`/coaching/playerdata/compare?player_a_id=${canonicalId}`}
                        className={styles.secondaryButton}
                      >
                        Compare
                      </Link>
                    )}
                  </div>
                </div>

                {!overview.has_overview_data && (
                  <div className={styles.notice}>
                    {overview.missing_reasons?.join(' ') || 'No enrichment data is available for this player yet.'}
                  </div>
                )}

                {overview.general_overview?.summary && (
                  <p style={{ color: 'rgba(255,255,255,0.75)', fontSize: '0.93rem', margin: 0 }}>
                    {overview.general_overview.summary}
                  </p>
                )}
              </div>

              {metricGroups.map((group) => (
                <MetricGroup key={group.key} group={group} />
              ))}

              {metricGroups.length === 0 && overview.has_overview_data && (
                <div className={styles.empty}>Stats are available but not yet organised into display groups.</div>
              )}
            </>
          )}
        </>
      )}

      {!selectedPlayer && !selectedClub && !searchQuery.trim() && (
        <div className={styles.empty}>
          Select a club above or search by name to browse players.
        </div>
      )}
    </div>
  );
};

export default InternalPlayerProfilePage;
