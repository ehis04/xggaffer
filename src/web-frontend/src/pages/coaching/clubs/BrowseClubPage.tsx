import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { clubsApi } from "../../../services/api";
import type { Club, ClubJoinRequest } from "../../../types/club";
import styles from "./css/BrowseClubsPage.module.css";
import { Sidebar } from "../../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../../components/Social/SocialUserButtons";
import {
  isFeaturedFanClub,
  sortFeaturedFanClubs,
} from "../../../utils/featuredClubs";

const getRequestStatusLabel = (status: ClubJoinRequest["status"]) => {
  const map: Record<string, string> = {
    pending: "Pending review",
    approved: "Approved",
    rejected: "Rejected",
    withdrawn: "Withdrawn",
    cancelled: "Cancelled",
  };
  return map[status] ?? status;
};

const FORMAT_FILTERS = ["All", "7v7", "9v9", "11v11", "Futsal"] as const;
const AGE_FILTERS = ["All", "U9", "U12", "U15", "U18", "Adult"] as const;

type FormatFilter = (typeof FORMAT_FILTERS)[number];
type AgeFilter = (typeof AGE_FILTERS)[number];

/* ─── BrowseClubCard ──────────────────────────────────────── */

interface BrowseClubCardProps {
  club: Club;
  onView: (club: Club) => void;
  onRequestToJoin: (club: Club) => void;
  onToggleFollow: (club: Club) => void;
  onCopy: (club: Club) => void;
  isRequesting: boolean;
  isFollowing: boolean;
  isCopying: boolean;
  existingRequest?: ClubJoinRequest;
}

const BrowseClubCard: React.FC<BrowseClubCardProps> = ({
  club,
  onView,
  onRequestToJoin,
  onToggleFollow,
  onCopy,
  isRequesting,
  isFollowing,
  isCopying,
  existingRequest,
}) => {
  const initials = club.name.slice(0, 2).toUpperCase();

  const badgeColors: Record<number, string> = {
    0: "#22c55e",
    1: "#3b82f6",
    2: "#f59e0b",
    3: "#a78bfa",
    4: "#ec4899",
    5: "#06b6d4",
  };
  const colorKey = club.id % 6;
  const badgeColor = badgeColors[colorKey] ?? "#22c55e";

  const tags: string[] = [
    (club as any).format,
    (club as any).age_group ?? (club as any).division,
  ].filter(Boolean) as string[];

  const hasActiveRequest =
    existingRequest &&
    existingRequest.status !== "rejected" &&
    existingRequest.status !== "withdrawn" &&
    existingRequest.status !== "cancelled";

  return (
    <div className={styles.clubCard}>
      <div className={styles.clubCardTop}>
        <div
          className={styles.clubCardBadge}
          style={{
            background: `${badgeColor}22`,
            border: `1.5px solid ${badgeColor}55`,
          }}
        >
          {club.badge ? (
            <img src={club.badge} alt={club.name} className={styles.clubCardBadgeImg} />
          ) : (
            <span style={{ color: badgeColor, fontWeight: 700, fontSize: "0.9rem" }}>
              {initials}
            </span>
          )}
        </div>
        <div className={styles.clubCardInfo}>
          <button
            type="button"
            className={styles.clubCardName}
            onClick={() => onView(club)}
          >
            {club.name}
          </button>
          {club.city && (
            <div className={styles.clubCardLocation}>
              {club.city}{club.country ? `, ${club.country}` : ""}
            </div>
          )}
        </div>
      </div>

      <div className={styles.clubCardTags}>
        {tags.map((t) => (
          <span key={t} className={styles.clubCardTag}>{t}</span>
        ))}
        <span className={styles.clubCardTag}>{club.player_count} players</span>
        <span className={styles.clubCardTag}>{club.fan_count ?? 0} fans</span>
      </div>

      {club.description && (
        <p className={styles.clubCardDesc}>
          {club.description.length > 100
            ? club.description.slice(0, 100) + "…"
            : club.description}
        </p>
      )}

      <div className={styles.clubCardActions}>
        <button
          className={styles.viewBtn}
          onClick={() => onView(club)}
        >
          View
        </button>
        <button
          className={`${styles.fanBtn} ${club.is_followed ? styles.fanBtnActive : ""}`}
          disabled={isFollowing}
          onClick={() => onToggleFollow(club)}
        >
          {isFollowing ? "Saving..." : club.is_followed ? "Following" : "Follow"}
        </button>
        <button
          className={styles.requestBtn}
          disabled={isCopying}
          onClick={() => onCopy(club)}
        >
          {isCopying ? "Copying…" : "Copy Club"}
        </button>
        {hasActiveRequest ? (
          <div className={styles.requestedPill}>
            {getRequestStatusLabel(existingRequest!.status)}
          </div>
        ) : (
          <button
            className={styles.requestBtn}
            disabled={isRequesting || club.join_policy === "invite_only" || club.join_policy === "system_managed"}
            onClick={() => onRequestToJoin(club)}
          >
            {isRequesting
              ? "Submitting…"
              : club.join_policy === "invite_only"
              ? "Invite only"
              : club.join_policy === "system_managed"
              ? "System managed"
              : "Request to join"}
          </button>
        )}
      </div>
    </div>
  );
};

