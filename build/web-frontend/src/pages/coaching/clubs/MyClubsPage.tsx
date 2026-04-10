import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../../services/api/client';
import { clubsApi } from '../../../services/api';
import type { Club, ClubInvitation, ClubJoinRequest } from '../../../types/club';
import { ClubCard } from '../../../components/Clubs';
import styles from './css/MyClubsPage.module.css';

const collectRoleValues = (value: unknown): string[] => {
  if (typeof value === 'string') {
    return [value];
  }

  if (Array.isArray(value)) {
    return value.flatMap(collectRoleValues);
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return [
      ...collectRoleValues(record.role),
      ...collectRoleValues(record.roles),
      ...collectRoleValues(record.results),
      ...collectRoleValues(record.data),
      ...collectRoleValues(record.code),
      ...collectRoleValues(record.name),
    ];
  }

  return [];
};

const isCoachCapablePayload = (payload: unknown): boolean => {
  return collectRoleValues(payload).some((value) => {
    const normalised = value.trim().toLowerCase();
    return normalised === 'c' || normalised === 'coach';
  });
};

const getRequestStatusLabel = (status: ClubJoinRequest['status']) => {
  switch (status) {
    case 'pending':
      return 'Pending review';
    case 'approved':
      return 'Approved';
    case 'rejected':
      return 'Rejected';
    case 'withdrawn':
      return 'Withdrawn';
    case 'cancelled':
      return 'Cancelled';
    default:
      return status;
  }
};

const getInvitationStatusLabel = (status: ClubInvitation['status']) => {
  switch (status) {
    case 'pending':
      return 'Pending response';
    case 'accepted':
      return 'Accepted';
    case 'declined':
      return 'Declined';
    case 'revoked':
      return 'Revoked';
    case 'expired':
      return 'Expired';
    default:
      return status;
  }
};

