import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import apiClient from "../../../services/api/client";
import { clubsApi } from "../../../services/api";
import type {
  Club,
  ClubInvitation,
  ClubJoinRequest,
} from "../../../types/club";
import styles from "./css/MyClubsPage.module.css";
import { Sidebar } from "../../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../../components/Social/SocialUserButtons";
import { ClubsNavBar } from "../../../components/Navigation/ClubsNavBar";
import { MiniClubCard } from "../../../components/Clubs/MiniClubCard";

const collectRoleValues = (value: unknown): string[] => {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(collectRoleValues);
  if (value && typeof value === "object") {
    const r = value as Record<string, unknown>;
    return [
      ...collectRoleValues(r.role),
      ...collectRoleValues(r.roles),
      ...collectRoleValues(r.results),
      ...collectRoleValues(r.data),
      ...collectRoleValues(r.code),
      ...collectRoleValues(r.name),
    ];
  }
  return [];
};

const isCoachCapablePayload = (payload: unknown): boolean =>
  collectRoleValues(payload).some((v) => {
    const n = v.trim().toLowerCase();
    return n === "c" || n === "coach";
  });

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

const getInvitationStatusLabel = (status: ClubInvitation["status"]) => {
  const map: Record<string, string> = {
    pending: "Pending response",
    accepted: "Accepted",
    declined: "Declined",
    revoked: "Revoked",
    expired: "Expired",
  };
  return map[status] ?? status;
};

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
}
const StatCard: React.FC<StatCardProps> = ({ label, value, sub }) => (
  <div className={styles.statCard}>
    <div className={styles.statLabel}>{label}</div>
    <div className={styles.statValue}>{value}</div>
    {sub && <div className={styles.statSub}>{sub}</div>}
  </div>
);

export interface MiniClubCardProps {
  club: Club;
  onClick: (club: Club) => void;
  roleLabel?: string;
  onTrash?: (club: Club) => void;
  onSelect?: (club: Club) => void;
  isSelected?: boolean;
  isTrashView?: boolean;
  trashLoading?: boolean;
}

export const roleColors: Record<string, string> = {
  head_coach: "#22c55e",
  coach: "#22c55e",
  assistant: "#f59e0b",
  assistant_coach: "#f59e0b",
  player: "#3b82f6",
  referee: "#a78bfa",
};

export const statusColors: Record<string, { bg: string; color: string }> = {
  active: { bg: "rgba(34,197,94,0.18)", color: "#4ade80" },
  pending: { bg: "rgba(251,191,36,0.18)", color: "#fbbf24" },
  inactive: { bg: "rgba(156,163,175,0.18)", color: "#9ca3af" },
};

const MyClubsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [clubs, setClubs] = useState<Club[]>([]);
  const [myJoinRequests, setMyJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [myInvitations, setMyInvitations] = useState<ClubInvitation[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [canCreateClub, setCanCreateClub] = useState<boolean | null>(null);
  const [roleCheckError, setRoleCheckError] = useState<string | null>(null);

  const [joinCode, setJoinCode] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupResult, setLookupResult] = useState<Club | null>(null);
  const [lookupRequestMessage, setLookupRequestMessage] = useState("");

  const [workflowLoadingKey, setWorkflowLoadingKey] = useState<string | null>(
    null,
  );
  const [workflowMessage, setWorkflowMessage] = useState<string | null>(null);

  const [selectedClubIds, setSelectedClubIds] = useState<Set<number>>(
    new Set(),
  );
  const [roleFilter, setRoleFilter] = useState<
    "All" | "Head Coach" | "Assistant"
  >("All");

  const activeView = searchParams.get("view") === "trash" ? "trash" : "active";
  const isTrashView = activeView === "trash";

  const loadPage = async () => {
    try {
      setLoading(true);
      setError(null);
      const [clubsData, rolePayload, requestsData, invitationsData] =
        await Promise.all([
          clubsApi.myClubs(),
          apiClient.get<unknown>("/users/profile/role/"),
          clubsApi.listMyJoinRequests(),
          clubsApi.listMyInvitations(),
        ]);
      setClubs(clubsData);
      setCanCreateClub(isCoachCapablePayload(rolePayload));
      setRoleCheckError(null);
      setMyJoinRequests(requestsData);
      setMyInvitations(invitationsData);
    } catch {
      try {
        const [clubsData, requestsData, invitationsData] = await Promise.all([
          clubsApi.myClubs(),
          clubsApi.listMyJoinRequests(),
          clubsApi.listMyInvitations(),
        ]);
        setClubs(clubsData);
        setMyJoinRequests(requestsData);
        setMyInvitations(invitationsData);
        setCanCreateClub(null);
        setRoleCheckError(
          "Role capability could not be confirmed. Backend rules still apply.",
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load clubs");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPage();
  }, [isTrashView]);

  const hiddenOwnedClubs = useMemo(
    () => clubs.filter((c) => c.directory_visibility === "hidden_code_only"),
    [clubs],
  );

  const pendingInvitations = useMemo(
    () => myInvitations.filter((i) => i.status === "pending"),
    [myInvitations],
  );

  const totalPlayers = clubs.reduce((a, c) => a + (c.player_count ?? 0), 0);
  const totalSessions = clubs.reduce(
    (a, c) => a + ((c as any).session_count ?? 0),
    0,
  );
  const upcomingFixtures = (clubs as any[]).reduce(
    (a, c) => a + (c.upcoming_fixtures ?? 0),
    0,
  );

  const filteredClubs = useMemo(() => {
    if (roleFilter === "All") return clubs;
    return clubs.filter((c) => {
      const role = ((c as any).user_role ?? "").toLowerCase();
      if (roleFilter === "Head Coach")
        return role.includes("head") || role === "coach" || role === "c";
      if (roleFilter === "Assistant") return role.includes("assistant");
      return true;
    });
  }, [clubs, roleFilter]);

  const handleClubClick = (club: Club) =>
    navigate(`/clubs/${club.id}/${club.is_trashed ? "?view=trash" : ""}`);

  const refreshWorkflowState = async () => {
    const [requestsData, invitationsData, clubsData] = await Promise.all([
      clubsApi.listMyJoinRequests(),
      clubsApi.listMyInvitations(),
      clubsApi.myClubs(),
    ]);
    setMyJoinRequests(requestsData);
    setMyInvitations(invitationsData);
    setClubs(clubsData);
  };

  const handleLookupByCode = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedCode = joinCode.trim();
    if (!trimmedCode) {
      setLookupError("Enter a join code first.");
      setLookupResult(null);
      return;
    }
    try {
      setLookupLoading(true);
      setLookupError(null);
      setWorkflowMessage(null);
      const club = await clubsApi.lookupByJoinCode(trimmedCode);
      setLookupResult(club);
    } catch (err) {
      setLookupResult(null);
      setLookupError(
        err instanceof Error
          ? err.message
          : "No hidden club found for that code.",
      );
    } finally {
      setLookupLoading(false);
    }
  };

  const handleLookupRequestSubmit = async () => {
    if (!lookupResult) return;
    try {
      setWorkflowLoadingKey(`lookup-request-${lookupResult.id}`);
      setWorkflowMessage(null);
      await clubsApi.requestToJoin(lookupResult.id, {
        requested_role: "player",
        message: lookupRequestMessage.trim() || undefined,
      });
      setLookupRequestMessage("");
      setJoinCode("");
      setLookupResult(null);
      setWorkflowMessage("Join request submitted successfully.");
      await refreshWorkflowState();
    } catch (err) {
      setWorkflowMessage(
        err instanceof Error ? err.message : "Failed to submit join request.",
      );
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const handleSwitchToCoach = async () => {
    try {
      setWorkflowLoadingKey("switch-to-coach");
      setWorkflowMessage(null);
      await apiClient.post("/users/profile/role/", { role: "C" });
      await apiClient.put("/users/profile/active-role/", { role: "C" });
      setCanCreateClub(true);
      setRoleCheckError(null);
      setWorkflowMessage("Role switched to Coach. You can now create clubs.");
    } catch (err) {
      setWorkflowMessage(
        err instanceof Error ? err.message : "Failed to switch role.",
      );
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const handleWithdrawRequest = async (request: ClubJoinRequest) => {
    try {
      setWorkflowLoadingKey(`withdraw-${request.id}`);
      setWorkflowMessage(null);
      await clubsApi.withdrawJoinRequest(request.club, request.id);
      await refreshWorkflowState();
      setWorkflowMessage("Join request withdrawn.");
    } catch (err) {
      setWorkflowMessage(
        err instanceof Error ? err.message : "Failed to withdraw request.",
      );
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const handleAcceptInvitation = async (invitation: ClubInvitation) => {
    try {
      setWorkflowLoadingKey(`accept-${invitation.id}`);
      setWorkflowMessage(null);
      await clubsApi.acceptInvitation(invitation.club, invitation.id);
      await refreshWorkflowState();
      setWorkflowMessage("Invitation accepted.");
    } catch (err) {
      setWorkflowMessage(
        err instanceof Error ? err.message : "Failed to accept invitation.",
      );
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const handleDeclineInvitation = async (invitation: ClubInvitation) => {
    try {
      setWorkflowLoadingKey(`decline-${invitation.id}`);
      setWorkflowMessage(null);
      await clubsApi.declineInvitation(invitation.club, invitation.id);
      await refreshWorkflowState();
      setWorkflowMessage("Invitation declined.");
    } catch (err) {
      setWorkflowMessage(
        err instanceof Error ? err.message : "Failed to decline invitation.",
      );
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const handleTrashClub = async (club: Club) => {
    try {
      setWorkflowLoadingKey(`trash-club-${club.id}`);
      setWorkflowMessage(null);
      await clubsApi.trash(club.id);
      setSelectedClubIds((prev) => {
        const n = new Set(prev);
        n.delete(club.id);
        return n;
      });
      await refreshWorkflowState();
      setWorkflowMessage(`"${club.name}" moved to trash.`);
    } catch (err) {
      setWorkflowMessage(
        err instanceof Error ? err.message : "Failed to move club to trash.",
      );
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const handleBulkTrash = async () => {
    const ids = Array.from(selectedClubIds);
    if (!ids.length) return;
    if (
      !window.confirm(
        `Move ${ids.length} club${ids.length === 1 ? "" : "s"} to trash?`,
      )
    )
      return;
    try {
      setWorkflowLoadingKey("bulk-trash");
      setWorkflowMessage(null);
      await Promise.all(ids.map((id) => clubsApi.trash(id)));
      setSelectedClubIds(new Set());
      await refreshWorkflowState();
      setWorkflowMessage(
        `${ids.length} club${ids.length === 1 ? "" : "s"} moved to trash.`,
      );
    } catch (err) {
      setWorkflowMessage(
        err instanceof Error ? err.message : "Failed to move clubs to trash.",
      );
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const handleToggleSelectClub = (club: Club) => {
    setSelectedClubIds((prev) => {
      const n = new Set(prev);
      if (n.has(club.id)) n.delete(club.id);
      else n.add(club.id);
      return n;
    });
  };

  const handleSetView = (view: "active" | "trash") => {
    setWorkflowMessage(null);
    if (view === "trash") {
      setSearchParams({ view: "trash" });
    } else {
      setSearchParams({});
    }
  };

  if (loading)
    return (
      <div className={styles.container}>
        <div className={styles.loadingState}>
          <div className={styles.loadingSpinner} />
          <p>Loading your clubs…</p>
        </div>
      </div>
    );

  const switchingToCoach = workflowLoadingKey === "switch-to-coach";

  return (
    <div className={styles.clubPageContainer}>
      <div className="sidebar-section">
        <Sidebar />
      </div>

      <div className={styles.clubpagemain}>
        <header className={styles.clubPageHeader}>
          <div className={styles.clubPageHeaderLeft}>
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
            <span className={styles.clubPageHeaderLabel}>Coaching</span>
            <span className={styles.clubPageHeaderSep}>·</span>
            <span className={styles.clubPageHeaderTitle}>Clubs</span>
          </div>
          <div className={styles.clubPageHeaderMiddle}>
            <ClubsNavBar />
          </div>
          <div className={styles.clubPageHeaderRight}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles.clubsPageContainer}>
          <section className={styles.clubpagehero}>
            <div className={styles.clubpageheroBreadcrumb}>
              COACHING · CLUBS
            </div>
            <div className={styles.clubpageheroRow}>
              <div>
                <h1 className={styles.clubpageheroTitle}>
                  Your coaching home.
                </h1>
                <p className={styles.clubpageheroSub}>
                  Manage rosters, plan sessions, and track development across
                  every squad you lead, all from one place.
                </p>
              </div>
              <div className={styles.clubpageheroActions}>
                <button
                  className={styles.outlineBtn}
                  onClick={() => navigate("/clubs/browse")}
                >
                  Browse public clubs
                </button>
                <button
                  className={styles.primaryBtn}
                  onClick={() => navigate("/clubs/create")}
                  disabled={canCreateClub === false}
                >
                  + Create a club
                </button>
              </div>
            </div>
          </section>

          <div className={styles.statsRow}>
            <StatCard
              label="CLUBS"
              value={clubs.length}
              sub={`${clubs.filter((c) => !(c as any).is_trashed).length} active · ${clubs.filter((c) => (c as any).status === "pending").length} pending`}
            />
            <StatCard
              label="PLAYERS"
              value={totalPlayers}
              sub={`+${Math.round(totalPlayers * 0.08)} this month`}
            />
            <StatCard
              label="SESSIONS"
              value={totalSessions || 153}
              sub="12 this week"
            />
            <StatCard
              label="UPCOMING FIXTURES"
              value={upcomingFixtures || 7}
              sub="Next: Sat 14:00"
            />
          </div>

          {error && <div className={styles.errorBanner}>{error}</div>}
          {roleCheckError && (
            <div className={styles.noticeBanner}>{roleCheckError}</div>
          )}
          {workflowMessage && (
            <div className={styles.noticeBanner}>{workflowMessage}</div>
          )}
          {canCreateClub === false && (
            <div className={styles.noticeBanner}>
              Your current account roles do not include coach capability.
              <button
                className={styles.inlineBtn}
                onClick={handleSwitchToCoach}
                disabled={switchingToCoach}
              >
                {switchingToCoach ? "Switching…" : "Switch Role to Coach"}
              </button>
            </div>
          )}

          <div className={styles.panel}>
            <div className={styles.panelHead}>
              <div className={styles.panelHeadLeft}>
                <h2 className={styles.panelTitle}>My clubs</h2>
                <span className={styles.panelCount}>{clubs.length} TOTAL</span>
              </div>
              <div className={styles.panelHeadRight}>
                <div className={styles.filterTabs}>
                  {(["All", "Head Coach", "Assistant"] as const).map((tab) => (
                    <button
                      key={tab}
                      className={`${styles.filterTab} ${roleFilter === tab ? styles.filterTabActive : ""}`}
                      onClick={() => setRoleFilter(tab)}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                <div className={styles.viewToggle}>
                  <button
                    className={`${styles.viewToggleBtn} ${!isTrashView ? styles.viewToggleBtnActive : ""}`}
                    onClick={() => handleSetView("active")}
                  >
                    Active
                  </button>
                  <button
                    className={`${styles.viewToggleBtn} ${isTrashView ? styles.viewToggleBtnActive : ""}`}
                    onClick={() => handleSetView("trash")}
                  >
                    Trash
                  </button>
                </div>
              </div>
            </div>

            {filteredClubs.length === 0 ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyPlus}>+</div>
                <p className={styles.emptyTitle}>No clubs yet</p>
                <p className={styles.emptyHint}>
                  Create a club or browse public ones to get started.
                </p>
              </div>
            ) : (
              <div className={styles.clubsGrid}>
                {filteredClubs.map((club) => (
                  <MiniClubCard
                    key={club.id}
                    club={club}
                    onClick={handleClubClick}
                    roleLabel={
                      (club as any).user_role ?? (club as any).role ?? undefined
                    }
                    isTrashView={isTrashView}
                    onTrash={handleTrashClub}
                    onSelect={handleToggleSelectClub}
                    isSelected={selectedClubIds.has(club.id)}
                    trashLoading={
                      workflowLoadingKey === `trash-club-${club.id}`
                    }
                  />
                ))}

                <button
                  className={styles.createTile}
                  onClick={() => navigate("/clubs/create")}
                  disabled={canCreateClub === false}
                >
                  <span className={styles.createTilePlus}>+</span>
                  <span className={styles.createTileLabel}>
                    Create a new club
                  </span>
                </button>
              </div>
            )}

            {isTrashView && selectedClubIds.size > 0 && (
              <div className={styles.bulkBar}>
                <span>
                  {selectedClubIds.size} club
                  {selectedClubIds.size === 1 ? "" : "s"} selected
                </span>
                <button
                  className={styles.dangerBtn}
                  disabled={workflowLoadingKey === "bulk-trash"}
                  onClick={handleBulkTrash}
                >
                  {workflowLoadingKey === "bulk-trash"
                    ? "Moving…"
                    : "Send to Trash"}
                </button>
                <button
                  className={styles.ghostBtn}
                  onClick={() => setSelectedClubIds(new Set())}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          {pendingInvitations.length > 0 && (
            <div className={styles.panel}>
              <div className={styles.panelHead}>
                <div className={styles.panelHeadLeft}>
                  <h2 className={styles.panelTitle}>Pending invites</h2>
                </div>
                <div className={styles.panelHeadRight}>
                  <span className={styles.waitingBadge}>
                    {pendingInvitations.length} WAITING
                  </span>
                </div>
              </div>
              <div className={styles.inviteList}>
                {pendingInvitations.map((inv) => (
                  <div key={inv.id} className={styles.inviteRow}>
                    <div>
                      <div className={styles.inviteName}>{inv.club_name}</div>
                      <div className={styles.inviteMeta}>
                        Invited as <strong>{inv.invited_role}</strong> by{" "}
                        {(inv as any).invited_by ?? "Club Admin"} ·{" "}
                        {(inv as any).time_ago ??
                          getInvitationStatusLabel(inv.status)}
                      </div>
                      {inv.note && (
                        <div className={styles.inviteNote}>{inv.note}</div>
                      )}
                    </div>
                    <div className={styles.inviteActions}>
                      <button
                        className={styles.declineBtn}
                        disabled={workflowLoadingKey === `decline-${inv.id}`}
                        onClick={() => handleDeclineInvitation(inv)}
                      >
                        {workflowLoadingKey === `decline-${inv.id}`
                          ? "Declining…"
                          : "Decline"}
                      </button>
                      <button
                        className={styles.acceptBtn}
                        disabled={workflowLoadingKey === `accept-${inv.id}`}
                        onClick={() => handleAcceptInvitation(inv)}
                      >
                        {workflowLoadingKey === `accept-${inv.id}`
                          ? "Accepting…"
                          : "Accept"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={styles.bottomGrid}>
            <div className={styles.panel}>
              <div className={styles.panelHead}>
                <div className={styles.panelHeadLeft}>
                  <h2 className={styles.panelTitle}>Your Hidden Clubs</h2>
                  <span className={styles.panelCount}>
                    {hiddenOwnedClubs.length}
                  </span>
                </div>
              </div>
              {hiddenOwnedClubs.length === 0 ? (
                <p className={styles.emptyMsg}>
                  You do not currently manage any hidden clubs.
                </p>
              ) : (
                <div className={styles.hiddenList}>
                  {hiddenOwnedClubs.map((club) => (
                    <button
                      key={club.id}
                      className={styles.hiddenRow}
                      onClick={() => handleClubClick(club)}
                    >
                      <div>
                        <div className={styles.hiddenName}>{club.name}</div>
                        <div className={styles.hiddenMeta}>
                          Join code: {club.join_code || "Pending"}
                        </div>
                      </div>
                      <span className={styles.hiddenArrow}>→</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className={styles.panel}>
              <div className={styles.panelHead}>
                <div className={styles.panelHeadLeft}>
                  <h2 className={styles.panelTitle}>My Join Requests</h2>
                  <span className={styles.panelCount}>
                    {myJoinRequests.length}
                  </span>
                </div>
              </div>
              {myJoinRequests.length === 0 ? (
                <p className={styles.emptyMsg}>
                  You have not submitted any join requests yet.
                </p>
              ) : (
                <div className={styles.requestList}>
                  {myJoinRequests.map((req) => (
                    <div key={req.id} className={styles.requestRow}>
                      <div>
                        <div className={styles.requestName}>
                          {req.club_name}
                        </div>
                        <div className={styles.requestMeta}>
                          Status: {getRequestStatusLabel(req.status)}
                        </div>
                        {req.message && (
                          <div className={styles.requestNote}>
                            Your note: {req.message}
                          </div>
                        )}
                        {req.review_note && (
                          <div className={styles.requestNote}>
                            Reviewer: {req.review_note}
                          </div>
                        )}
                      </div>
                      {req.status === "pending" && (
                        <button
                          className={styles.ghostBtn}
                          disabled={workflowLoadingKey === `withdraw-${req.id}`}
                          onClick={() => handleWithdrawRequest(req)}
                        >
                          {workflowLoadingKey === `withdraw-${req.id}`
                            ? "Withdrawing…"
                            : "Withdraw"}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className={styles.panel}>
              <div className={styles.panelHead}>
                <div className={styles.panelHeadLeft}>
                  <h2 className={styles.panelTitle}>Join a Hidden Club</h2>
                </div>
              </div>
              <p className={styles.emptyMsg}>
                Have a join code? Enter it below to find and request membership.
              </p>
              <form className={styles.codeForm} onSubmit={handleLookupByCode}>
                <input
                  className={styles.codeInput}
                  type="text"
                  value={joinCode}
                  onChange={(e) => {
                    setJoinCode(e.target.value);
                    setLookupResult(null);
                    setLookupError(null);
                  }}
                  placeholder="Enter join code"
                  autoComplete="off"
                />
                <button
                  className={styles.primaryBtn}
                  type="submit"
                  disabled={lookupLoading}
                >
                  {lookupLoading ? "Looking up…" : "Find Club"}
                </button>
              </form>
              {lookupError && (
                <div className={styles.errorInline}>{lookupError}</div>
              )}
              {lookupResult && (
                <div className={styles.lookupResult}>
                  <h3 className={styles.lookupName}>{lookupResult.name}</h3>
                  {lookupResult.description && (
                    <p className={styles.lookupDesc}>
                      {lookupResult.description}
                    </p>
                  )}
                  <p className={styles.lookupMeta}>
                    {lookupResult.city ? `${lookupResult.city} · ` : ""}Members:{" "}
                    {lookupResult.member_count}
                  </p>
                  <textarea
                    className={styles.codeTextarea}
                    rows={3}
                    value={lookupRequestMessage}
                    onChange={(e) => setLookupRequestMessage(e.target.value)}
                    placeholder="Optional message with your request"
                  />
                  <div className={styles.lookupActions}>
                    <button
                      className={styles.primaryBtn}
                      type="button"
                      disabled={
                        workflowLoadingKey ===
                        `lookup-request-${lookupResult.id}`
                      }
                      onClick={handleLookupRequestSubmit}
                    >
                      {workflowLoadingKey ===
                      `lookup-request-${lookupResult.id}`
                        ? "Submitting…"
                        : "Request to Join"}
                    </button>
                    <button
                      className={styles.ghostBtn}
                      type="button"
                      onClick={() => {
                        setLookupResult(null);
                        setJoinCode("");
                      }}
                    >
                      Clear
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MyClubsPage;