/* ─── page ────────────────────────────────────────────────── */

const BrowseClubsPage: React.FC = () => {
  const navigate = useNavigate();

  const [clubs, setClubs] = useState<Club[]>([]);
  const [myJoinRequests, setMyJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [selectedClub, setSelectedClub] = useState<Club | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestingClubId, setRequestingClubId] = useState<number | null>(null);
  const [followingClubId, setFollowingClubId] = useState<number | null>(null);
  const [copyingClubId, setCopyingClubId] = useState<number | null>(null);

  const [searchInput, setSearchInput] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [requestMessage, setRequestMessage] = useState("");
  const [workflowMessage, setWorkflowMessage] = useState<string | null>(null);

  const [formatFilter, setFormatFilter] = useState<FormatFilter>("All");
  const [ageFilter, setAgeFilter] = useState<AgeFilter>("All");
  const [showFilters, setShowFilters] = useState(false);

  const loadData = useCallback(async (search?: string) => {
    try {
      setLoading(true);
      setError(null);
      const [clubsData, requestsData] = await Promise.all([
        clubsApi.browse(search ? { search } : undefined),
        clubsApi.listMyJoinRequests(),
      ]);
      const targetClubs = clubsData.filter(
        (club) => (club as any).is_trashed !== true && isFeaturedFanClub(club)
      );
      const playerLists = await Promise.all(
        targetClubs.map(async (club) => {
          try {
            const players = await clubsApi.listPlayers(club.id);
            return { clubId: club.id, playerCount: players.length };
          } catch {
            return { clubId: club.id, playerCount: club.player_count };
          }
        })
      );

      const countByClubId = new Map(playerLists.map((x) => [x.clubId, x.playerCount]));
      const visibleClubs = sortFeaturedFanClubs(
        targetClubs.map((club) => ({
          ...club,
          player_count: countByClubId.get(club.id) ?? club.player_count,
        }))
      );

      setClubs(visibleClubs);
      setMyJoinRequests(requestsData);
      setSelectedClub((current) => current
        ? visibleClubs.find((club) => club.id === current.id) || null
        : null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load clubs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadData(activeSearch); }, [activeSearch, loadData]);

  const filteredClubs = useMemo(() => {
    return clubs.filter((club) => {
      if (formatFilter !== "All") {
        const fmt = ((club as any).format ?? "").toLowerCase();
        if (fmt !== formatFilter.toLowerCase()) return false;
      }
      if (ageFilter !== "All") {
        const age = ((club as any).age_group ?? (club as any).division ?? "").toLowerCase();
        if (!age.includes(ageFilter.toLowerCase())) return false;
      }
      return true;
    });
  }, [clubs, formatFilter, ageFilter]);

  const visibleCountLabel = useMemo(() => {
    const count = filteredClubs.length;
    if (!activeSearch) return `${count} clubs · sorted by relevance`;
    return `${count} results for "${activeSearch}"`;
  }, [filteredClubs.length, activeSearch]);

  const latestRequestForClub = (clubId: number) =>
    myJoinRequests.find((r) => r.club === clubId);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveSearch(searchInput.trim());
  };

  const handleClearSearch = () => {
    setSearchInput("");
    setActiveSearch("");
  };

  const handleRequestToJoin = async (club: Club) => {
    try {
      setRequestingClubId(club.id);
      setWorkflowMessage(null);
      await clubsApi.requestToJoin(club.id, {
        requested_role: "player",
        message: requestMessage.trim() || undefined,
      });
      setRequestMessage("");
      setWorkflowMessage("Join request submitted successfully.");
      const updated = await clubsApi.listMyJoinRequests();
      setMyJoinRequests(updated);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : "Failed to submit join request.");
    } finally {
      setRequestingClubId(null);
    }
  };

  const replaceClub = (updatedClub: Club) => {
    setClubs((items) =>
      sortFeaturedFanClubs(
        items.map((club) => (club.id === updatedClub.id ? updatedClub : club))
      )
    );
    setSelectedClub((current) =>
      current?.id === updatedClub.id ? updatedClub : current
    );
  };

  const handleToggleFollow = async (club: Club) => {
    try {
      setFollowingClubId(club.id);
      setWorkflowMessage(null);
      const updatedClub = club.is_followed
        ? await clubsApi.unfollow(club.id)
        : await clubsApi.follow(club.id);
      replaceClub(updatedClub);
      setWorkflowMessage(
        updatedClub.is_followed
          ? `You're now following ${updatedClub.name}.`
          : `You're no longer following ${updatedClub.name}.`
      );
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : "Failed to update club follow.");
    } finally {
      setFollowingClubId(null);
    }
  };

  const handleCopyClub = async (club: Club) => {
    try {
      setCopyingClubId(club.id);
      setWorkflowMessage(null);
      const newClub = await clubsApi.duplicate(club.id, { include_players: false, visibility: "private" });
      navigate(`/clubs/${newClub.id}/`);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : "Failed to copy club.");
    } finally {
      setCopyingClubId(null);
    }
  };

  const handleViewClub = (club: Club) => {
    setSelectedClub(club);
    setRequestMessage("");
    setWorkflowMessage(null);
  };

  return (
    <div className={styles.pageShell}>
      <div className="sidebar-section">
        <Sidebar />
      </div>

      <div className={styles.pageMain}>
        <header className={styles.pageHeader}>
          <div className={styles.pageHeaderLeft}>
            <button
              className="ptb-back-btn"
              onClick={() => navigate(-1)}
              aria-label="Go back"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <span className={styles.pageHeaderLabel}>Coaching</span>
            <span className={styles.pageHeaderSep}>·</span>
            <span className={styles.pageHeaderTitle}>Clubs</span>
          </div>
          <div className={styles.pageHeaderMiddle}>
          </div>
          <div className={styles.pageHeaderRight}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles.content}>

          <section className={styles.hero}>
            <div className={styles.heroBreadcrumb}>BROWSE</div>
            <h1 className={styles.heroTitle}>Follow a featured club.</h1>
            <p className={styles.heroSub}>
              Choose from Manchester United, Real Madrid, Bayern Munich, PSG, and
              Juventus. Following a club personalises your home feed.
            </p>
          </section>

          <div className={styles.searchRow}>
            <form className={styles.searchForm} onSubmit={handleSearchSubmit}>
              <div className={styles.searchInputWrap}>
                <svg className={styles.searchIcon} xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                </svg>
                <input
                  className={styles.searchInput}
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search clubs by name, region, or age group…"
                />
                {(searchInput || activeSearch) && (
                  <button type="button" className={styles.searchClear} onClick={handleClearSearch}>✕</button>
                )}
              </div>
            </form>
            <button
              className={`${styles.filtersBtn} ${showFilters ? styles.filtersBtnActive : ""}`}
              onClick={() => setShowFilters((v) => !v)}
            >
              Filters
            </button>
          </div>

          <div className={styles.filterBar}>
            <div className={styles.filterGroup}>
              <span className={styles.filterGroupLabel}>FORMAT</span>
              <div className={styles.filterPills}>
                {FORMAT_FILTERS.map((f) => (
                  <button
                    key={f}
                    className={`${styles.filterPill} ${formatFilter === f ? styles.filterPillActive : ""}`}
                    onClick={() => setFormatFilter(f)}
                  >{f}</button>
                ))}
              </div>
            </div>
            <div className={styles.filterGroup}>
              <span className={styles.filterGroupLabel}>AGE</span>
              <div className={styles.filterPills}>
                {AGE_FILTERS.map((a) => (
                  <button
                    key={a}
                    className={`${styles.filterPill} ${ageFilter === a ? styles.filterPillActive : ""}`}
                    onClick={() => setAgeFilter(a)}
                  >{a}</button>
                ))}
              </div>
            </div>
            <div className={styles.filterCount}>{visibleCountLabel}</div>
          </div>

          {error && <div className={styles.errorBanner}>{error}</div>}
          {workflowMessage && <div className={styles.noticeBanner}>{workflowMessage}</div>}

          {selectedClub && (
            <div className={styles.workflowPanel}>
              <div className={styles.workflowPanelHead}>
                <div>
                  <h2 className={styles.workflowPanelTitle}>{selectedClub.name}</h2>
                  <p className={styles.workflowPanelSub}>Review the membership path for this club before you act.</p>
                </div>
                <div className={styles.workflowActions}>
                  <button
                    className={`${styles.fanBtn} ${selectedClub.is_followed ? styles.fanBtnActive : ""}`}
                    disabled={followingClubId === selectedClub.id}
                    onClick={() => handleToggleFollow(selectedClub)}
                  >
                    {followingClubId === selectedClub.id
                      ? "Saving..."
                      : selectedClub.is_followed
                      ? "Following"
                      : "Follow"}
                  </button>
                  <button className={styles.ghostBtn} onClick={() => setSelectedClub(null)}>
                    Clear selection
                  </button>
                </div>
              </div>
              <div className={styles.workflowGrid}>
                <div className={styles.workflowCard}>
                  <h3 className={styles.workflowCardTitle}>Membership path</h3>
                  {selectedClub.join_policy === "approval_required" && (
                    <>
                      <p className={styles.workflowCardText}>
                        This club accepts player join requests. Approval is still required even when the club is publicly listed.
                      </p>
                      {latestRequestForClub(selectedClub.id) && (
                        <div className={styles.statusBox}>
                          <span className={styles.statusLabel}>Your latest request</span>
                          <span className={styles.statusValue}>
                            {getRequestStatusLabel(latestRequestForClub(selectedClub.id)!.status)}
                          </span>
                        </div>
                      )}
                      {(!latestRequestForClub(selectedClub.id) ||
                        ["rejected", "withdrawn", "cancelled"].includes(
                          latestRequestForClub(selectedClub.id)!.status
                        )) && (
                        <>
                          <textarea
                            className={styles.workflowTextarea}
                            value={requestMessage}
                            onChange={(e) => setRequestMessage(e.target.value)}
                            placeholder="Optional note to the club reviewer"
                            rows={3}
                          />
                          <button
                            className={styles.requestBtn}
                            style={{ marginTop: "0.5rem" }}
                            disabled={requestingClubId === selectedClub.id}
                            onClick={() => handleRequestToJoin(selectedClub)}
                          >
                            {requestingClubId === selectedClub.id ? "Submitting…" : "Request to Join"}
                          </button>
                        </>
                      )}
                    </>
                  )}
                  {selectedClub.join_policy === "invite_only" && (
                    <div className={styles.noticeBlock}>This club is invite only. No self-service request flow is available from browse.</div>
                  )}
                  {selectedClub.join_policy === "system_managed" && (
                    <div className={styles.noticeBlock}>This club is system managed and not claimable through ordinary membership workflows.</div>
                  )}
                </div>
                <div className={styles.workflowCard}>
                  <h3 className={styles.workflowCardTitle}>How this works</h3>
                  <ul className={styles.infoList}>
                    <li>Listed clubs appear in browse and search.</li>
                    <li>Approval-required clubs route you into a real request flow.</li>
                    <li>Invite-only clubs do not show self-join buttons.</li>
                    <li>System-managed clubs stay non-claimable.</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {loading ? (
            <div className={styles.loadingState}>
              <div className={styles.loadingSpinner} />
              <p>Loading clubs…</p>
            </div>
          ) : filteredClubs.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No listed clubs matched your search.</p>
              {activeSearch && (
                <button className={styles.ghostBtn} onClick={handleClearSearch}>Clear search</button>
              )}
            </div>
          ) : (
            <div className={styles.clubGrid}>
              {filteredClubs.map((club) => (
                <BrowseClubCard
                  key={club.id}
                  club={club}
                  onView={handleViewClub}
                  onRequestToJoin={handleRequestToJoin}
                  onToggleFollow={handleToggleFollow}
                  onCopy={handleCopyClub}
                  isRequesting={requestingClubId === club.id}
                  isFollowing={followingClubId === club.id}
                  isCopying={copyingClubId === club.id}
                  existingRequest={latestRequestForClub(club.id)}
                />
              ))}
            </div>
          )}

          {!loading && filteredClubs.length > 0 && (
            <div className={styles.loadMore}>
              <button className={styles.loadMoreBtn} onClick={() => void loadData(activeSearch)}>
                Load more clubs
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default BrowseClubsPage;