const MyClubsPage: React.FC = () => {
  const navigate = useNavigate();

  const [clubs, setClubs] = useState<Club[]>([]);
  const [myJoinRequests, setMyJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [myInvitations, setMyInvitations] = useState<ClubInvitation[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [canCreateClub, setCanCreateClub] = useState<boolean | null>(null);
  const [roleCheckError, setRoleCheckError] = useState<string | null>(null);

  const [joinCode, setJoinCode] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupResult, setLookupResult] = useState<Club | null>(null);
  const [lookupRequestMessage, setLookupRequestMessage] = useState('');

  const [workflowLoadingKey, setWorkflowLoadingKey] = useState<string | null>(null);
  const [workflowMessage, setWorkflowMessage] = useState<string | null>(null);

  const loadPage = async () => {
    try {
      setLoading(true);
      setError(null);

      const [clubsData, rolePayload, requestsData, invitationsData] = await Promise.all([
        clubsApi.myClubs(),
        apiClient.get<unknown>('/users/profile/role/'),
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
        setRoleCheckError('Role capability could not be confirmed on this page. Backend rules still apply.');
      } catch (clubsError) {
        setError(clubsError instanceof Error ? clubsError.message : 'Failed to load clubs');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPage();
  }, []);

  const hiddenOwnedClubs = useMemo(
    () => clubs.filter((club) => club.directory_visibility === 'hidden_code_only'),
    [clubs]
  );

  const joinedClubIds = useMemo(
    () => new Set(clubs.map((club) => club.id)),
    [clubs]
  );

  const latestLookupRequest = lookupResult
    ? myJoinRequests.find((request) => request.club === lookupResult.id)
    : undefined;

  const handleClubClick = (club: Club) => {
    navigate(`/clubs/${club.id}/`);
  };

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
      setLookupError('Enter a join code first.');
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
      setLookupError(err instanceof Error ? err.message : 'No hidden club found for that code.');
    } finally {
      setLookupLoading(false);
    }
  };

  const handleCreateClick = () => {
    navigate('/clubs/create');
  };

  const handleSwitchToCoach = async () => {
    try {
      setWorkflowLoadingKey('switch-to-coach');
      setWorkflowMessage(null);

      await apiClient.post('/users/profile/role/', { role: 'C' });
      await apiClient.put('/users/profile/active-role/', { role: 'C' });

      setCanCreateClub(true);
      setRoleCheckError(null);
      setWorkflowMessage('Role switched to Coach. You can now create clubs with this account.');
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to switch role to Coach.');
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const handleLookupRequestSubmit = async () => {
    if (!lookupResult) {
      return;
    }

    try {
      setWorkflowLoadingKey(`lookup-request-${lookupResult.id}`);
      setWorkflowMessage(null);

      await clubsApi.requestToJoin(lookupResult.id, {
        requested_role: 'player',
        message: lookupRequestMessage.trim() || undefined,
      });

      setLookupRequestMessage('');
      setWorkflowMessage('Join request submitted successfully.');
      await refreshWorkflowState();
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to submit join request.');
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
      setWorkflowMessage('Join request withdrawn.');
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to withdraw request.');
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
      setWorkflowMessage('Invitation accepted.');
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to accept invitation.');
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
      setWorkflowMessage('Invitation declined.');
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to decline invitation.');
    } finally {
      setWorkflowLoadingKey(null);
    }
  };

  const renderCreateButtonLabel = () => {
    if (canCreateClub === false) {
      return 'Create Club (coach role required)';
    }

    return 'Create Club';
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading your clubs...</div>
      </div>
    );
  }

  const lookupIsMember = lookupResult ? joinedClubIds.has(lookupResult.id) : false;
  const switchingToCoach = workflowLoadingKey === 'switch-to-coach';
  const canSubmitLookupRequest =
    lookupResult?.join_policy === 'approval_required' &&
    (!latestLookupRequest ||
      latestLookupRequest.status === 'rejected' ||
      latestLookupRequest.status === 'withdrawn' ||
      latestLookupRequest.status === 'cancelled');

  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <div>
          <h1 className={styles.title}>Clubs</h1>
          <p className={styles.subtitle}>
            Manage your clubs, discover listed clubs, track your own membership workflow, and look up hidden clubs by code.
          </p>
        </div>

        <div className={styles.heroActions}>
          <button
            className={styles.primaryButton}
            onClick={handleCreateClick}
            disabled={canCreateClub === false}
            title={canCreateClub === false ? 'Coach-capable users can create clubs.' : undefined}
          >
            {renderCreateButtonLabel()}
          </button>

          <button
            className={styles.secondaryButton}
            onClick={() => navigate('/clubs/browse')}
          >
            Discover Clubs
          </button>

          <button
            className={styles.secondaryButton}
            onClick={() => navigate('/livefootball')}
          >
            Live Football
          </button>
        </div>
      </section>

      {error && <div className={styles.error}>{error}</div>}
      {roleCheckError && <div className={styles.notice}>{roleCheckError}</div>}
      {canCreateClub === false && (
        <div className={styles.notice}>
          Your current account roles do not include coach capability, so club creation is disabled.
          <div className={styles.noticeActions}>
            <button
              className={styles.primaryButton}
              type="button"
              onClick={handleSwitchToCoach}
              disabled={switchingToCoach}
            >
              {switchingToCoach ? 'Switching...' : 'Switch Role to Coach'}
            </button>
          </div>
        </div>
      )}
      {workflowMessage && <div className={styles.notice}>{workflowMessage}</div>}

      <div className={styles.topGrid}>
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Join by Code</h2>
            <span className={styles.badge}>Hidden clubs</span>
          </div>

          <p className={styles.panelCopy}>
            Hidden clubs do not appear in normal browse results. Enter a join code to look one up safely.
          </p>

          <form className={styles.codeForm} onSubmit={handleLookupByCode}>
            <input
              className={styles.codeInput}
              value={joinCode}
              onChange={(event) => setJoinCode(event.target.value.toUpperCase())}
              placeholder="Enter join code"
              maxLength={12}
            />
            <button className={styles.primaryButton} type="submit" disabled={lookupLoading}>
              {lookupLoading ? 'Looking up...' : 'Find Club'}
            </button>
          </form>

          {lookupError && <div className={styles.errorInline}>{lookupError}</div>}

          {lookupResult && (
            <div className={styles.lookupResult}>
              <div className={styles.lookupTitleRow}>
                <h3 className={styles.lookupTitle}>{lookupResult.name}</h3>
                <span className={styles.badge}>Match found</span>
              </div>

              <p className={styles.lookupMeta}>
                {lookupResult.club_type === 'user_real_non_pro' && 'Real non-pro club'}
                {lookupResult.club_type === 'user_fictional' &&
                  (lookupResult.fictional_basis === 'real_club_copy'
                    ? 'Fictional copy'
                    : 'Fictional club')}
                {lookupResult.club_type === 'system_professional' && 'System professional club'}
              </p>

              <p className={styles.lookupText}>{lookupResult.description}</p>

              {lookupResult.source_real_club_name && (
                <p className={styles.lookupMeta}>
                  Reference club: {lookupResult.source_real_club_name}
                </p>
              )}

              {lookupIsMember ? (
                <div className={styles.noticeBlock}>
                  You are already in this club. Open the club workspace instead of requesting access again.
                  <div className={styles.inlineActions}>
                    <button
                      className={styles.secondaryButton}
                      type="button"
                      onClick={() => navigate(`/clubs/${lookupResult.id}/`)}
                    >
                      Open Club
                    </button>
                  </div>
                </div>
              ) : lookupResult.join_policy === 'approval_required' ? (
                <>
                  {latestLookupRequest && (
                    <div className={styles.noticeBlock}>
                      Your latest request is currently: <strong>{getRequestStatusLabel(latestLookupRequest.status)}</strong>
                      {latestLookupRequest.review_note && (
                        <div className={styles.detailNote}>Reviewer note: {latestLookupRequest.review_note}</div>
                      )}
                    </div>
                  )}

                  {canSubmitLookupRequest ? (
                    <>
                      <textarea
                        className={styles.codeTextarea}
                        value={lookupRequestMessage}
                        onChange={(event) => setLookupRequestMessage(event.target.value)}
                        placeholder="Optional note to the reviewer"
                        rows={3}
                      />
                      <div className={styles.inlineActions}>
                        <button
                          className={styles.primaryButton}
                          type="button"
                          onClick={handleLookupRequestSubmit}
                          disabled={workflowLoadingKey === `lookup-request-${lookupResult.id}`}
                        >
                          {workflowLoadingKey === `lookup-request-${lookupResult.id}`
                            ? 'Submitting...'
                            : 'Request to Join'}
                        </button>
                      </div>
                    </>
                  ) : null}
                </>
              ) : lookupResult.join_policy === 'invite_only' ? (
                <div className={styles.noticeBlock}>
                  This club is invite only. Lookup by code reveals the club safely, but does not bypass the invite requirement.
                </div>
              ) : (
                <div className={styles.noticeBlock}>
                  This club is system managed and is not claimable through ordinary user flows.
                </div>
              )}
            </div>
          )}
        </section>

        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Your Hidden Clubs</h2>
            <span className={styles.badge}>{hiddenOwnedClubs.length}</span>
          </div>

          {hiddenOwnedClubs.length === 0 ? (
            <p className={styles.panelCopy}>
              You do not currently manage any hidden code-only clubs.
            </p>
          ) : (
            <div className={styles.hiddenClubList}>
              {hiddenOwnedClubs.map((club) => (
                <button
                  key={club.id}
                  type="button"
                  className={styles.hiddenClubRow}
                  onClick={() => handleClubClick(club)}
                >
                  <div>
                    <div className={styles.hiddenClubName}>{club.name}</div>
                    <div className={styles.hiddenClubMeta}>Join code: {club.join_code || 'Pending'}</div>
                  </div>
                  <span className={styles.hiddenClubArrow}>→</span>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className={styles.workflowGrid}>
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>My Join Requests</h2>
            <span className={styles.badge}>{myJoinRequests.length}</span>
          </div>

          {myJoinRequests.length === 0 ? (
            <p className={styles.panelCopy}>
              You have not submitted any club join requests yet.
            </p>
          ) : (
            <div className={styles.workflowList}>
              {myJoinRequests.map((request) => (
                <div key={request.id} className={styles.workflowRow}>
                  <div>
                    <div className={styles.workflowName}>{request.club_name}</div>
                    <div className={styles.workflowMeta}>
                      Status: {getRequestStatusLabel(request.status)}
                    </div>
                    {request.message && (
                      <div className={styles.detailNote}>Your note: {request.message}</div>
                    )}
                    {request.review_note && (
                      <div className={styles.detailNote}>Reviewer note: {request.review_note}</div>
                    )}
                  </div>

                  <div className={styles.inlineActions}>
                    {request.status === 'pending' && (
                      <button
                        className={styles.secondaryButton}
                        type="button"
                        disabled={workflowLoadingKey === `withdraw-${request.id}`}
                        onClick={() => handleWithdrawRequest(request)}
                      >
                        {workflowLoadingKey === `withdraw-${request.id}` ? 'Withdrawing...' : 'Withdraw'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>My Invitations</h2>
            <span className={styles.badge}>{myInvitations.length}</span>
          </div>

          {myInvitations.length === 0 ? (
            <p className={styles.panelCopy}>
              You do not currently have any club invitations.
            </p>
          ) : (
            <div className={styles.workflowList}>
              {myInvitations.map((invitation) => (
                <div key={invitation.id} className={styles.workflowRow}>
                  <div>
                    <div className={styles.workflowName}>{invitation.club_name}</div>
                    <div className={styles.workflowMeta}>
                      Role: {invitation.invited_role} · Status: {getInvitationStatusLabel(invitation.status)}
                    </div>
                    {invitation.note && (
                      <div className={styles.detailNote}>Invite note: {invitation.note}</div>
                    )}
                    {invitation.response_note && (
                      <div className={styles.detailNote}>Response note: {invitation.response_note}</div>
                    )}
                  </div>

                  <div className={styles.inlineActions}>
                    {invitation.status === 'pending' && (
                      <>
                        <button
                          className={styles.primaryButton}
                          type="button"
                          disabled={workflowLoadingKey === `accept-${invitation.id}`}
                          onClick={() => handleAcceptInvitation(invitation)}
                        >
                          {workflowLoadingKey === `accept-${invitation.id}` ? 'Accepting...' : 'Accept'}
                        </button>
                        <button
                          className={styles.secondaryButton}
                          type="button"
                          disabled={workflowLoadingKey === `decline-${invitation.id}`}
                          onClick={() => handleDeclineInvitation(invitation)}
                        >
                          {workflowLoadingKey === `decline-${invitation.id}` ? 'Declining...' : 'Decline'}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>My Clubs</h2>
          <span className={styles.badge}>{clubs.length}</span>
        </div>

        {clubs.length === 0 ? (
          <div className={styles.empty}>
            <p>You do not have any clubs yet.</p>
            <div className={styles.emptyActions}>
              <button
                className={styles.secondaryButton}
                onClick={() => navigate('/clubs/browse')}
              >
                Discover listed clubs
              </button>
              <button
                className={styles.secondaryButton}
                onClick={handleCreateClick}
                disabled={canCreateClub === false}
              >
                {renderCreateButtonLabel()}
              </button>
            </div>
          </div>
        ) : (
          <div className={styles.grid}>
            {clubs.map((club) => (
              <ClubCard
                key={club.id}
                club={club}
                variant="mine"
                onClick={handleClubClick}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default MyClubsPage;