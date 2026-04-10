import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { clubsApi } from '../../../services/api';
import ClubResourcesSection from './resources/ClubResourcesSection';
import type {
  Club,
  ClubInvitation,
  ClubJoinRequest,
  ClubMembershipRole,
  ClubEvent,
  Fixture,
  ClubCalendarFeedItem,
  ClubEventType,
  FixtureVenue,
  FixtureStatus,
} from '../../../types/club';
import type { ClubPlayer } from '../../../types/clubPlayers';
import styles from './css/IndividualClubBase.module.css';

const FEATURES = [
  {
    key: 'teamsheets',
    title: 'Teamsheets',
    description: 'Create and manage match day teamsheets',
    path: (clubId: number) => `/clubs/${clubId}/teamsheets`,
  },
  {
    key: 'players',
    title: 'Players',
    description: 'View, manage, and sync your squad',
    path: (clubId: number) => `/clubs/${clubId}/players`,
  },
];

const STAFF_INVITE_ROLE_OPTIONS: Exclude<ClubMembershipRole, 'owner'>[] = [
  'admin',
  'coach',
  'player',
  'viewer',
];

const EVENT_TYPE_OPTIONS: { value: ClubEventType; label: string }[] = [
  { value: 'training', label: 'Training' },
  { value: 'meeting', label: 'Meeting' },
  { value: 'social', label: 'Social' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'other', label: 'Other' },
];

const FIXTURE_VENUE_OPTIONS: { value: FixtureVenue; label: string }[] = [
  { value: 'home', label: 'Home' },
  { value: 'away', label: 'Away' },
  { value: 'neutral', label: 'Neutral' },
];

const FIXTURE_STATUS_OPTIONS: { value: FixtureStatus; label: string }[] = [
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'completed', label: 'Completed' },
  { value: 'postponed', label: 'Postponed' },
  { value: 'cancelled', label: 'Cancelled' },
];

type EventFormState = {
  title: string;
  event_type: ClubEventType;
  description: string;
  start_datetime: string;
  end_datetime: string;
  is_all_day: boolean;
  location: string;
  is_mandatory: boolean;
};

type FixtureFormState = {
  opponent_name: string;
  venue: FixtureVenue;
  competition: string;
  match_datetime: string;
  location: string;
  fixture_status: FixtureStatus;
};

const createEmptyEventForm = (): EventFormState => ({
  title: '',
  event_type: 'training',
  description: '',
  start_datetime: '',
  end_datetime: '',
  is_all_day: false,
  location: '',
  is_mandatory: false,
});

const createEmptyFixtureForm = (): FixtureFormState => ({
  opponent_name: '',
  venue: 'home',
  competition: '',
  match_datetime: '',
  location: '',
  fixture_status: 'scheduled',
});

