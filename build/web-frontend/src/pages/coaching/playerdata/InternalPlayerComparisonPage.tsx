import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Sidebar } from "../../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../../components/Social/SocialUserButtons";
import { clubsApi } from "../../../services/api";
import { playerdataApi } from "../../../services/api/playerdataApi";
import type { Club } from "../../../types/club";
import type {
  EnrichedPlayerListItem,
  PlayerOverviewComparison,
  PlayerOverviewComparisonMetricGroup,
} from "../../../types/playerdata";
import styles from "./css/InternalPlayerComparisonPage.module.css";

const SEASON = '2025';
const PROVIDER = "understat";

const ALLOWED_COMPARE_CLUBS = new Set([
  "manchester united",
  "real madrid cf",
  "paris saint-germain fc",
  "fc bayern munchen",
  "juventus fc",
]);

const normaliseClubName = (name: string): string =>
  name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

const ComparisonMetricGroup: React.FC<{
  group: PlayerOverviewComparisonMetricGroup;
}> = ({ group }) => {
  const visible = (group.metrics ?? []).filter(
    (m) => m.is_comparable !== false,
  );
  if (visible.length === 0) return null;

  return (
    <div className={styles["icp-panel"]} style={{ marginBottom: "1rem" }}>
      <h3 className={styles["icp-metric-group-title"]}>{group.label}</h3>
      <div className={styles["icp-metric-table"]}>
        {visible.map((metric) => {
          const valA =
            metric.player_a_formatted ??
            (metric.player_a_value != null
              ? String(metric.player_a_value)
              : "—");
          const valB =
            metric.player_b_formatted ??
            (metric.player_b_value != null
              ? String(metric.player_b_value)
              : "—");
          const winA = metric.winner === "player_a";
          const winB = metric.winner === "player_b";
          return (
            <div key={metric.key} className={styles["icp-metric-row"]}>
              <div
                className={`${styles["icp-metric-val"]} ${styles["icp-metric-val--left"]} ${winA ? styles["icp-metric-val--winner"] : ""}`}
              >
                {valA}
              </div>
              <div className={styles["icp-metric-label"]}>{metric.label}</div>
              <div
                className={`${styles["icp-metric-val"]} ${styles["icp-metric-val--right"]} ${winB ? styles["icp-metric-val--winner"] : ""}`}
              >
                {valB}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

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
  <div className={styles["icp-picker-col"]}>
    <div className={styles["icp-picker-header"]}>
      <span className={styles["icp-picker-label"]}>{label}</span>
      {selectedPlayer && (
        <button
          type="button"
          className={styles["icp-clear-btn"]}
          onClick={onClear}
        >
          Clear
        </button>
      )}
    </div>

    {selectedPlayer ? (
      <div className={styles["icp-selected-player"]}>
        <div className={styles["icp-selected-player-name"]}>
          {selectedPlayer.player.display_name ||
            selectedPlayer.player.full_name}
        </div>
        <div className={styles["icp-selected-player-meta"]}>
          {[selectedPlayer.player.position, selectedPlayer.club?.name]
            .filter(Boolean)
            .join(" · ")}
        </div>
      </div>
    ) : (
      <>
        {clubsLoading ? (
          <div className={styles["icp-hint"]}>Loading clubs…</div>
        ) : (
          <div className={styles["icp-mini-club-grid"]}>
            {proClubs.map((club) => (
              <button
                key={club.id}
                type="button"
                className={`${styles["icp-mini-club-card"]} ${selectedClub?.id === club.id ? styles["icp-mini-club-card--active"] : ""}`}
                onClick={() => onSelectClub(club)}
              >
                {club.name}
              </button>
            ))}
          </div>
        )}

        <input
          className={styles["icp-search-input"]}
          type="text"
          placeholder={
            selectedClub ? `Search in ${selectedClub.name}…` : "Search by name…"
          }
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />

        {playersLoading ? (
          <div className={styles["icp-hint"]}>Loading…</div>
        ) : players.length > 0 ? (
          <div className={styles["icp-player-list"]}>
            {players.map((item) => {
              const name =
                item.player.display_name ||
                item.player.full_name ||
                `Player ${item.player.id}`;
              const meta = [item.player.position, item.player.nationality]
                .filter(Boolean)
                .join(" · ");
              return (
                <button
                  key={item.player.id}
                  type="button"
                  className={styles["icp-player-row"]}
                  onClick={() => onSelectPlayer(item)}
                >
                  <div className={styles["icp-player-name"]}>{name}</div>
                  {meta && (
                    <div className={styles["icp-player-meta"]}>{meta}</div>
                  )}
                </button>
              );
            })}
          </div>
        ) : selectedClub || searchQuery.trim() ? (
          <div className={styles["icp-hint"]}>No players found.</div>
        ) : (
          <div className={styles["icp-hint"]}>
            Select a club or search by name.
          </div>
        )}
      </>
    )}
  </div>
);

const InternalPlayerComparisonPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  const playerAIdFromUrl = useMemo(() => {
    const v = searchParams.get("player_a_id");
    const n = v ? Number(v) : NaN;
    return Number.isInteger(n) && n > 0 ? n : null;
  }, [searchParams]);

  const [proClubs, setProClubs] = useState<Club[]>([]);
  const [clubsLoading, setClubsLoading] = useState(true);

  const [clubA, setClubA] = useState<Club | null>(null);
  const [searchA, setSearchA] = useState("");
  const [playersA, setPlayersA] = useState<EnrichedPlayerListItem[]>([]);
  const [loadingA, setLoadingA] = useState(false);
  const [selectedA, setSelectedA] = useState<EnrichedPlayerListItem | null>(
    null,
  );
  const [preloadedAName, setPreloadedAName] = useState<string | null>(null);

  const [clubB, setClubB] = useState<Club | null>(null);
  const [searchB, setSearchB] = useState("");
  const [playersB, setPlayersB] = useState<EnrichedPlayerListItem[]>([]);
  const [loadingB, setLoadingB] = useState(false);
  const [selectedB, setSelectedB] = useState<EnrichedPlayerListItem | null>(
    null,
  );

  const [comparison, setComparison] = useState<PlayerOverviewComparison | null>(
    null,
  );
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);

  useEffect(() => {
    clubsApi
      .browse()
      .then((clubs) =>
        setProClubs(
          clubs.filter(
            (c) =>
              c.club_type === "system_professional" &&
              ALLOWED_COMPARE_CLUBS.has(normaliseClubName(c.name)),
          ),
        ),
      )
      .catch(() => {})
      .finally(() => setClubsLoading(false));
  }, []);

  useEffect(() => {
    if (!playerAIdFromUrl) return;
    void playerdataApi.getPlayerOverview(playerAIdFromUrl, { season: SEASON, provider: PROVIDER })
      .then((r) => setPreloadedAName(r.data?.player?.display_name || r.data?.player?.full_name || null))
      .catch(() => {});
  }, [playerAIdFromUrl]);

  useEffect(() => {
    if (!clubA && !searchA.trim()) {
      setPlayersA([]);
      return;
    }
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

  useEffect(() => {
    if (!clubB && !searchB.trim()) {
      setPlayersB([]);
      return;
    }
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

  const idA = selectedA?.player?.id ?? playerAIdFromUrl ?? null;
  const idB = selectedB?.player?.id ?? null;

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
          setComparisonError(
            err instanceof Error ? err.message : "Could not load comparison.",
          );
        }
      })
      .finally(() => {
        if (active) setComparisonLoading(false);
      });
    return () => {
      active = false;
    };
  }, [idA, idB]);

  const handleSelectClubA = (club: Club) => {
    setClubA(clubA?.id === club.id ? null : club);
    setSelectedA(null);
    setSearchA("");
  };

  const handleSelectClubB = (club: Club) => {
    setClubB(clubB?.id === club.id ? null : club);
    setSelectedB(null);
    setSearchB("");
  };

  const nameA =
    selectedA?.player?.display_name ||
    selectedA?.player?.full_name ||
    preloadedAName ||
    (playerAIdFromUrl ? `Player ${playerAIdFromUrl}` : null);

  const nameB =
    selectedB?.player?.display_name || selectedB?.player?.full_name || null;

  const comparisonNameA =
    comparison?.player_a?.player?.display_name ||
    comparison?.player_a?.player?.full_name ||
    nameA ||
    "Player A";

  const comparisonNameB =
    comparison?.player_b?.player?.display_name ||
    comparison?.player_b?.player?.full_name ||
    nameB ||
    "Player B";

  const metricGroups = useMemo(
    () =>
      (comparison?.metric_groups ?? []).filter((g) =>
        (g.metrics ?? []).some((m) => m.is_comparable !== false),
      ),
    [comparison],
  );

  return (
    <div className={styles["icp-root"]}>
      <div className={styles["icp-sidebar-section"]}>
        <Sidebar />
      </div>

      <div className={styles["icp-main"]}>
        <header className={styles["icp-header"]}>
          <div className={styles["icp-header-left"]}>Player Comparison</div>
          <div className={styles["icp-header-mid"]} />
          <div className={styles["icp-header-right"]}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles["icp-content"]}>
          <section className={styles["icp-hero"]}>
            <h1 className={styles["icp-title"]}>Player Comparison</h1>
            <p className={styles["icp-subtitle"]}>
              Select two players to compare their {SEASON}/{String(Number(SEASON) + 1).slice(2)} season stats side by
              side.
            </p>
          </section>

          <div className={styles["icp-pickers-row"]}>
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
              onClear={() => {
                setSelectedA(null);
                setClubA(null);
                setSearchA("");
              }}
            />

            <div className={styles["icp-vs-bar"]}>
              {nameA && nameB ? (
                <>
                  <div className={styles["icp-vs-name"]}>{nameA}</div>
                  <div className={styles["icp-vs-divider"]}>vs</div>
                  <div className={styles["icp-vs-name"]}>{nameB}</div>
                </>
              ) : (
                <div className={styles["icp-vs-divider"]}>vs</div>
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
              onClear={() => {
                setSelectedB(null);
                setClubB(null);
                setSearchB("");
              }}
            />
          </div>

          {comparisonLoading && (
            <div className={styles["icp-loading"]}>Loading comparison…</div>
          )}

          {comparisonError && (
            <div className={styles["icp-error"]}>{comparisonError}</div>
          )}

          {comparison && !comparisonLoading && (
            <>
              <div className={styles["icp-comparison-header"]}>
                <div className={styles["icp-comparison-player-name"]}>
                  {comparisonNameA}
                </div>
                <div className={styles["icp-comparison-vs"]}>vs</div>
                <div className={styles["icp-comparison-player-name"]}>
                  {comparisonNameB}
                </div>
              </div>

              {!comparison.has_comparison_data &&
              comparison.missing_reasons?.length ? (
                <div className={styles["icp-notice"]}>
                  {comparison.missing_reasons.join(" ")}
                </div>
              ) : null}

              {metricGroups.map((group) => (
                <ComparisonMetricGroup key={group.key} group={group} />
              ))}

              {metricGroups.length === 0 && comparison.has_comparison_data && (
                <div className={styles["icp-empty"]}>
                  Stats are available but no comparable metrics were found.
                </div>
              )}
            </>
          )}

          {!idA && !idB && (
            <div className={styles["icp-empty"]}>
              Select two players above to start the comparison.
            </div>
          )}

          {idA && !idB && (
            <div className={styles["icp-empty"]}>
              {nameA
                ? `${nameA} selected — now pick Player B.`
                : "Player A ready — now pick Player B."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InternalPlayerComparisonPage;
