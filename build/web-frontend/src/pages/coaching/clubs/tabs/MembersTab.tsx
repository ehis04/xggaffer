import { useEffect, useState } from 'react';
import { clubsApi } from '../../../../services/api';
import type { ClubContext } from '../IndividualClubBase';
import type {
  ClubInvitation,
  ClubJoinRequest,
  ClubMembershipRole,
} from '../../../../types/club';
import type { ClubPlayer } from '../../../../types/clubPlayers';
import styles from './css/MembersTab.module.css';

interface Props {
  ctx: ClubContext;
}

type SubView = 'invitations' | 'requests' | 'join';

const STAFF_INVITE_ROLE_OPTIONS: Exclude<ClubMembershipRole, 'owner'>[] = [
  'admin', 'coach', 'player', 'viewer',
];

const getRequestStatusLabel = (status: ClubJoinRequest['status']): string => {
  switch (status) {
    case 'pending':   return 'Pending review';
    case 'approved':  return 'Approved';
    case 'rejected':  return 'Rejected';
    case 'withdrawn': return 'Withdrawn';
    case 'cancelled': return 'Cancelled';
    default:          return status;
  }
};

const getInvitationStatusLabel = (status: ClubInvitation['status']): string => {
  switch (status) {
    case 'pending':  return 'Pending response';
    case 'accepted': return 'Accepted';
    case 'declined': return 'Declined';
    case 'revoked':  return 'Revoked';
    case 'expired':  return 'Expired';
    default:         return status;
  }
};

const getStatusColour = (status: string): string => {
  if (['approved', 'accepted'].includes(status)) return '#4ade80';
  if (['pending'].includes(status)) return '#fbbf24';
  return '#9aa4b2';
};