const buildTags = (club: Club): string[] => {
  const tags: string[] = [];

  if (club.club_type === 'user_fictional') {
    tags.push(club.fictional_basis === 'real_club_copy' ? 'Fictional copy' : 'Fictional club');
  } else if (club.club_type === 'user_real_non_pro') {
    tags.push('Real non-pro club');
  } else if (club.club_type === 'system_professional') {
    tags.push('System professional club');
  }

  if (club.directory_visibility === 'hidden_code_only') {
    tags.push('Hidden club');
  } else if (club.directory_visibility === 'listed') {
    tags.push('Listed club');
  }

  if (club.join_policy === 'approval_required') {
    tags.push('Approval required');
  } else if (club.join_policy === 'invite_only') {
    tags.push('Invite only');
  } else if (club.join_policy === 'system_managed') {
    tags.push('System managed');
  }

  if (club.verification_status === 'pending') {
    tags.push('Pending verification');
  } else if (club.verification_status === 'approved') {
    tags.push('Verified');
  } else if (club.verification_status === 'rejected') {
    tags.push('Verification rejected');
  }

  return tags;
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

const formatDateTimeLabel = (value: string) => {
  return new Date(value).toLocaleString('en-IE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const toDateTimeLocalValue = (value: string | null) => {
  if (!value) {
    return '';
  }

  const date = new Date(value);
  const timezoneOffsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - timezoneOffsetMs).toISOString().slice(0, 16);
};

const toIsoStringFromLocalValue = (value: string) => {
  return new Date(value).toISOString();
};

const getScheduleItemSummary = (item: ClubCalendarFeedItem) => {
  if (item.item_type === 'event' && item.event) {
    return `${item.event.event_type_display} · ${item.event.source_type_display}`;
  }

  if (item.item_type === 'fixture' && item.fixture) {
    const competition = item.fixture.competition || 'Fixture';
    return `${competition} · ${item.fixture.venue_display} · ${item.fixture.source_type_display}`;
  }

  return '';
};

export const IndividualClubBase = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();

  const numericClubId = Number(clubId);

  const [club, setClub] = useState<Club | null>(null);
  const [myClubIds, setMyClubIds] = useState<number[]>([]);
  const [myJoinRequests, setMyJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [reviewJoinRequests, setReviewJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [reviewInvitations, setReviewInvitations] = useState<ClubInvitation[]>([]);
  const [clubPlayers, setClubPlayers] = useState<ClubPlayer[]>([]);

  const [calendarFeed, setCalendarFeed] = useState<ClubCalendarFeedItem[]>([]);
  const [events, setEvents] = useState<ClubEvent[]>([]);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);

  const [loading, setLoading] = useState(true);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [reviewAccess, setReviewAccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [workflowMessage, setWorkflowMessage] = useState<string | null>(null);

  const [requestMessage, setRequestMessage] = useState('');
  const [inviteUserIdInput, setInviteUserIdInput] = useState('');
  const [inviteRole, setInviteRole] = useState<Exclude<ClubMembershipRole, 'owner'>>('coach');
  const [inviteNote, setInviteNote] = useState('');

  const [editingEventId, setEditingEventId] = useState<number | null>(null);
  const [eventForm, setEventForm] = useState<EventFormState>(createEmptyEventForm());
  const [editingFixtureId, setEditingFixtureId] = useState<number | null>(null);
  const [fixtureForm, setFixtureForm] = useState<FixtureFormState>(createEmptyFixtureForm());

  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [selectedClubPlayerByRequest, setSelectedClubPlayerByRequest] = useState<Record<number, string>>({});
  const [reviewNoteByRequest, setReviewNoteByRequest] = useState<Record<number, string>>({});
  const [revokeNoteByInvitation, setRevokeNoteByInvitation] = useState<Record<number, string>>({});

  const reloadClubWorkflowData = async (clubRecord: Club) => {
    const myRequestsPromise = clubsApi.listMyJoinRequests();
    const myClubsPromise = clubsApi.myClubs();

    let reviewerRequests: ClubJoinRequest[] = [];
    let reviewerInvitations: ClubInvitation[] = [];
    let players: ClubPlayer[] = [];
    let hasReviewAccess = false;

    try {
      reviewerRequests = await clubsApi.listClubJoinRequests(clubRecord.id);
      reviewerInvitations = await clubsApi.listClubInvitations(clubRecord.id);
      players = await clubsApi.listPlayers(clubRecord.id);
      hasReviewAccess = true;
    } catch {
      hasReviewAccess = false;
    }

    const [myRequestsData, myClubsData] = await Promise.all([
      myRequestsPromise,
      myClubsPromise,
    ]);

    setMyJoinRequests(myRequestsData);
    setMyClubIds(myClubsData.map((entry) => entry.id));
    setReviewJoinRequests(reviewerRequests);
    setReviewInvitations(reviewerInvitations);
    setClubPlayers(players);
    setReviewAccess(hasReviewAccess);
  };

  const reloadSchedulingData = async (clubRecord: Club) => {
    try {
      setScheduleLoading(true);
      setScheduleError(null);

      const [calendarData, eventData, fixtureData] = await Promise.all([
        clubsApi.listCalendarFeed(clubRecord.id, { limit: 6 }),
        clubsApi.listEvents(clubRecord.id),
        clubsApi.listFixtures(clubRecord.id),
      ]);

      setCalendarFeed(calendarData);
      setEvents(eventData);
      setFixtures(fixtureData);
    } catch (err) {
      setCalendarFeed([]);
      setEvents([]);
      setFixtures([]);
      setScheduleError(err instanceof Error ? err.message : 'Failed to load scheduling data.');
    } finally {
      setScheduleLoading(false);
    }
  };

  useEffect(() => {
    const fetchClub = async () => {
      try {
        setLoading(true);
        setError(null);

        const clubData = await clubsApi.get(numericClubId);
        setClub(clubData);
        await reloadClubWorkflowData(clubData);
        await reloadSchedulingData(clubData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load club');
      } finally {
        setLoading(false);
      }
    };

    if (Number.isFinite(numericClubId)) {
      void fetchClub();
    }
  }, [numericClubId]);

  const tags = useMemo(() => (club ? buildTags(club) : []), [club]);
  const metaParts = useMemo(
    () => (club ? [club.city, club.country, club.division].filter(Boolean) : []),
    [club]
  );

  const isMember = club ? myClubIds.includes(club.id) : false;
  const myLatestRequest = club
    ? myJoinRequests.find((request) => request.club === club.id)
    : undefined;

  const availableRosterLinks = useMemo(
    () => clubPlayers.filter((player) => !player.user),
    [clubPlayers]
  );

  const requestCanBeSubmitted =
    club?.join_policy === 'approval_required' &&
    !isMember &&
    (!myLatestRequest ||
      myLatestRequest.status === 'rejected' ||
      myLatestRequest.status === 'withdrawn' ||
      myLatestRequest.status === 'cancelled');

  const canAttemptSchedulingManagement = Boolean(
    club && isMember && club.club_type !== 'system_professional'
  );

  const handleRequestToJoin = async () => {
    if (!club) {
      return;
    }

    try {
      setLoadingKey(`request-${club.id}`);
      setWorkflowMessage(null);

      await clubsApi.requestToJoin(club.id, {
        requested_role: 'player',
        message: requestMessage.trim() || undefined,
      });

      setRequestMessage('');
      setWorkflowMessage('Join request submitted successfully.');
      await reloadClubWorkflowData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to submit join request.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleApproveRequest = async (request: ClubJoinRequest) => {
    if (!club) {
      return;
    }

    try {
      setLoadingKey(`approve-${request.id}`);
      setWorkflowMessage(null);

      const selectedValue = selectedClubPlayerByRequest[request.id];
      await clubsApi.approveJoinRequest(club.id, request.id, {
        review_note: reviewNoteByRequest[request.id] || '',
        selected_club_player: selectedValue ? Number(selectedValue) : null,
      });

      setWorkflowMessage('Join request approved.');
      await reloadClubWorkflowData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to approve join request.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleRejectRequest = async (request: ClubJoinRequest) => {
    if (!club) {
      return;
    }

    try {
      setLoadingKey(`reject-${request.id}`);
      setWorkflowMessage(null);

      await clubsApi.rejectJoinRequest(club.id, request.id, {
        review_note: reviewNoteByRequest[request.id] || '',
      });

      setWorkflowMessage('Join request rejected.');
      await reloadClubWorkflowData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to reject join request.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleCreateInvitation = async () => {
    if (!club) {
      return;
    }

    const invitedUser = Number(inviteUserIdInput);
    if (!Number.isInteger(invitedUser) || invitedUser <= 0) {
      setWorkflowMessage('Enter a valid existing platform user ID for the invitation.');
      return;
    }

    try {
      setLoadingKey('create-invitation');
      setWorkflowMessage(null);

      await clubsApi.createInvitation(club.id, {
        invited_user: invitedUser,
        invited_role: inviteRole,
        note: inviteNote.trim() || undefined,
      });

      setInviteUserIdInput('');
      setInviteRole('coach');
      setInviteNote('');
      setWorkflowMessage('Invitation created successfully.');
      await reloadClubWorkflowData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to create invitation.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleRevokeInvitation = async (invitation: ClubInvitation) => {
    if (!club) {
      return;
    }

    try {
      setLoadingKey(`revoke-${invitation.id}`);
      setWorkflowMessage(null);

      await clubsApi.revokeInvitation(club.id, invitation.id, {
        response_note: revokeNoteByInvitation[invitation.id] || '',
      });

      setWorkflowMessage('Invitation revoked.');
      await reloadClubWorkflowData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to revoke invitation.');
    } finally {
      setLoadingKey(null);
    }
  };

  const resetEventForm = () => {
    setEditingEventId(null);
    setEventForm(createEmptyEventForm());
  };

  const resetFixtureForm = () => {
    setEditingFixtureId(null);
    setFixtureForm(createEmptyFixtureForm());
  };

  const handleEventSubmit = async () => {
    if (!club) {
      return;
    }

    if (!eventForm.title.trim() || !eventForm.start_datetime) {
      setWorkflowMessage('Event title and start date/time are required.');
      return;
    }

    try {
      setLoadingKey(editingEventId ? `save-event-${editingEventId}` : 'create-event');
      setWorkflowMessage(null);

      const payload = {
        title: eventForm.title.trim(),
        event_type: eventForm.event_type,
        description: eventForm.description.trim(),
        start_datetime: toIsoStringFromLocalValue(eventForm.start_datetime),
        end_datetime: eventForm.end_datetime ? toIsoStringFromLocalValue(eventForm.end_datetime) : null,
        is_all_day: eventForm.is_all_day,
        location: eventForm.location.trim(),
        is_mandatory: eventForm.is_mandatory,
      };

      if (editingEventId) {
        await clubsApi.updateEvent(club.id, editingEventId, payload);
        setWorkflowMessage('Club event updated successfully.');
      } else {
        await clubsApi.createEvent(club.id, payload);
        setWorkflowMessage('Club event created successfully.');
      }

      resetEventForm();
      await reloadSchedulingData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to save club event.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleFixtureSubmit = async () => {
    if (!club) {
      return;
    }

    if (!fixtureForm.opponent_name.trim() || !fixtureForm.match_datetime) {
      setWorkflowMessage('Opponent and fixture date/time are required.');
      return;
    }

    try {
      setLoadingKey(editingFixtureId ? `save-fixture-${editingFixtureId}` : 'create-fixture');
      setWorkflowMessage(null);

      const payload = {
        opponent_name: fixtureForm.opponent_name.trim(),
        venue: fixtureForm.venue,
        competition: fixtureForm.competition.trim(),
        match_datetime: toIsoStringFromLocalValue(fixtureForm.match_datetime),
        location: fixtureForm.location.trim(),
        fixture_status: fixtureForm.fixture_status,
      };

      if (editingFixtureId) {
        await clubsApi.updateFixture(club.id, editingFixtureId, payload);
        setWorkflowMessage('Fixture updated successfully.');
      } else {
        await clubsApi.createFixture(club.id, payload);
        setWorkflowMessage('Fixture created successfully.');
      }

      resetFixtureForm();
      await reloadSchedulingData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to save fixture.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleEditEvent = (event: ClubEvent) => {
    setEditingEventId(event.id);
    setEventForm({
      title: event.title,
      event_type: event.event_type,
      description: event.description,
      start_datetime: toDateTimeLocalValue(event.start_datetime),
      end_datetime: toDateTimeLocalValue(event.end_datetime),
      is_all_day: event.is_all_day,
      location: event.location,
      is_mandatory: event.is_mandatory,
    });
  };

  const handleEditFixture = (fixture: Fixture) => {
    setEditingFixtureId(fixture.id);
    setFixtureForm({
      opponent_name: fixture.opponent_name,
      venue: fixture.venue,
      competition: fixture.competition,
      match_datetime: toDateTimeLocalValue(fixture.match_datetime),
      location: fixture.location,
      fixture_status: fixture.fixture_status,
    });
  };

  const handleDeleteEvent = async (event: ClubEvent) => {
    if (!club) {
      return;
    }

    const confirmed = window.confirm(`Delete the event “${event.title}”?`);
    if (!confirmed) {
      return;
    }

    try {
      setLoadingKey(`delete-event-${event.id}`);
      setWorkflowMessage(null);
      await clubsApi.deleteEvent(club.id, event.id);
      setWorkflowMessage('Club event deleted successfully.');
      if (editingEventId === event.id) {
        resetEventForm();
      }
      await reloadSchedulingData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to delete club event.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleDeleteFixture = async (fixture: Fixture) => {
    if (!club) {
      return;
    }

    const confirmed = window.confirm(`Delete the fixture against “${fixture.opponent_name}”?`);
    if (!confirmed) {
      return;
    }

    try {
      setLoadingKey(`delete-fixture-${fixture.id}`);
      setWorkflowMessage(null);
      await clubsApi.deleteFixture(club.id, fixture.id);
      setWorkflowMessage('Fixture deleted successfully.');
      if (editingFixtureId === fixture.id) {
        resetFixtureForm();
      }
      await reloadSchedulingData(club);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to delete fixture.');
    } finally {
      setLoadingKey(null);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading club...</div>
      </div>
    );
  }

  if (error || !club) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>{error || 'Club not found'}</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <div className={styles.clubInfo}>
          <h1>{club.name}</h1>
          {metaParts.length > 0 && (
            <p className={styles.meta}>{metaParts.join(' · ')}</p>
          )}

          {tags.length > 0 && (
            <div className={styles.tagRow}>
              {tags.map((tag) => (
                <span key={tag} className={styles.tag}>
                  {tag}
                </span>
              ))}
            </div>
          )}

          {club.source_real_club_name && (
            <p className={styles.referenceText}>
              Reference club: {club.source_real_club_name}
            </p>
          )}
        </div>

        <div className={styles.heroActions}>
          <button className={styles.backButton} onClick={() => navigate('/clubs')}>
            Back to Clubs
          </button>
          <button className={styles.secondaryButton} onClick={() => navigate('/clubs/browse')}>
            Discover Clubs
          </button>
        </div>
      </section>

      {workflowMessage && <div className={styles.notice}>{workflowMessage}</div>}
      {scheduleError && <div className={styles.error}>{scheduleError}</div>}

      <section className={styles.infoGrid}>
        <div className={styles.infoPanel}>
          <h2 className={styles.panelTitle}>Club Profile</h2>
          <p className={styles.bodyText}>{club.description}</p>

          {club.directory_visibility === 'hidden_code_only' && club.join_code && (
            <div className={styles.codeBox}>
              <div className={styles.codeLabel}>Join code</div>
              <div className={styles.codeValue}>{club.join_code}</div>
            </div>
          )}
        </div>

        <div className={styles.infoPanel}>
          <h2 className={styles.panelTitle}>Membership Workflow</h2>

          {isMember ? (
            <div className={styles.noticeBlock}>
              You already belong to this club workspace.
            </div>
          ) : club.join_policy === 'approval_required' ? (
            <>
              <p className={styles.bodyText}>
                This club supports a real player request-to-join flow. Approval is still required before membership is granted.
              </p>

              {myLatestRequest && (
                <div className={styles.noticeBlock}>
                  Your latest request: <strong>{getRequestStatusLabel(myLatestRequest.status)}</strong>
                  {myLatestRequest.review_note && (
                    <div className={styles.detailNote}>Reviewer note: {myLatestRequest.review_note}</div>
                  )}
                </div>
              )}

              {requestCanBeSubmitted && (
                <>
                  <textarea
                    className={styles.textarea}
                    value={requestMessage}
                    onChange={(event) => setRequestMessage(event.target.value)}
                    placeholder="Optional note to the reviewer"
                    rows={3}
                  />
                  <button
                    className={styles.primaryButton}
                    type="button"
                    disabled={loadingKey === `request-${club.id}`}
                    onClick={handleRequestToJoin}
                  >
                    {loadingKey === `request-${club.id}` ? 'Submitting...' : 'Request to Join'}
                  </button>
                </>
              )}
            </>
          ) : club.join_policy === 'invite_only' ? (
            <div className={styles.noticeBlock}>
              This club is invite only. No self-service join request is available from this page.
            </div>
          ) : (
            <div className={styles.noticeBlock}>
              This club is system managed and is not claimable through ordinary user flows.
            </div>
          )}
        </div>
      </section>

      <ClubResourcesSection
        club={club}
        isMember={isMember}
      />

      {reviewAccess && (
        <div className={styles.reviewGrid}>
          <section className={styles.infoPanel}>
            <h2 className={styles.panelTitle}>Pending Join Requests</h2>

            {reviewJoinRequests.length === 0 ? (
              <p className={styles.bodyText}>No join requests have been submitted for this club.</p>
            ) : (
              <div className={styles.workflowList}>
                {reviewJoinRequests.map((request) => (
                  <div key={request.id} className={styles.workflowCard}>
                    <div className={styles.workflowHeaderRow}>
                      <div>
                        <div className={styles.workflowTitle}>{request.user_email}</div>
                        <div className={styles.workflowMeta}>
                          Requested role: {request.requested_role} · Status: {getRequestStatusLabel(request.status)}
                        </div>
                      </div>
                    </div>

                    {request.message && (
                      <div className={styles.detailNote}>Requester note: {request.message}</div>
                    )}

                    {request.status === 'pending' ? (
                      <>
                        <label
                          className={styles.formLabel}
                          htmlFor={`selected-club-player-${request.id}`}
                        >
                          Optional roster link
                        </label>
                        <select
                          id={`selected-club-player-${request.id}`}
                          className={styles.input}
                          value={selectedClubPlayerByRequest[request.id] || ''}
                          onChange={(event) =>
                            setSelectedClubPlayerByRequest((prev) => ({
                              ...prev,
                              [request.id]: event.target.value,
                            }))
                          }
                        >
                          <option value="">No manual roster link</option>
                          {availableRosterLinks.map((player) => (
                            <option key={player.id} value={player.id}>
                              {player.full_name} {player.squad_number ? `#${player.squad_number}` : ''}
                            </option>
                          ))}
                        </select>

                        <label
                          className={styles.formLabel}
                          htmlFor={`review-note-${request.id}`}
                        >
                          Review note
                        </label>
                        <textarea
                          id={`review-note-${request.id}`}
                          className={styles.textarea}
                          rows={3}
                          value={reviewNoteByRequest[request.id] || ''}
                          onChange={(event) =>
                            setReviewNoteByRequest((prev) => ({
                              ...prev,
                              [request.id]: event.target.value,
                            }))
                          }
                          placeholder="Optional note for the requester"
                        />

                        <div className={styles.inlineActions}>
                          <button
                            className={styles.primaryButton}
                            type="button"
                            disabled={loadingKey === `approve-${request.id}`}
                            onClick={() => handleApproveRequest(request)}
                          >
                            {loadingKey === `approve-${request.id}` ? 'Approving...' : 'Approve'}
                          </button>
                          <button
                            className={styles.secondaryButton}
                            type="button"
                            disabled={loadingKey === `reject-${request.id}`}
                            onClick={() => handleRejectRequest(request)}
                          >
                            {loadingKey === `reject-${request.id}` ? 'Rejecting...' : 'Reject'}
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        {request.selected_club_player_name && (
                          <div className={styles.detailNote}>
                            Linked roster row: {request.selected_club_player_name}
                          </div>
                        )}
                        {request.review_note && (
                          <div className={styles.detailNote}>Review note: {request.review_note}</div>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className={styles.infoPanel}>
            <h2 className={styles.panelTitle}>Invitations</h2>

            <div className={styles.noticeBlock}>
              Invitations currently target existing platform users only. This frontend uses an explicit user ID input because no separate user-lookup flow has been introduced in this phase.
            </div>

            <div className={styles.formGrid}>
              <div className={styles.formField}>
                <label className={styles.formLabel} htmlFor="invited-user-id">
                  Invited user ID
                </label>
                <input
                  id="invited-user-id"
                  className={styles.input}
                  type="number"
                  min={1}
                  value={inviteUserIdInput}
                  onChange={(event) => setInviteUserIdInput(event.target.value)}
                  placeholder="Existing user ID"
                />
              </div>

              <div className={styles.formField}>
                <label className={styles.formLabel} htmlFor="invite-role">
                  Role
                </label>
                <select
                  id="invite-role"
                  className={styles.input}
                  value={inviteRole}
                  onChange={(event) =>
                    setInviteRole(event.target.value as Exclude<ClubMembershipRole, 'owner'>)
                  }
                >
                  {STAFF_INVITE_ROLE_OPTIONS.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className={styles.formField}>
              <label className={styles.formLabel} htmlFor="invite-note">
                Invite note
              </label>
              <textarea
                id="invite-note"
                className={styles.textarea}
                rows={3}
                value={inviteNote}
                onChange={(event) => setInviteNote(event.target.value)}
                placeholder="Optional note for the invited user"
              />
            </div>

            <div className={styles.inlineActions}>
              <button
                className={styles.primaryButton}
                type="button"
                disabled={loadingKey === 'create-invitation'}
                onClick={handleCreateInvitation}
              >
                {loadingKey === 'create-invitation' ? 'Sending...' : 'Send Invitation'}
              </button>
            </div>

            <div className={styles.workflowList}>
              {reviewInvitations.length === 0 ? (
                <p className={styles.bodyText}>No invitations have been sent for this club yet.</p>
              ) : (
                reviewInvitations.map((invitation) => (
                  <div key={invitation.id} className={styles.workflowCard}>
                    <div className={styles.workflowTitle}>{invitation.invited_user_email}</div>
                    <div className={styles.workflowMeta}>
                      Role: {invitation.invited_role} · Status: {getInvitationStatusLabel(invitation.status)}
                    </div>

                    {invitation.note && (
                      <div className={styles.detailNote}>Invite note: {invitation.note}</div>
                    )}
                    {invitation.response_note && (
                      <div className={styles.detailNote}>Response note: {invitation.response_note}</div>
                    )}

                    {invitation.status === 'pending' && (
                      <>
                        <textarea
                          className={styles.textarea}
                          rows={2}
                          value={revokeNoteByInvitation[invitation.id] || ''}
                          onChange={(event) =>
                            setRevokeNoteByInvitation((prev) => ({
                              ...prev,
                              [invitation.id]: event.target.value,
                            }))
                          }
                          placeholder="Optional revoke note"
                        />
                        <div className={styles.inlineActions}>
                          <button
                            className={styles.secondaryButton}
                            type="button"
                            disabled={loadingKey === `revoke-${invitation.id}`}
                            onClick={() => handleRevokeInvitation(invitation)}
                          >
                            {loadingKey === `revoke-${invitation.id}` ? 'Revoking...' : 'Revoke'}
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      )}

      <section className={styles.featureSection}>
        <div className={styles.featureHeader}>
          <h2 className={styles.panelTitle}>Club Scheduling</h2>
        </div>

        <div className={styles.reviewGrid}>
          <section className={styles.infoPanel}>
            <h3 className={styles.panelTitle}>Upcoming Schedule</h3>

            {scheduleLoading ? (
              <p className={styles.bodyText}>Loading upcoming schedule…</p>
            ) : calendarFeed.length === 0 ? (
              <div className={styles.noticeBlock}>
                No upcoming events or fixtures have been scheduled yet.
              </div>
            ) : (
              <div className={styles.workflowList}>
                {calendarFeed.map((item) => (
                  <div key={`${item.item_type}-${item.item_type === 'event' ? item.event?.id : item.fixture?.id}`} className={styles.workflowCard}>
                    <div className={styles.workflowHeaderRow}>
                      <div>
                        <div className={styles.workflowTitle}>{item.calendar_label}</div>
                        <div className={styles.workflowMeta}>
                          {formatDateTimeLabel(item.sort_datetime)}
                        </div>
                      </div>
                      <span className={styles.tag}>
                        {item.item_type === 'event' ? 'Event' : 'Fixture'}
                      </span>
                    </div>
                    <div className={styles.detailNote}>{getScheduleItemSummary(item)}</div>
                    {item.item_type === 'event' && item.event?.location && (
                      <div className={styles.detailNote}>Location: {item.event.location}</div>
                    )}
                    {item.item_type === 'fixture' && item.fixture?.location && (
                      <div className={styles.detailNote}>Location: {item.fixture.location}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className={styles.infoPanel}>
            <h3 className={styles.panelTitle}>Scheduling Access</h3>

            {club.club_type === 'system_professional' ? (
              <div className={styles.noticeBlock}>
                This club uses a read-only scheduling surface in Phase D. Official events and fixtures can be shown here, but ordinary manual scheduling is intentionally restricted.
              </div>
            ) : isMember ? (
              <div className={styles.noticeBlock}>
                Upcoming events and fixtures are now available in the club workspace. Manual scheduling actions are intended for club staff on user-managed clubs, and backend rules still enforce those permissions.
              </div>
            ) : (
              <div className={styles.noticeBlock}>
                You can view the schedule for this club here. Scheduling management becomes available inside the club workspace for authorised members.
              </div>
            )}
          </section>
        </div>

        <div className={styles.reviewGrid}>
          <section className={styles.infoPanel}>
            <h3 className={styles.panelTitle}>Club Events</h3>

            {canAttemptSchedulingManagement && (
              <>
                <div className={styles.formGrid}>
                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="club-event-title">
                      Title
                    </label>
                    <input
                      id="club-event-title"
                      className={styles.input}
                      type="text"
                      value={eventForm.title}
                      onChange={(event) => setEventForm((prev) => ({ ...prev, title: event.target.value }))}
                      placeholder="e.g. Tuesday analysis session"
                    />
                  </div>

                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="club-event-type">
                      Event type
                    </label>
                    <select
                      id="club-event-type"
                      className={styles.input}
                      value={eventForm.event_type}
                      onChange={(event) =>
                        setEventForm((prev) => ({ ...prev, event_type: event.target.value as ClubEventType }))
                      }
                    >
                      {EVENT_TYPE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className={styles.formGrid}>
                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="club-event-start">
                      Start date and time
                    </label>
                    <input
                      id="club-event-start"
                      className={styles.input}
                      type="datetime-local"
                      value={eventForm.start_datetime}
                      onChange={(event) => setEventForm((prev) => ({ ...prev, start_datetime: event.target.value }))}
                    />
                  </div>

                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="club-event-end">
                      End date and time
                    </label>
                    <input
                      id="club-event-end"
                      className={styles.input}
                      type="datetime-local"
                      value={eventForm.end_datetime}
                      onChange={(event) => setEventForm((prev) => ({ ...prev, end_datetime: event.target.value }))}
                    />
                  </div>
                </div>

                <div className={styles.formGrid}>
                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="club-event-location">
                      Location
                    </label>
                    <input
                      id="club-event-location"
                      className={styles.input}
                      type="text"
                      value={eventForm.location}
                      onChange={(event) => setEventForm((prev) => ({ ...prev, location: event.target.value }))}
                      placeholder="e.g. Main pitch"
                    />
                  </div>
                </div>

                <div className={styles.formField}>
                  <label className={styles.formLabel} htmlFor="club-event-description">
                    Description
                  </label>
                  <textarea
                    id="club-event-description"
                    className={styles.textarea}
                    rows={3}
                    value={eventForm.description}
                    onChange={(event) => setEventForm((prev) => ({ ...prev, description: event.target.value }))}
                    placeholder="Optional event details"
                  />
                </div>

                <div className={styles.inlineActions}>
                  <label className={styles.bodyText} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input
                      type="checkbox"
                      checked={eventForm.is_all_day}
                      onChange={(event) => setEventForm((prev) => ({ ...prev, is_all_day: event.target.checked }))}
                    />
                    All day event
                  </label>

                  <label className={styles.bodyText} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input
                      type="checkbox"
                      checked={eventForm.is_mandatory}
                      onChange={(event) => setEventForm((prev) => ({ ...prev, is_mandatory: event.target.checked }))}
                    />
                    Mandatory
                  </label>
                </div>

                <div className={styles.inlineActions}>
                  <button
                    className={styles.primaryButton}
                    type="button"
                    disabled={loadingKey === 'create-event' || (editingEventId !== null && loadingKey === `save-event-${editingEventId}`)}
                    onClick={handleEventSubmit}
                  >
                    {editingEventId !== null
                      ? loadingKey === `save-event-${editingEventId}`
                        ? 'Saving...'
                        : 'Save Event'
                      : loadingKey === 'create-event'
                        ? 'Creating...'
                        : 'Create Event'}
                  </button>
                  {editingEventId !== null && (
                    <button className={styles.secondaryButton} type="button" onClick={resetEventForm}>
                      Cancel Edit
                    </button>
                  )}
                </div>
              </>
            )}

            <div className={styles.workflowList}>
              {events.length === 0 ? (
                <p className={styles.bodyText}>No club events have been created yet.</p>
              ) : (
                events.map((event) => (
                  <div key={event.id} className={styles.workflowCard}>
                    <div className={styles.workflowHeaderRow}>
                      <div>
                        <div className={styles.workflowTitle}>{event.title}</div>
                        <div className={styles.workflowMeta}>
                          {event.event_type_display} · {formatDateTimeLabel(event.start_datetime)}
                        </div>
                      </div>
                      <span className={styles.tag}>{event.source_type_display}</span>
                    </div>

                    {event.location && (
                      <div className={styles.detailNote}>Location: {event.location}</div>
                    )}
                    {event.end_datetime && (
                      <div className={styles.detailNote}>Ends: {formatDateTimeLabel(event.end_datetime)}</div>
                    )}
                    {event.description && (
                      <div className={styles.detailNote}>{event.description}</div>
                    )}
                    {event.is_mandatory && (
                      <div className={styles.detailNote}>Mandatory event</div>
                    )}

                    {canAttemptSchedulingManagement && event.is_user_editable && (
                      <div className={styles.inlineActions}>
                        <button
                          className={styles.secondaryButton}
                          type="button"
                          onClick={() => handleEditEvent(event)}
                        >
                          Edit
                        </button>
                        <button
                          className={styles.secondaryButton}
                          type="button"
                          disabled={loadingKey === `delete-event-${event.id}`}
                          onClick={() => handleDeleteEvent(event)}
                        >
                          {loadingKey === `delete-event-${event.id}` ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>

          <section className={styles.infoPanel}>
            <h3 className={styles.panelTitle}>Fixtures</h3>

            {canAttemptSchedulingManagement && (
              <>
                <div className={styles.formGrid}>
                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="fixture-opponent-name">
                      Opponent
                    </label>
                    <input
                      id="fixture-opponent-name"
                      className={styles.input}
                      type="text"
                      value={fixtureForm.opponent_name}
                      onChange={(event) => setFixtureForm((prev) => ({ ...prev, opponent_name: event.target.value }))}
                      placeholder="e.g. Dublin City FC"
                    />
                  </div>

                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="fixture-venue">
                      Venue
                    </label>
                    <select
                      id="fixture-venue"
                      className={styles.input}
                      value={fixtureForm.venue}
                      onChange={(event) =>
                        setFixtureForm((prev) => ({ ...prev, venue: event.target.value as FixtureVenue }))
                      }
                    >
                      {FIXTURE_VENUE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className={styles.formGrid}>
                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="fixture-competition">
                      Competition
                    </label>
                    <input
                      id="fixture-competition"
                      className={styles.input}
                      type="text"
                      value={fixtureForm.competition}
                      onChange={(event) => setFixtureForm((prev) => ({ ...prev, competition: event.target.value }))}
                      placeholder="e.g. Friendly or League"
                    />
                  </div>

                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="fixture-status">
                      Status
                    </label>
                    <select
                      id="fixture-status"
                      className={styles.input}
                      value={fixtureForm.fixture_status}
                      onChange={(event) =>
                        setFixtureForm((prev) => ({ ...prev, fixture_status: event.target.value as FixtureStatus }))
                      }
                    >
                      {FIXTURE_STATUS_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className={styles.formGrid}>
                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="fixture-match-datetime">
                      Match date and time
                    </label>
                    <input
                      id="fixture-match-datetime"
                      className={styles.input}
                      type="datetime-local"
                      value={fixtureForm.match_datetime}
                      onChange={(event) => setFixtureForm((prev) => ({ ...prev, match_datetime: event.target.value }))}
                    />
                  </div>

                  <div className={styles.formField}>
                    <label className={styles.formLabel} htmlFor="fixture-location">
                      Location
                    </label>
                    <input
                      id="fixture-location"
                      className={styles.input}
                      type="text"
                      value={fixtureForm.location}
                      onChange={(event) => setFixtureForm((prev) => ({ ...prev, location: event.target.value }))}
                      placeholder="e.g. Main ground"
                    />
                  </div>
                </div>

                <div className={styles.inlineActions}>
                  <button
                    className={styles.primaryButton}
                    type="button"
                    disabled={loadingKey === 'create-fixture' || (editingFixtureId !== null && loadingKey === `save-fixture-${editingFixtureId}`)}
                    onClick={handleFixtureSubmit}
                  >
                    {editingFixtureId !== null
                      ? loadingKey === `save-fixture-${editingFixtureId}`
                        ? 'Saving...'
                        : 'Save Fixture'
                      : loadingKey === 'create-fixture'
                        ? 'Creating...'
                        : 'Create Fixture'}
                  </button>
                  {editingFixtureId !== null && (
                    <button className={styles.secondaryButton} type="button" onClick={resetFixtureForm}>
                      Cancel Edit
                    </button>
                  )}
                </div>
              </>
            )}

            <div className={styles.workflowList}>
              {fixtures.length === 0 ? (
                <p className={styles.bodyText}>No fixtures have been scheduled yet.</p>
              ) : (
                fixtures.map((fixture) => (
                  <div key={fixture.id} className={styles.workflowCard}>
                    <div className={styles.workflowHeaderRow}>
                      <div>
                        <div className={styles.workflowTitle}>{fixture.calendar_label}</div>
                        <div className={styles.workflowMeta}>
                          {fixture.competition || 'Fixture'} · {formatDateTimeLabel(fixture.match_datetime)}
                        </div>
                      </div>
                      <span className={styles.tag}>{fixture.source_type_display}</span>
                    </div>

                    <div className={styles.detailNote}>
                      Venue: {fixture.venue_display} · Status: {fixture.fixture_status_display}
                    </div>
                    {fixture.location && (
                      <div className={styles.detailNote}>Location: {fixture.location}</div>
                    )}

                    {canAttemptSchedulingManagement && fixture.is_user_editable && (
                      <div className={styles.inlineActions}>
                        <button
                          className={styles.secondaryButton}
                          type="button"
                          onClick={() => handleEditFixture(fixture)}
                        >
                          Edit
                        </button>
                        <button
                          className={styles.secondaryButton}
                          type="button"
                          disabled={loadingKey === `delete-fixture-${fixture.id}`}
                          onClick={() => handleDeleteFixture(fixture)}
                        >
                          {loadingKey === `delete-fixture-${fixture.id}` ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </section>

      <section className={styles.featureSection}>
        <div className={styles.featureHeader}>
          <h2 className={styles.panelTitle}>Club Workspace</h2>
        </div>

        <div className={styles.grid}>
          {FEATURES.map((feature) => (
            <div
              key={feature.key}
              className={styles.card}
              onClick={() => navigate(feature.path(club.id))}
            >
              <h3 className={styles.cardTitle}>{feature.title}</h3>
              <p className={styles.cardDesc}>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default IndividualClubBase;
