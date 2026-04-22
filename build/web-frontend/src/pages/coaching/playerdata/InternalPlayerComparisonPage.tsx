import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { clubsApi } from '../../../services/api';
import { playerdataApi } from '../../../services/api/playerdataApi';
import type { Club } from '../../../types/club';
import type {
  EnrichedPlayerListItem,
  PlayerOverviewComparison,
  PlayerOverviewComparisonMetricGroup,
} from '../../../types/playerdata';
import styles from './css/InternalPlayerComparisonPage.module.css';

const SEASON = '2024';
const PROVIDER = 'understat';

// ── Metric group ────────────────────────────────────────────────────────────

const ComparisonMetricGroup: React.FC<{
  group: PlayerOverviewComparisonMetricGroup;
}> = ({ group }) => {
  const visible = (group.metrics ?? []).filter((m) => m.is_comparable !== false);
  if (visible.length === 0) return null;

  return (
    <div className={styles.panel} style={{ marginBottom: '1rem' }}>
      <h3 className={styles.metricGroupTitle}>{group.label}</h3>
      <div className={styles.metricTable}>
        {visible.map((metric) => {
          const valA = metric.player_a_formatted ?? (metric.player_a_value != null ? String(metric.player_a_value) : '—');
          const valB = metric.player_b_formatted ?? (metric.player_b_value != null ? String(metric.player_b_value) : '—');
          const winA = metric.winner === 'player_a';
          const winB = metric.winner === 'player_b';
          return (
            <div key={metric.key} className={styles.metricRow}>
              <div className={`${styles.metricVal} ${styles.metricValLeft} ${winA ? styles.metricWinner : ''}`}>
                {valA}
              </div>
              <div className={styles.metricLabel}>{metric.label}</div>
              <div className={`${styles.metricVal} ${styles.metricValRight} ${winB ? styles.metricWinner : ''}`}>
                {valB}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── Player picker column ─────────────────────────────────────────────────────

interface PlayerPickerProps {
  label: string;
  proClubs: Club[];
  clubsLoading: boolean;
  selectedClub: Club | null;
  onSelectClub: (club: Club) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  players: EnrichedPlayerListItem[];
  playersLoading: boolean;
  selectedPlayer: EnrichedPlayerListItem | null;
  onSelectPlayer: (item: EnrichedPlayerListItem) => void;
  onClear: () => void;
}

const PlayerPicker: React.FC<PlayerPickerProps> = ({
  label,
  proClubs,
  clubsLoading,
  selectedClub,
  onSelectClub,
  searchQuery,
  onSearchChange,
  players,
  playersLoading,
  selectedPlayer,
  onSelectPlayer,
  onClear,
}) => (
  <div className={styles.pickerColumn}>
    <div className={styles.pickerHeader}>
      <span className={styles.pickerLabel}>{label}</span>
      {selectedPlayer && (
        <button type="button" className={styles.clearButton} onClick={onClear}>
          Clear
        </button>
      )}
    </div>

    {selectedPlayer ? (
      <div className={styles.selectedPlayer}>
        <div className={styles.selectedPlayerName}>
          {selectedPlayer.player.display_name || selectedPlayer.player.full_name}
        </div>
        <div className={styles.selectedPlayerMeta}>
          {[selectedPlayer.player.position, selectedPlayer.club?.name].filter(Boolean).join(' · ')}
        </div>
      </div>
    ) : (
      <>
        {clubsLoading ? (
          <div className={styles.hint}>Loading clubs…</div>
        ) : (
          <div className={styles.miniClubGrid}>
            {proClubs.map((club) => (
              <button
                key={club.id}
                type="button"
                className={`${styles.miniClubCard} ${selectedClub?.id === club.id ? styles.miniClubCardActive : ''}`}
                onClick={() => onSelectClub(club)}
              >
                {club.name}
              </button>
            ))}
          </div>
        )}

        <input
          className={styles.searchInput}
          type="text"
          placeholder={selectedClub ? `Search in ${selectedClub.name}…` : 'Search by name…'}
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />

        {playersLoading ? (
          <div className={styles.hint}>Loading…</div>
        ) : players.length > 0 ? (
          <div className={styles.playerList}>
            {players.map((item) => {
              const name = item.player.display_name || item.player.full_name || `Player ${item.player.id}`;
              const meta = [item.player.position, item.player.nationality].filter(Boolean).join(' · ');
              return (
                <button
                  key={item.player.id}
                  type="button"
                  className={styles.playerRow}
                  onClick={() => onSelectPlayer(item)}
                >
                  <div className={styles.playerName}>{name}</div>
                  {meta && <div className={styles.playerMeta}>{meta}</div>}
                </button>
              );
            })}
          </div>
        ) : (selectedClub || searchQuery.trim()) ? (
          <div className={styles.hint}>No players found.</div>
        ) : (
          <div className={styles.hint}>Select a club or search by name.</div>
        )}
      </>
    )}
  </div>
);

// ── Page ─────────────────────────────────────────────────────────────────────

const InternalPlayerComparisonPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  // Optional pre-population from profile page "Compare" button
  const playerAIdFromUrl = useMemo(() => {
    const v = searchParams.get('player_a_id');
    const n = v ? Number(v) : NaN;
    return Number.isInteger(n) && n > 0 ? n : null;
  }, [searchParams]);

  // Clubs
  const [proClubs, setProClubs] = useState<Club[]>([]);
  const [clubsLoading, setClubsLoading] = useState(true);

  // Player A
  const [clubA, setClubA] = useState<Club | null>(null);
  const [searchA, setSearchA] = useState('');
  const [playersA, setPlayersA] = useState<EnrichedPlayerListItem[]>([]);
  const [loadingA, setLoadingA] = useState(false);
  const [selectedA, setSelectedA] = useState<EnrichedPlayerListItem | null>(null);
  const [preloadedAName, setPreloadedAName] = useState<string | null>(null);

  // Player B
  const [clubB, setClubB] = useState<Club | null>(null);
  const [searchB, setSearchB] = useState('');
  const [playersB, setPlayersB] = useState<EnrichedPlayerListItem[]>([]);
  const [loadingB, setLoadingB] = useState(false);
  const [selectedB, setSelectedB] = useState<EnrichedPlayerListItem | null>(null);

  // Comparison result
  const [comparison, setComparison] = useState<PlayerOverviewComparison | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);

  // Load clubs
  useEffect(() => {
    clubsApi.browse()
      .then((clubs) => setProClubs(clubs.filter((c) => c.club_type === 'system_professional')))
      .catch(() => {})
      .finally(() => setClubsLoading(false));
  }, []);

  // Pre-load player A name from URL param
  useEffect(() => {
    if (!playerAIdFromUrl) return;
    void playerdataApi.getPlayerOverview(playerAIdFromUrl, { season: SEASON, provider: PROVIDER })
      .then((r) => setPreloadedAName(r.data?.player?.display_name || r.data?.player?.full_name || null))
      .catch(() => {});
  }, [playerAIdFromUrl]);

  // Load player list — side A
  useEffect(() => {
    if (!clubA && !searchA.trim()) { setPlayersA([]); return; }
    let active = true;
    setLoadingA(true);
    void playerdataApi.listEnrichedPlayers({
      club_id: clubA?.id,
      search: searchA.trim() || undefined,
      season: SEASON,
      provider: PROVIDER,
      limit: 60,
    }).then((r) => { if (active) setPlayersA(r.data?.results ?? []); })
      .catch(() => { if (active) setPlayersA([]); })
      .finally(() => { if (active) setLoadingA(false); });
    return () => { active = false; };
  }, [clubA, searchA]);

  // Load player list — side B
  useEffect(() => {
    if (!clubB && !searchB.trim()) { setPlayersB([]); return; }
    let active = true;
    setLoadingB(true);
    void playerdataApi.listEnrichedPlayers({
      club_id: clubB?.id,
      search: searchB.trim() || undefined,
      season: SEASON,
      provider: PROVIDER,
      limit: 60,
    }).then((r) => { if (active) setPlayersB(r.data?.results ?? []); })
      .catch(() => { if (active) setPlayersB([]); })
      .finally(() => { if (active) setLoadingB(false); });
    return () => { active = false; };
  }, [clubB, searchB]);

  // Derive canonical IDs
  const idA = selectedA?.player?.id ?? playerAIdFromUrl ?? null;
  const idB = selectedB?.player?.id ?? null;

  // Load comparison when both IDs are set
  useEffect(() => {
    if (!idA || !idB || idA === idB) {
      setComparison(null);
      setComparisonError(null);
      return;
    }

    let active = true;
    setComparisonLoading(true);
    setComparisonError(null);
    void playerdataApi.getPlayerOverviewComparison({
      player_a_id: idA,
      player_b_id: idB,
      season: SEASON,
      provider: PROVIDER,
    }).then((r) => { if (active) setComparison(r.data ?? null); })
      .catch((err) => {
        if (active) {
          setComparison(null);
          setComparisonError(err instanceof Error ? err.message : 'Could not load comparison.');
        }
      })
      .finally(() => { if (active) setComparisonLoading(false); });
    return () => { active = false; };
  }, [idA, idB]);

  const handleSelectClubA = (club: Club) => {
    setClubA(clubA?.id === club.id ? null : club);
    setSelectedA(null);
    setSearchA('');
  };

  const handleSelectClubB = (club: Club) => {
    setClubB(clubB?.id === club.id ? null : club);
    setSelectedB(null);
    setSearchB('');
  };

  const nameA =
    selectedA?.player?.display_name ||
    selectedA?.player?.full_name ||
    preloadedAName ||
    (playerAIdFromUrl ? `Player ${playerAIdFromUrl}` : null);

  const nameB =
    selectedB?.player?.display_name ||
    selectedB?.player?.full_name ||
    null;

  const comparisonNameA =
    comparison?.player_a?.player?.display_name ||
    comparison?.player_a?.player?.full_name ||
    nameA ||
    'Player A';

  const comparisonNameB =
    comparison?.player_b?.player?.display_name ||
    comparison?.player_b?.player?.full_name ||
    nameB ||
    'Player B';

  const metricGroups = useMemo(
    () => (comparison?.metric_groups ?? []).filter(
      (g) => (g.metrics ?? []).some((m) => m.is_comparable !== false)
    ),
    [comparison]
  );

  return (
    <div className={styles.container}>
      {/* Hero */}
      <section className={styles.hero}>
        <div>
          <h1 className={styles.title}>Player Comparison</h1>
          <p className={styles.subtitle}>
            Select two players to compare their 2024/25 season stats side by side.
          </p>
        </div>
      </section>

      {/* Player pickers */}
      <div className={styles.pickersRow}>
        <PlayerPicker
          label="Player A"
          proClubs={proClubs}
          clubsLoading={clubsLoading}
          selectedClub={clubA}
          onSelectClub={handleSelectClubA}
          searchQuery={searchA}
          onSearchChange={setSearchA}
          players={playersA}
          playersLoading={loadingA}
          selectedPlayer={selectedA}
          onSelectPlayer={setSelectedA}
          onClear={() => { setSelectedA(null); setClubA(null); setSearchA(''); }}
        />

        <div className={styles.vsBar}>
          {nameA && nameB ? (
            <>
              <div className={styles.vsName}>{nameA}</div>
              <div className={styles.vsDivider}>vs</div>
              <div className={styles.vsName}>{nameB}</div>
            </>
          ) : (
            <div className={styles.vsDivider}>vs</div>
          )}
        </div>

        <PlayerPicker
          label="Player B"
          proClubs={proClubs}
          clubsLoading={clubsLoading}
          selectedClub={clubB}
          onSelectClub={handleSelectClubB}
          searchQuery={searchB}
          onSearchChange={setSearchB}
          players={playersB}
          playersLoading={loadingB}
          selectedPlayer={selectedB}
          onSelectPlayer={setSelectedB}
          onClear={() => { setSelectedB(null); setClubB(null); setSearchB(''); }}
        />
      </div>

      {/* Comparison results */}
      {comparisonLoading && (
        <div className={styles.loading}>Loading comparison…</div>
      )}

      {comparisonError && (
        <div className={styles.error}>{comparisonError}</div>
      )}

      {comparison && !comparisonLoading && (
        <>
          {/* Header names */}
          <div className={styles.comparisonHeader}>
            <div className={styles.comparisonPlayerName}>{comparisonNameA}</div>
            <div className={styles.comparisonVs}>vs</div>
            <div className={styles.comparisonPlayerName}>{comparisonNameB}</div>
          </div>

          {!comparison.has_comparison_data && comparison.missing_reasons?.length ? (
            <div className={styles.notice}>
              {comparison.missing_reasons.join(' ')}
            </div>
          ) : null}

          {metricGroups.map((group) => (
            <ComparisonMetricGroup
              key={group.key}
              group={group}
            />
          ))}

          {metricGroups.length === 0 && comparison.has_comparison_data && (
            <div className={styles.empty}>
              Stats are available but no comparable metrics were found.
            </div>
          )}
        </>
      )}

      {!idA && !idB && (
        <div className={styles.empty}>
          Select two players above to start the comparison.
        </div>
      )}

      {idA && !idB && (
        <div className={styles.empty}>
          {nameA ? `${nameA} selected — now pick Player B.` : 'Player A ready — now pick Player B.'}
        </div>
      )}
    </div>
  );
};

export default InternalPlayerComparisonPage;