const fmtDate = (v: string | null): string => {
  if (!v) return '—';
  return new Date(v).toLocaleDateString('en-IE', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
};

const MembersTab = ({ ctx }: Props) => {
  const { club, clubId, canManage, isMember, myRole } = ctx;

  const [subView, setSubView] = useState<SubView>(canManage ? 'invitations' : 'join');

  const [joinRequests, setJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [invitations, setInvitations] = useState<ClubInvitation[]>([]);
  const [players, setPlayers] = useState<ClubPlayer[]>([]);
  const [myRequests, setMyRequests] = useState<ClubJoinRequest[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<Exclude<ClubMembershipRole, 'owner'>>('coach');
  const [inviteNote, setInviteNote] = useState('');

  const [requestMessage, setRequestMessage] = useState('');
  const [reviewNotes, setReviewNotes] = useState<Record<number, string>>({});
  const [selectedPlayers, setSelectedPlayers] = useState<Record<number, string>>({});
  const [revokeNotes, setRevokeNotes] = useState<Record<number, string>>({});

  const loadData = async () => {
    const [myReqs] = await Promise.all([clubsApi.listMyJoinRequests()]);
    setMyRequests(myReqs);

    if (canManage) {
      const [reqs, invs, pls] = await Promise.allSettled([
        clubsApi.listClubJoinRequests(clubId),
        clubsApi.listClubInvitations(clubId),
        clubsApi.listPlayers(clubId),
      ]);
      setJoinRequests(reqs.status === 'fulfilled' ? reqs.value : []);
      setInvitations(invs.status === 'fulfilled' ? invs.value : []);
      setPlayers(pls.status === 'fulfilled' ? pls.value : []);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        await loadData();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load member data.');
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, [clubId]);

  const myLatestRequest = myRequests.find((r) => r.club === clubId);
  const availableRosterLinks = players.filter((p) => !p.user);

  const canRequestToJoin =
    club.join_policy === 'approval_required' &&
    !isMember &&
    (!myLatestRequest ||
      ['rejected', 'withdrawn', 'cancelled'].includes(myLatestRequest.status));

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleRequestToJoin = async () => {
    try {
      setLoadingKey('request-join');
      setMessage(null);
      await clubsApi.requestToJoin(clubId, {
        requested_role: 'player',
        message: requestMessage.trim() || undefined,
      });
      setRequestMessage('');
      setMessage('Join request submitted.');
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to submit request.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleApprove = async (req: ClubJoinRequest) => {
    try {
      setLoadingKey(`approve-${req.id}`);
      setMessage(null);
      const selected = selectedPlayers[req.id];
      await clubsApi.approveJoinRequest(clubId, req.id, {
        review_note: reviewNotes[req.id] || '',
        selected_club_player: selected ? Number(selected) : null,
      });
      setMessage('Request approved.');
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to approve.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleReject = async (req: ClubJoinRequest) => {
    try {
      setLoadingKey(`reject-${req.id}`);
      setMessage(null);
      await clubsApi.rejectJoinRequest(clubId, req.id, {
        review_note: reviewNotes[req.id] || '',
      });
      setMessage('Request rejected.');
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to reject.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleCreateInvitation = async () => {
    const trimmed = inviteEmail.trim();
    if (!trimmed || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setMessage('Enter a valid email address.');
      return;
    }
    try {
      setLoadingKey('create-invitation');
      setMessage(null);
      await clubsApi.createInvitation(clubId, {
        invited_email: trimmed,
        invited_role: inviteRole,
        note: inviteNote.trim() || undefined,
      });
      setInviteEmail('');
      setInviteNote('');
      setInviteRole('coach');
      setMessage('Invitation sent.');
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to send invitation.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleRevoke = async (inv: ClubInvitation) => {
    try {
      setLoadingKey(`revoke-${inv.id}`);
      setMessage(null);
      await clubsApi.revokeInvitation(clubId, inv.id, {
        response_note: revokeNotes[inv.id] || '',
      });
      setMessage('Invitation revoked.');
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to revoke.');
    } finally {
      setLoadingKey(null);
    }
  };

  // ── Sub-tabs ─────────────────────────────────────────────────────────────────

  const pendingRequests = joinRequests.filter((r) => r.status === 'pending');
  const pendingInvitations = invitations.filter((i) => i.status === 'pending');

  const SUB_TABS: { value: SubView; label: string; count?: number }[] = canManage
    ? [
        { value: 'invitations', label: 'Invitations', count: pendingInvitations.length || undefined },
        { value: 'requests', label: 'Join requests', count: pendingRequests.length || undefined },
      ]
    : [
        { value: 'join', label: 'Join club' },
      ];

  if (loading) return <div className={styles.loading}>Loading members...</div>;
  if (error) return <div className={styles.errorNotice}>{error}</div>;

  return (
    <div className={styles.tabContent}>
      <div className={styles.topBar}>
        <div className={styles.subViewTabs}>
          {SUB_TABS.map((t) => (
            <button
              key={t.value}
              type="button"
              className={`${styles.subTab}${subView === t.value ? ' ' + styles.subTabActive : ''}`}
              onClick={() => { setSubView(t.value); setMessage(null); }}
            >
              {t.label}
              {t.count !== undefined && t.count > 0 && (
                <span className={styles.countDot}>{t.count}</span>
              )}
            </button>
          ))}
        </div>
        {club.join_code && (
          <div className={styles.joinCode}>
            <span className={styles.joinCodeLabel}>Join code</span>
            <span className={styles.joinCodeValue}>{club.join_code}</span>
          </div>
        )}
      </div>

      {message && (
        <div className={styles.notice}>{message}</div>
      )}

      {/* ── Invitations ───────────────────────────────────────────────────── */}
      {subView === 'invitations' && canManage && (
        <div className={styles.twoCol}>
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>Send invitation</span>
            </div>

            <div className={styles.formGrid}>
              <div className={styles.formGroup} style={{ gridColumn: '1 / -1' }}>
                <label className={styles.label} htmlFor="mb_invite_email">Email address</label>
                <input
                  id="mb_invite_email"
                  type="email"
                  className={styles.input}
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="user@example.com"
                />
              </div>
              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="mb_invite_role">Role</label>
                <select
                  id="mb_invite_role"
                  className={styles.select}
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as Exclude<ClubMembershipRole, 'owner'>)}
                >
                  {STAFF_INVITE_ROLE_OPTIONS.map((r) => (
                    <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="mb_invite_note">Note (optional)</label>
                <input
                  id="mb_invite_note"
                  className={styles.input}
                  value={inviteNote}
                  onChange={(e) => setInviteNote(e.target.value)}
                  placeholder="Optional note for the recipient"
                />
              </div>
            </div>

            <div className={styles.formActions}>
              <button
                type="button"
                className={styles.primaryBtn}
                disabled={loadingKey === 'create-invitation'}
                onClick={handleCreateInvitation}
              >
                {loadingKey === 'create-invitation' ? 'Sending...' : 'Send invitation'}
              </button>
            </div>
          </div>

          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>All invitations</span>
              <span className={styles.badge}>{invitations.length}</span>
            </div>

            {invitations.length === 0 ? (
              <p className={styles.emptyText}>No invitations sent yet.</p>
            ) : (
              <div className={styles.itemList}>
                {invitations.map((inv) => (
                  <div key={inv.id} className={styles.workflowCard}>
                    <div className={styles.workflowHeader}>
                      <div>
                        <span className={styles.workflowTitle}>{inv.invited_user_email}</span>
                        <span className={styles.workflowMeta}>
                          Role: {inv.invited_role} · {getInvitationStatusLabel(inv.status)}
                          {inv.responded_at ? ` · ${fmtDate(inv.responded_at)}` : ''}
                        </span>
                        {inv.note && (
                          <span className={styles.workflowDetail}>Note: {inv.note}</span>
                        )}
                        {inv.response_note && (
                          <span className={styles.workflowDetail}>Response: {inv.response_note}</span>
                        )}
                      </div>
                      <span
                        className={styles.statusPill}
                        style={{ color: getStatusColour(inv.status) }}
                      >
                        {getInvitationStatusLabel(inv.status)}
                      </span>
                    </div>

                    {inv.status === 'pending' && (
                      <div className={styles.revokeRow}>
                        <input
                          className={styles.input}
                          value={revokeNotes[inv.id] || ''}
                          onChange={(e) => setRevokeNotes((p) => ({ ...p, [inv.id]: e.target.value }))}
                          placeholder="Optional revoke note"
                        />
                        <button
                          type="button"
                          className={styles.dangerBtn}
                          disabled={loadingKey === `revoke-${inv.id}`}
                          onClick={() => handleRevoke(inv)}
                        >
                          {loadingKey === `revoke-${inv.id}` ? 'Revoking...' : 'Revoke'}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Join requests ─────────────────────────────────────────────────── */}
      {subView === 'requests' && canManage && (
        <div className={styles.twoCol}>
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>Pending requests</span>
              <span className={styles.badge}>{pendingRequests.length}</span>
            </div>

            {pendingRequests.length === 0 ? (
              <p className={styles.emptyText}>No pending join requests.</p>
            ) : (
              <div className={styles.itemList}>
                {pendingRequests.map((req) => (
                  <div key={req.id} className={styles.workflowCard}>
                    <div className={styles.workflowHeader}>
                      <div>
                        <span className={styles.workflowTitle}>{req.user_email}</span>
                        <span className={styles.workflowMeta}>
                          Role: {req.requested_role} · {fmtDate(req.created_at)}
                        </span>
                        {req.message && (
                          <span className={styles.workflowDetail}>"{req.message}"</span>
                        )}
                      </div>
                    </div>

                    {availableRosterLinks.length > 0 && (
                      <div className={styles.formGroup}>
                        <label className={styles.label} htmlFor={`roster-link-${req.id}`}>
                          Link to roster player (optional)
                        </label>
                        <select
                          id={`roster-link-${req.id}`}
                          className={styles.select}
                          value={selectedPlayers[req.id] || ''}
                          onChange={(e) =>
                            setSelectedPlayers((p) => ({ ...p, [req.id]: e.target.value }))
                          }
                        >
                          <option value="">No roster link</option>
                          {availableRosterLinks.map((pl) => (
                            <option key={pl.id} value={pl.id}>
                              {pl.display_name || `${pl.first_name} ${pl.last_name}`.trim()}
                              {pl.squad_number ? ` #${pl.squad_number}` : ''}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor={`review-note-${req.id}`}>
                        Review note (optional)
                      </label>
                      <input
                        id={`review-note-${req.id}`}
                        className={styles.input}
                        value={reviewNotes[req.id] || ''}
                        onChange={(e) =>
                          setReviewNotes((p) => ({ ...p, [req.id]: e.target.value }))
                        }
                        placeholder="Optional note for the requester"
                      />
                    </div>

                    <div className={styles.formActions}>
                      <button
                        type="button"
                        className={styles.approveBtn}
                        disabled={loadingKey === `approve-${req.id}`}
                        onClick={() => handleApprove(req)}
                      >
                        {loadingKey === `approve-${req.id}` ? 'Approving...' : 'Approve'}
                      </button>
                      <button
                        type="button"
                        className={styles.dangerBtn}
                        disabled={loadingKey === `reject-${req.id}`}
                        onClick={() => handleReject(req)}
                      >
                        {loadingKey === `reject-${req.id}` ? 'Rejecting...' : 'Reject'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>All requests</span>
              <span className={styles.badge}>{joinRequests.length}</span>
            </div>

            {joinRequests.length === 0 ? (
              <p className={styles.emptyText}>No join requests received.</p>
            ) : (
              <div className={styles.itemList}>
                {joinRequests.map((req) => (
                  <div key={req.id} className={styles.workflowCard}>
                    <div className={styles.workflowHeader}>
                      <div>
                        <span className={styles.workflowTitle}>{req.user_email}</span>
                        <span className={styles.workflowMeta}>
                          {req.requested_role} · {fmtDate(req.created_at)}
                        </span>
                        {req.review_note && (
                          <span className={styles.workflowDetail}>
                            Review note: {req.review_note}
                          </span>
                        )}
                        {req.selected_club_player_name && (
                          <span className={styles.workflowDetail}>
                            Linked: {req.selected_club_player_name}
                          </span>
                        )}
                      </div>
                      <span
                        className={styles.statusPill}
                        style={{ color: getStatusColour(req.status) }}
                      >
                        {getRequestStatusLabel(req.status)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Non-member: join club ─────────────────────────────────────────── */}
      {subView === 'join' && !canManage && (
        <div className={styles.joinSection}>
          {club.is_trashed ? (
            <div className={styles.noticeBlock}>
              This club is in trash. Membership workflows are paused.
            </div>
          ) : isMember ? (
            <div className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>Your membership</span>
                {myRole && (
                  <span className={styles.badge}>
                    {myRole.charAt(0).toUpperCase() + myRole.slice(1)}
                  </span>
                )}
              </div>
              <p className={styles.bodyText}>
                You are a member of {club.name}.
              </p>

              {myLatestRequest && (
                <div className={styles.noticeBlock}>
                  Latest request status:{' '}
                  <strong style={{ color: getStatusColour(myLatestRequest.status) }}>
                    {getRequestStatusLabel(myLatestRequest.status)}
                  </strong>
                  {myLatestRequest.review_note && (
                    <div className={styles.workflowDetail}>
                      Reviewer note: {myLatestRequest.review_note}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : club.join_policy === 'approval_required' ? (
            <div className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>Request to join</span>
              </div>

              {myLatestRequest && !canRequestToJoin && (
                <div className={styles.noticeBlock}>
                  Your request is currently{' '}
                  <strong style={{ color: getStatusColour(myLatestRequest.status) }}>
                    {getRequestStatusLabel(myLatestRequest.status)}
                  </strong>
                  {myLatestRequest.review_note && (
                    <div className={styles.workflowDetail}>
                      Reviewer note: {myLatestRequest.review_note}
                    </div>
                  )}
                </div>
              )}

              {canRequestToJoin && (
                <>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="mb_req_message">
                      Message (optional)
                    </label>
                    <textarea
                      id="mb_req_message"
                      className={styles.textarea}
                      rows={3}
                      value={requestMessage}
                      onChange={(e) => setRequestMessage(e.target.value)}
                      placeholder="Optional note to the reviewer"
                    />
                  </div>
                  <div className={styles.formActions}>
                    <button
                      type="button"
                      className={styles.primaryBtn}
                      disabled={loadingKey === 'request-join'}
                      onClick={handleRequestToJoin}
                    >
                      {loadingKey === 'request-join' ? 'Submitting...' : 'Submit request'}
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : club.join_policy === 'invite_only' ? (
            <div className={styles.noticeBlock}>
              This club is invite only. Contact the club admin to receive an invitation.
            </div>
          ) : (
            <div className={styles.noticeBlock}>
              This club is system managed.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MembersTab;