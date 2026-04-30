import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { clubsApi } from '../../../services/api';
import { ClubCalendar } from '../../../components/Clubs';
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
import styles from './css/ClubDetails.module.css';
import { useAuth } from '../../../context/useAuth';
import { Sidebar } from '../../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';
import { ClubsNavBar } from '../../../components/Navigation/ClubsNavBar';


const STAFF_INVITE_ROLE_OPTIONS: Exclude<ClubMembershipRole, 'owner'>[] = [
  'admin', 'coach', 'player', 'viewer',
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

const QUICK_ACTIONS = [
  {
    key: 'session',
    icon: (
      <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
    title: 'Plan a session',
    desc: 'Build drills, themes, and timings.',
    path: (id: number) => `/clubs/${id}/sessions/new`,
  },
  {
    key: 'announcement',
    icon: (
      <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
    title: 'Announcement',
    desc: 'Message the whole squad.',
    path: (id: number) => `/clubs/${id}/announcements/new`,
  },
  {
    key: 'invite',
    icon: (
      <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
      </svg>
    ),
    title: 'Invite player',
    desc: 'Generate a join link or code.',
    path: (id: number) => `/clubs/${id}/invite`,
  },
  {
    key: 'fixture',
    icon: (
      <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    ),
    title: 'Add fixture',
    desc: 'Schedule league or cup games.',
    path: (id: number) => `/clubs/${id}/fixtures/new`,
  },
];


type EventFormState = {
  title: string; event_type: ClubEventType; description: string;
  start_datetime: string; end_datetime: string; is_all_day: boolean;
  location: string; is_mandatory: boolean;
};

type FixtureFormState = {
  opponent_name: string; venue: FixtureVenue; competition: string;
  match_datetime: string; location: string; fixture_status: FixtureStatus;
};

const createEmptyEventForm = (): EventFormState => ({
  title: '', event_type: 'training', description: '',
  start_datetime: '', end_datetime: '', is_all_day: false,
  location: '', is_mandatory: false,
});

const createEmptyFixtureForm = (): FixtureFormState => ({
  opponent_name: '', venue: 'home', competition: '',
  match_datetime: '', location: '', fixture_status: 'scheduled',
});

const buildTags = (club: Club): string[] => {
  const tags: string[] = [];
  if (club.club_type === 'user_fictional') tags.push(club.fictional_basis === 'real_club_copy' ? 'Fictional copy' : 'Fictional club');
  else if (club.club_type === 'user_real_non_pro') tags.push('Real non-pro club');
  else if (club.club_type === 'system_professional') tags.push('System professional club');
  if (club.directory_visibility === 'hidden_code_only') tags.push('Hidden club');
  else if (club.directory_visibility === 'listed') tags.push('Listed club');
  if (club.join_policy === 'approval_required') tags.push('Approval required');
  else if (club.join_policy === 'invite_only') tags.push('Invite only');
  else if (club.join_policy === 'system_managed') tags.push('System managed');
  if (club.verification_status === 'pending') tags.push('Pending verification');
  else if (club.verification_status === 'approved') tags.push('Verified');
  else if (club.verification_status === 'rejected') tags.push('Verification rejected');
  return tags;
};

const getRequestStatusLabel = (status: ClubJoinRequest['status']) => {
  const map: Record<string, string> = {
    pending: 'Pending review', approved: 'Approved', rejected: 'Rejected',
    withdrawn: 'Withdrawn', cancelled: 'Cancelled',
  };
  return map[status] ?? status;
};

const getInvitationStatusLabel = (status: ClubInvitation['status']) => {
  const map: Record<string, string> = {
    pending: 'Pending response', accepted: 'Accepted', declined: 'Declined',
    revoked: 'Revoked', expired: 'Expired',
  };
  return map[status] ?? status;
};

const formatDateTimeLabel = (value: string) =>
  new Date(value).toLocaleString('en-IE', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });

const toDateTimeLocalValue = (value: string | null) => {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
};

const toIsoStringFromLocalValue = (value: string) => new Date(value).toISOString();

const getScheduleItemSummary = (item: ClubCalendarFeedItem) => {
  if (item.item_type === 'event' && item.event) return `${item.event.event_type_display} · ${item.event.source_type_display}`;
  if (item.item_type === 'fixture' && item.fixture) {
    const comp = item.fixture.competition || 'Fixture';
    return `${comp} · ${item.fixture.venue_display} · ${item.fixture.source_type_display}`;
  }
  return '';
};

const fixtureTypeColors: Record<string, string> = {
  League: '#3b82f6', Cup: '#a78bfa', Friendly: '#f59e0b', Training: '#22c55e',
};

export const ClubDetailsPage = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  const numericClubId = Number(clubId);
  const isTrashView = searchParams.get('view') === 'trash';

  const [club, setClub] = useState<Club | null>(null);
  const [myClubIds, setMyClubIds] = useState<number[]>([]);
  const [myJoinRequests, setMyJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [reviewJoinRequests, setReviewJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [reviewInvitations, setReviewInvitations] = useState<ClubInvitation[]>([]);
  const [clubPlayers, setClubPlayers] = useState<ClubPlayer[]>([]);
  const [clubActionLoading, setClubActionLoading] = useState(false);
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
  const [inviteEmailInput, setInviteEmailInput] = useState('');
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
    } catch { hasReviewAccess = false; }
    const [myRequestsData, myClubsData] = await Promise.all([myRequestsPromise, myClubsPromise]);
    setMyJoinRequests(myRequestsData);
    setMyClubIds(myClubsData.map((e) => e.id));
    setReviewJoinRequests(reviewerRequests);
    setReviewInvitations(reviewerInvitations);
    setClubPlayers(players);
    setReviewAccess(hasReviewAccess);
  };

  const reloadSchedulingData = async (clubRecord: Club) => {
    try {
      setScheduleLoading(true); setScheduleError(null);
      const [calendarData, eventData, fixtureData] = await Promise.all([
        clubsApi.listCalendarFeed(clubRecord.id, { limit: 50 }),
        clubsApi.listEvents(clubRecord.id),
        clubsApi.listFixtures(clubRecord.id),
      ]);
      setCalendarFeed(calendarData); setEvents(eventData); setFixtures(fixtureData);
    } catch (err) {
      setCalendarFeed([]); setEvents([]); setFixtures([]);
      setScheduleError(err instanceof Error ? err.message : 'Failed to load scheduling data.');
    } finally { setScheduleLoading(false); }
  };

  useEffect(() => {
    const fetchClub = async () => {
      try {
        setLoading(true); setError(null);
        const clubData = await clubsApi.get(numericClubId, isTrashView ? { trash: 'only' } : undefined);
        setClub(clubData);
        await reloadClubWorkflowData(clubData);
        await reloadSchedulingData(clubData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load club');
      } finally { setLoading(false); }
    };
    if (Number.isFinite(numericClubId)) void fetchClub();
  }, [numericClubId, isTrashView]);

  const tags = useMemo(() => (club ? buildTags(club) : []), [club]);
  const metaParts = useMemo(
    () => (club ? [club.division, `Founded ${(club as any).founded_year ?? ''}`, club.city].filter(Boolean) : []),
    [club]
  );

  const isMember = club ? myClubIds.includes(club.id) : false;
  const myLatestRequest = club ? myJoinRequests.find((r) => r.club === club.id) : undefined;
  const availableRosterLinks = useMemo(() => clubPlayers.filter((p) => !p.user), [clubPlayers]);

  const requestCanBeSubmitted =
    club?.join_policy === 'approval_required' && !isMember &&
    (!myLatestRequest || ['rejected', 'withdrawn', 'cancelled'].includes(myLatestRequest.status));

  const canAttemptSchedulingManagement = Boolean(
    club && isMember && club.club_type !== 'system_professional' && reviewAccess
  );

  const canManageClubTrash =
    typeof user?.id === 'number' && typeof club?.creator === 'number' && user.id === club.creator;

  const handleBackToClubs = () => navigate(`/clubs${isTrashView ? '?view=trash' : ''}`);

  const handleMoveClubToTrash = async () => {
    if (!club || !window.confirm(`Move "${club.name}" to trash?`)) return;
    try { setClubActionLoading(true); setWorkflowMessage(null); await clubsApi.trash(club.id); navigate('/clubs?view=trash'); }
    catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to move club to trash.'); }
    finally { setClubActionLoading(false); }
  };

  const handleRestoreClub = async () => {
    if (!club) return;
    try { setClubActionLoading(true); setWorkflowMessage(null); await clubsApi.restore(club.id); navigate(`/clubs/${club.id}/`); }
    catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to restore club.'); }
    finally { setClubActionLoading(false); }
  };

  const handlePermanentDeleteClub = async () => {
    if (!club || !window.confirm(`Delete "${club.name}" permanently? This cannot be undone.`)) return;
    try { setClubActionLoading(true); setWorkflowMessage(null); await clubsApi.permanentDelete(club.id); navigate('/clubs?view=trash'); }
    catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to permanently delete club.'); }
    finally { setClubActionLoading(false); }
  };

  const handleRequestToJoin = async () => {
    if (!club) return;
    try {
      setLoadingKey(`request-${club.id}`); setWorkflowMessage(null);
      await clubsApi.requestToJoin(club.id, { requested_role: 'player', message: requestMessage.trim() || undefined });
      setRequestMessage(''); setWorkflowMessage('Join request submitted successfully.');
      await reloadClubWorkflowData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to submit join request.'); }
    finally { setLoadingKey(null); }
  };

  const handleApproveRequest = async (request: ClubJoinRequest) => {
    if (!club) return;
    try {
      setLoadingKey(`approve-${request.id}`); setWorkflowMessage(null);
      const selectedValue = selectedClubPlayerByRequest[request.id];
      await clubsApi.approveJoinRequest(club.id, request.id, {
        selected_club_player: selectedValue ? Number(selectedValue) : undefined,
        review_note: reviewNoteByRequest[request.id] || '',
      });
      setWorkflowMessage('Join request approved.'); await reloadClubWorkflowData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to approve join request.'); }
    finally { setLoadingKey(null); }
  };

  const handleRejectRequest = async (request: ClubJoinRequest) => {
    if (!club) return;
    try {
      setLoadingKey(`reject-${request.id}`); setWorkflowMessage(null);
      await clubsApi.rejectJoinRequest(club.id, request.id, { review_note: reviewNoteByRequest[request.id] || '' });
      setWorkflowMessage('Join request rejected.'); await reloadClubWorkflowData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to reject join request.'); }
    finally { setLoadingKey(null); }
  };

  const handleCreateInvitation = async () => {
    if (!club) return;
    const trimmedEmail = inviteEmailInput.trim();
    if (!trimmedEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setWorkflowMessage('Enter a valid email address to invite.'); return;
    }
    try {
      setLoadingKey('create-invitation'); setWorkflowMessage(null);
      await clubsApi.createInvitation(club.id, { invited_email: trimmedEmail, invited_role: inviteRole, note: inviteNote.trim() || undefined });
      setInviteEmailInput(''); setInviteRole('coach'); setInviteNote('');
      setWorkflowMessage('Invitation created successfully.'); await reloadClubWorkflowData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to create invitation.'); }
    finally { setLoadingKey(null); }
  };

  const handleRevokeInvitation = async (invitation: ClubInvitation) => {
    if (!club) return;
    try {
      setLoadingKey(`revoke-${invitation.id}`); setWorkflowMessage(null);
      await clubsApi.revokeInvitation(club.id, invitation.id, { response_note: revokeNoteByInvitation[invitation.id] || '' });
      setWorkflowMessage('Invitation revoked.'); await reloadClubWorkflowData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to revoke invitation.'); }
    finally { setLoadingKey(null); }
  };

  const resetEventForm = () => { setEditingEventId(null); setEventForm(createEmptyEventForm()); };
  const resetFixtureForm = () => { setEditingFixtureId(null); setFixtureForm(createEmptyFixtureForm()); };

  const handleEventSubmit = async () => {
    if (!club) return;
    if (!eventForm.title.trim() || !eventForm.start_datetime) { setWorkflowMessage('Event title and start date/time are required.'); return; }
    try {
      setLoadingKey(editingEventId ? `save-event-${editingEventId}` : 'create-event'); setWorkflowMessage(null);
      const payload = {
        title: eventForm.title.trim(), event_type: eventForm.event_type, description: eventForm.description.trim(),
        start_datetime: toIsoStringFromLocalValue(eventForm.start_datetime),
        end_datetime: eventForm.end_datetime ? toIsoStringFromLocalValue(eventForm.end_datetime) : null,
        is_all_day: eventForm.is_all_day, location: eventForm.location.trim(), is_mandatory: eventForm.is_mandatory,
      };
      if (editingEventId) { await clubsApi.updateEvent(club.id, editingEventId, payload); setWorkflowMessage('Club event updated.'); }
      else { await clubsApi.createEvent(club.id, payload); setWorkflowMessage('Club event created.'); }
      resetEventForm(); await reloadSchedulingData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to save club event.'); }
    finally { setLoadingKey(null); }
  };

  const handleFixtureSubmit = async () => {
    if (!club) return;
    if (!fixtureForm.opponent_name.trim() || !fixtureForm.match_datetime) { setWorkflowMessage('Opponent and fixture date/time are required.'); return; }
    try {
      setLoadingKey(editingFixtureId ? `save-fixture-${editingFixtureId}` : 'create-fixture'); setWorkflowMessage(null);
      const payload = {
        opponent_name: fixtureForm.opponent_name.trim(), venue: fixtureForm.venue, competition: fixtureForm.competition.trim(),
        match_datetime: toIsoStringFromLocalValue(fixtureForm.match_datetime),
        location: fixtureForm.location.trim(), fixture_status: fixtureForm.fixture_status,
      };
      if (editingFixtureId) { await clubsApi.updateFixture(club.id, editingFixtureId, payload); setWorkflowMessage('Fixture updated.'); }
      else { await clubsApi.createFixture(club.id, payload); setWorkflowMessage('Fixture created.'); }
      resetFixtureForm(); await reloadSchedulingData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to save fixture.'); }
    finally { setLoadingKey(null); }
  };

  const handleEditEvent = (event: ClubEvent) => {
    setEditingEventId(event.id);
    setEventForm({ title: event.title, event_type: event.event_type, description: event.description, start_datetime: toDateTimeLocalValue(event.start_datetime), end_datetime: toDateTimeLocalValue(event.end_datetime), is_all_day: event.is_all_day, location: event.location, is_mandatory: event.is_mandatory });
  };

  const handleEditFixture = (fixture: Fixture) => {
    setEditingFixtureId(fixture.id);
    setFixtureForm({ opponent_name: fixture.opponent_name, venue: fixture.venue, competition: fixture.competition, match_datetime: toDateTimeLocalValue(fixture.match_datetime), location: fixture.location, fixture_status: fixture.fixture_status });
  };

  const handleDeleteEvent = async (event: ClubEvent) => {
    if (!club || !window.confirm(`Delete the event "${event.title}"?`)) return;
    try {
      setLoadingKey(`delete-event-${event.id}`); setWorkflowMessage(null);
      await clubsApi.deleteEvent(club.id, event.id); setWorkflowMessage('Club event deleted.');
      if (editingEventId === event.id) resetEventForm();
      await reloadSchedulingData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to delete club event.'); }
    finally { setLoadingKey(null); }
  };

  const handleDeleteFixture = async (fixture: Fixture) => {
    if (!club || !window.confirm(`Delete the fixture against "${fixture.opponent_name}"?`)) return;
    try {
      setLoadingKey(`delete-fixture-${fixture.id}`); setWorkflowMessage(null);
      await clubsApi.deleteFixture(club.id, fixture.id); setWorkflowMessage('Fixture deleted.');
      if (editingFixtureId === fixture.id) resetFixtureForm();
      await reloadSchedulingData(club);
    } catch (err) { setWorkflowMessage(err instanceof Error ? err.message : 'Failed to delete fixture.'); }
    finally { setLoadingKey(null); }
  };

  if (loading) return (
    <div className={styles.individualClubShell}>
      <div className="sidebar-section"><Sidebar /></div>
      <div className={styles.individualClubMain}>
        <div className={styles.individualClubLoadingState}>
          <div className={styles.individualClubSpinner} />
          <p>Loading club…</p>
        </div>
      </div>
    </div>
  );

  if (error || !club) return (
    <div className={styles.individualClubShell}>
      <div className="sidebar-section"><Sidebar /></div>
      <div className={styles.individualClubMain}>
        <div className={styles.individualClubErrorState}>{error || 'Club not found'}</div>
      </div>
    </div>
  );

  const initials = club.name.split(' ').map((w) => w[0]?.toUpperCase() ?? '').slice(0, 2).join('');
  const upcomingItems = calendarFeed.slice(0, 5);
  const squadPreview = clubPlayers.slice(0, 7);
  const pendingRequests = reviewJoinRequests.filter((r) => r.status === 'pending');

  return (
    <div className={styles.individualClubShell}>
      <div className="sidebar-section"><Sidebar /></div>

      <div className={styles.individualClubMain}>
        <header className={styles.individualClubHeader}>
          <div className={styles.individualClubHeaderLeft}>
            <span className={styles.individualClubHeaderLabel} onClick={handleBackToClubs} style={{ cursor: 'pointer' }}>← Clubs</span>
            <span className={styles.individualClubHeaderSep}>·</span>
            <span className={styles.individualClubHeaderTitle}>{club.name}</span>
          </div>
          <div className={styles.individualClubHeaderMiddle}>
            <ClubsNavBar />
          </div>
          <div className={styles.individualClubHeaderRight}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles.individualClubContent}>

          <section className={styles.individualClubHero}>
            <div className={styles.individualClubHeroLeft}>
              <div className={styles.individualClubBadge}>
                {club.badge
                  ? <img src={club.badge} alt={club.name} className={styles.individualClubBadgeImg} />
                  : <span className={styles.individualClubBadgeInitials}>{initials}</span>
                }
              </div>
              <div className={styles.individualClubHeroInfo}>
                <h1 className={styles.individualClubName}>{club.name}</h1>
                {metaParts.length > 0 && (
                  <p className={styles.individualClubMeta}>{metaParts.join(' · ')}</p>
                )}
                <div className={styles.individualClubTagRow}>
                  {tags.map((tag) => (
                    <span key={tag} className={styles.individualClubTag}>{tag}</span>
                  ))}
                  {club.player_count != null && (
                    <span className={styles.individualClubTag}>{club.player_count} players</span>
                  )}
                  {(club as any).head_coach && (
                    <span className={styles.individualClubTag}>Head coach: {(club as any).head_coach}</span>
                  )}
                </div>
              </div>
            </div>
            <div className={styles.individualClubHeroActions}>
              <button className={styles.individualClubPrimaryBtn} onClick={() => navigate(`/clubs/${club.id}/sessions/new`)}>
                + New session
              </button>
              <button className={styles.individualClubGhostBtn} onClick={() => navigate(`/clubs/${club.id}/invite`)}>
                Invite player
              </button>
              <button className={styles.individualClubGhostBtn}>
                Share club
              </button>
              {canManageClubTrash && !club.is_trashed && (
                <button className={styles.individualClubDangerBtn} disabled={clubActionLoading} onClick={handleMoveClubToTrash}>
                  {clubActionLoading ? 'Moving…' : 'Move to Trash'}
                </button>
              )}
              {club.is_trashed && canManageClubTrash && (
                <>
                  <button className={styles.individualClubRestoreBtn} disabled={clubActionLoading} onClick={handleRestoreClub}>
                    {clubActionLoading ? 'Restoring…' : 'Restore'}
                  </button>
                  <button className={styles.individualClubDangerBtn} disabled={clubActionLoading} onClick={handlePermanentDeleteClub}>
                    {clubActionLoading ? 'Deleting…' : 'Delete Permanently'}
                  </button>
                </>
              )}
            </div>
          </section>

          {club.is_trashed && (
            <div className={styles.individualClubTrashNotice}>
              This club is in trash. Workspace is in recovery mode.
              {club.trash_expires_at && <> Expires {new Date(club.trash_expires_at).toLocaleDateString('en-IE', { day: 'numeric', month: 'short', year: 'numeric' })}.</>}
            </div>
          )}

          {workflowMessage && <div className={styles.individualClubNotice}>{workflowMessage}</div>}
          {scheduleError && <div className={styles.individualClubError}>{scheduleError}</div>}

          <div className={styles.individualClubStatStrip}>
            <div className={styles.individualClubStatCard}>
              <div className={styles.individualClubStatLabel}>FORM (LAST 5)</div>
              <div className={styles.individualClubStatValue} style={{ fontSize: '1.4rem', letterSpacing: '0.1em' }}>
                {(club as any).recent_form ?? 'W W D W L'}
              </div>
              <div className={styles.individualClubStatSub}>
                {(club as any).recent_form_summary ?? '3 wins, 1 draw'}
              </div>
            </div>
            <div className={styles.individualClubStatCard}>
              <div className={styles.individualClubStatLabel}>ATTENDANCE</div>
              <div className={styles.individualClubStatValue}>{(club as any).attendance_rate ?? '87%'}</div>
              <div className={styles.individualClubStatSub}>{(club as any).attendance_trend ?? '+4% vs last month'}</div>
            </div>
            <div className={styles.individualClubStatCard}>
              <div className={styles.individualClubStatLabel}>SESSIONS THIS MONTH</div>
              <div className={styles.individualClubStatValue}>{(club as any).sessions_this_month ?? events.length}</div>
              <div className={styles.individualClubStatSub}>{(club as any).next_session ?? 'Next: Wed 19:30'}</div>
            </div>
            <div className={styles.individualClubStatCard}>
              <div className={styles.individualClubStatLabel}>GOALS SCORED</div>
              <div className={styles.individualClubStatValue}>{(club as any).goals_scored ?? 24}</div>
              <div className={styles.individualClubStatSub}>Conceded: {(club as any).goals_conceded ?? 11}</div>
            </div>
          </div>

          <div className={styles.individualClubBodyGrid}>

            <div className={styles.individualClubLeftCol}>

              <div className={styles.individualClubPanel}>
                <div className={styles.individualClubPanelHead}>
                  <h2 className={styles.individualClubPanelTitle}>Upcoming</h2>
                  <button className={styles.individualClubLinkBtn} onClick={() => navigate(`/clubs/${club.id}/fixtures`)}>
                    View all fixtures →
                  </button>
                </div>
                {scheduleLoading ? (
                  <p className={styles.individualClubBodyText}>Loading schedule…</p>
                ) : upcomingItems.length === 0 ? (
                  <p className={styles.individualClubBodyText}>No upcoming events or fixtures scheduled.</p>
                ) : (
                  <div className={styles.individualClubUpcomingList}>
                    {upcomingItems.map((item) => {
                      const isFixture = item.item_type === 'fixture';
                      const date = new Date(item.sort_datetime);
                      const dayName = date.toLocaleDateString('en-IE', { weekday: 'short' }).toUpperCase();
                      const dayNum = date.getDate();
                      const time = date.toLocaleTimeString('en-IE', { hour: '2-digit', minute: '2-digit' });
                      const competition = isFixture ? item.fixture?.competition ?? 'Fixture' : item.event?.event_type_display ?? 'Event';
                      const venue = isFixture ? item.fixture?.venue_display : item.event?.location;
                      const compColor = fixtureTypeColors[competition] ?? '#22c55e';
                      const summary = getScheduleItemSummary(item);
                      return (
                        <div key={`${item.item_type}-${isFixture ? item.fixture?.id : item.event?.id}`} className={styles.individualClubUpcomingRow}>
                          <div className={styles.individualClubUpcomingDate}>
                            <span className={styles.individualClubUpcomingDay}>{dayName}</span>
                            <span className={styles.individualClubUpcomingNum}>{dayNum}</span>
                          </div>
                          <div className={styles.individualClubUpcomingInfo}>
                            <div className={styles.individualClubUpcomingTitle}>
                              {item.calendar_label}
                              {competition && (
                                <span className={styles.individualClubUpcomingTag} style={{ background: `${compColor}22`, color: compColor, borderColor: `${compColor}44` }}>
                                  {competition}
                                </span>
                              )}
                              {venue && (
                                <span className={styles.individualClubUpcomingTag}>{venue}</span>
                              )}
                            </div>
                            <div className={styles.individualClubUpcomingMeta}>
                              {time}{item.item_type === 'event' && item.event?.location ? ` · ${item.event.location}` : ''}
                              {item.item_type === 'fixture' && item.fixture?.location ? ` · ${item.fixture.location}` : ''}
                              {summary && ` · ${summary}`}
                            </div>
                          </div>
                          <button className={styles.individualClubDetailsBtn}>Details</button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className={styles.individualClubPanel}>
                <div className={styles.individualClubPanelHead}>
                  <h2 className={styles.individualClubPanelTitle}>
                    Squad
                    <span className={styles.individualClubPanelCount}>
                      {squadPreview.length} SHOWN · {clubPlayers.length} TOTAL
                    </span>
                  </h2>
                  <button className={styles.individualClubLinkBtn} onClick={() => navigate(`/clubs/${club.id}/players`)}>
                    Full roster →
                  </button>
                </div>
                {clubPlayers.length === 0 ? (
                  <p className={styles.individualClubBodyText}>No players on the roster yet.</p>
                ) : (
                  <>
                    <div className={styles.individualClubSquadTableHead}>
                      <span>#</span>
                      <span>PLAYER</span>
                      <span>POSITION</span>
                      <span>AGE</span>
                      <span>FORM</span>
                      <span />
                    </div>
                    <div className={styles.individualClubSquadList}>
                      {squadPreview.map((player) => {
                        const playerInitials = player.full_name.split(' ').map((w) => w[0]?.toUpperCase() ?? '').slice(0, 2).join('');
                        return (
                          <div key={player.id} className={styles.individualClubSquadRow}>
                            <span className={styles.individualClubSquadNum}>{player.squad_number ?? '—'}</span>
                            <div className={styles.individualClubSquadPlayer}>
                              <div className={styles.individualClubSquadAvatar}>{playerInitials}</div>
                              <span className={styles.individualClubSquadName}>{player.full_name}</span>
                            </div>
                            <span className={styles.individualClubSquadPos}>{player.primary_position ?? '—'}</span>
                            <span className={styles.individualClubSquadAge}>{(player as any).age ?? '—'}</span>
                            <span className={styles.individualClubSquadForm}>
                              {(player as any).form_label ? (
                                <span className={`${styles.individualClubFormPill} ${
                                  (player as any).form_label === 'Hot' ? styles.individualClubFormHot :
                                  (player as any).form_label === 'Cool' ? styles.individualClubFormCool :
                                  styles.individualClubFormSteady
                                }`}>
                                  {(player as any).form_label === 'Hot' ? '↑' : (player as any).form_label === 'Cool' ? '↓' : '→'} {(player as any).form_label}
                                </span>
                              ) : '—'}
                            </span>
                            <button
                              className={styles.individualClubDetailsBtn}
                              onClick={() => navigate(`/clubs/${club.id}/players/${player.id}`)}
                            >
                              View
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>

              {!club.is_trashed && (
                <ClubResourcesSection club={club} isMember={isMember} canManageResources={reviewAccess} />
              )}

              {canAttemptSchedulingManagement && !club.is_trashed && (
                <>
                  <div className={styles.individualClubPanel}>
                    <div className={styles.individualClubPanelHead}>
                      <h2 className={styles.individualClubPanelTitle}>Club Events</h2>
                    </div>
                    <div className={styles.individualClubFormGrid}>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Title</label>
                        <input className={styles.individualClubInput} type="text" value={eventForm.title} onChange={(e) => setEventForm((p) => ({ ...p, title: e.target.value }))} placeholder="e.g. Tuesday analysis session" />
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Event type</label>
                        <select className={styles.individualClubSelect} value={eventForm.event_type} onChange={(e) => setEventForm((p) => ({ ...p, event_type: e.target.value as ClubEventType }))}>
                          {EVENT_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Start</label>
                        <input className={styles.individualClubInput} type="datetime-local" value={eventForm.start_datetime} onChange={(e) => setEventForm((p) => ({ ...p, start_datetime: e.target.value }))} />
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>End</label>
                        <input className={styles.individualClubInput} type="datetime-local" value={eventForm.end_datetime} onChange={(e) => setEventForm((p) => ({ ...p, end_datetime: e.target.value }))} />
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Location</label>
                        <input className={styles.individualClubInput} type="text" value={eventForm.location} onChange={(e) => setEventForm((p) => ({ ...p, location: e.target.value }))} placeholder="e.g. Main pitch" />
                      </div>
                    </div>
                    <textarea className={styles.individualClubTextarea} rows={3} value={eventForm.description} onChange={(e) => setEventForm((p) => ({ ...p, description: e.target.value }))} placeholder="Optional event details" />
                    <div className={styles.individualClubInlineActions}>
                      <label className={styles.individualClubCheckLabel}><input type="checkbox" checked={eventForm.is_all_day} onChange={(e) => setEventForm((p) => ({ ...p, is_all_day: e.target.checked }))} /> All day</label>
                      <label className={styles.individualClubCheckLabel}><input type="checkbox" checked={eventForm.is_mandatory} onChange={(e) => setEventForm((p) => ({ ...p, is_mandatory: e.target.checked }))} /> Mandatory</label>
                      <button className={styles.individualClubPrimaryBtn} type="button" disabled={!!loadingKey} onClick={handleEventSubmit}>
                        {editingEventId ? (loadingKey ? 'Saving…' : 'Save Event') : (loadingKey === 'create-event' ? 'Creating…' : 'Create Event')}
                      </button>
                      {editingEventId !== null && <button className={styles.individualClubGhostBtn} type="button" onClick={resetEventForm}>Cancel</button>}
                    </div>
                    <div className={styles.individualClubWorkflowList}>
                      {events.map((event) => (
                        <div key={event.id} className={styles.individualClubWorkflowCard}>
                          <div className={styles.individualClubWorkflowRow}>
                            <div>
                              <div className={styles.individualClubWorkflowTitle}>{event.title}</div>
                              <div className={styles.individualClubWorkflowMeta}>{event.event_type_display} · {formatDateTimeLabel(event.start_datetime)}</div>
                            </div>
                            <span className={styles.individualClubWorkflowTag}>{event.source_type_display}</span>
                          </div>
                          {event.location && <div className={styles.individualClubDetailNote}>Location: {event.location}</div>}
                          {event.is_user_editable && (
                            <div className={styles.individualClubInlineActions}>
                              <button className={styles.individualClubGhostBtn} onClick={() => handleEditEvent(event)}>Edit</button>
                              <button className={styles.individualClubGhostBtn} disabled={loadingKey === `delete-event-${event.id}`} onClick={() => handleDeleteEvent(event)}>
                                {loadingKey === `delete-event-${event.id}` ? 'Deleting…' : 'Delete'}
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className={styles.individualClubPanel}>
                    <div className={styles.individualClubPanelHead}>
                      <h2 className={styles.individualClubPanelTitle}>Fixtures</h2>
                    </div>
                    <div className={styles.individualClubFormGrid}>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Opponent</label>
                        <input className={styles.individualClubInput} type="text" value={fixtureForm.opponent_name} onChange={(e) => setFixtureForm((p) => ({ ...p, opponent_name: e.target.value }))} placeholder="e.g. Dublin City FC" />
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Venue</label>
                        <select className={styles.individualClubSelect} value={fixtureForm.venue} onChange={(e) => setFixtureForm((p) => ({ ...p, venue: e.target.value as FixtureVenue }))}>
                          {FIXTURE_VENUE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Competition</label>
                        <input className={styles.individualClubInput} type="text" value={fixtureForm.competition} onChange={(e) => setFixtureForm((p) => ({ ...p, competition: e.target.value }))} placeholder="e.g. League" />
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Status</label>
                        <select className={styles.individualClubSelect} value={fixtureForm.fixture_status} onChange={(e) => setFixtureForm((p) => ({ ...p, fixture_status: e.target.value as FixtureStatus }))}>
                          {FIXTURE_STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Date &amp; time</label>
                        <input className={styles.individualClubInput} type="datetime-local" value={fixtureForm.match_datetime} onChange={(e) => setFixtureForm((p) => ({ ...p, match_datetime: e.target.value }))} />
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Location</label>
                        <input className={styles.individualClubInput} type="text" value={fixtureForm.location} onChange={(e) => setFixtureForm((p) => ({ ...p, location: e.target.value }))} placeholder="e.g. Main ground" />
                      </div>
                    </div>
                    <div className={styles.individualClubInlineActions}>
                      <button className={styles.individualClubPrimaryBtn} type="button" disabled={!!loadingKey} onClick={handleFixtureSubmit}>
                        {editingFixtureId ? (loadingKey ? 'Saving…' : 'Save Fixture') : (loadingKey === 'create-fixture' ? 'Creating…' : 'Create Fixture')}
                      </button>
                      {editingFixtureId !== null && <button className={styles.individualClubGhostBtn} type="button" onClick={resetFixtureForm}>Cancel</button>}
                    </div>
                    <div className={styles.individualClubWorkflowList}>
                      {fixtures.map((fixture) => (
                        <div key={fixture.id} className={styles.individualClubWorkflowCard}>
                          <div className={styles.individualClubWorkflowRow}>
                            <div>
                              <div className={styles.individualClubWorkflowTitle}>{fixture.calendar_label}</div>
                              <div className={styles.individualClubWorkflowMeta}>{fixture.competition || 'Fixture'} · {formatDateTimeLabel(fixture.match_datetime)}</div>
                            </div>
                            <span className={styles.individualClubWorkflowTag}>{fixture.source_type_display}</span>
                          </div>
                          <div className={styles.individualClubDetailNote}>Venue: {fixture.venue_display} · Status: {fixture.fixture_status_display}</div>
                          {fixture.is_user_editable && (
                            <div className={styles.individualClubInlineActions}>
                              <button className={styles.individualClubGhostBtn} onClick={() => handleEditFixture(fixture)}>Edit</button>
                              <button className={styles.individualClubGhostBtn} disabled={loadingKey === `delete-fixture-${fixture.id}`} onClick={() => handleDeleteFixture(fixture)}>
                                {loadingKey === `delete-fixture-${fixture.id}` ? 'Deleting…' : 'Delete'}
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className={styles.individualClubRightCol}>

              <div className={styles.individualClubPanel}>
                <ClubCalendar calendarItems={calendarFeed} />
              </div>

              <div className={styles.individualClubPanel}>
                <div className={styles.individualClubPanelHead}>
                  <h2 className={styles.individualClubPanelTitle}>Quick actions</h2>
                </div>
                <div className={styles.individualClubWorkflowList}>
                  {QUICK_ACTIONS.map((action) => (
                    <button
                      key={action.key}
                      type="button"
                      className={styles.individualClubGhostBtn}
                      onClick={() => navigate(action.path(club.id))}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%', textAlign: 'left', marginBottom: '0.4rem' }}
                    >
                      {action.icon}
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{action.title}</div>
                        <div style={{ color: '#888', fontSize: '0.75rem' }}>{action.desc}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {reviewAccess && !club.is_trashed && (
                <div className={styles.individualClubPanel}>
                  <div className={styles.individualClubPanelHead}>
                    <h2 className={styles.individualClubPanelTitle}>Join requests</h2>
                    {pendingRequests.length > 0 && (
                      <span className={styles.individualClubBadgePill}>{pendingRequests.length} new</span>
                    )}
                  </div>

                  {reviewJoinRequests.length === 0 ? (
                    <p className={styles.individualClubBodyText}>No join requests yet.</p>
                  ) : (
                    <div className={styles.individualClubRequestList}>
                      {reviewJoinRequests.map((request) => (
                        <div key={request.id}>
                          <div className={styles.individualClubRequestRow}>
                            <div className={styles.individualClubRequestAvatar}>
                              {(request.user_email ?? '?')[0].toUpperCase()}
                            </div>
                            <div className={styles.individualClubRequestInfo}>
                              <div className={styles.individualClubRequestName}>{request.user_email}</div>
                              <div className={styles.individualClubRequestMeta}>
                                {request.requested_role} · {getRequestStatusLabel(request.status)}
                              </div>
                            </div>
                            {request.status === 'pending' && (
                              <div className={styles.individualClubRequestActions}>
                                <button
                                  className={styles.individualClubDeclineBtn}
                                  disabled={loadingKey === `reject-${request.id}`}
                                  onClick={() => handleRejectRequest(request)}
                                >
                                  Decline
                                </button>
                                <button
                                  className={styles.individualClubApproveBtn}
                                  disabled={loadingKey === `approve-${request.id}`}
                                  onClick={() => handleApproveRequest(request)}
                                >
                                  {loadingKey === `approve-${request.id}` ? 'Approving…' : 'Approve'}
                                </button>
                              </div>
                            )}
                          </div>
                          {request.status === 'pending' && (
                            <div className={styles.individualClubFormGrid} style={{ marginTop: '0.4rem', paddingLeft: '2.5rem' }}>
                              {availableRosterLinks.length > 0 && (
                                <div className={styles.individualClubFormField}>
                                  <label className={styles.individualClubFormLabel}>Link to roster slot (optional)</label>
                                  <select
                                    className={styles.individualClubSelect}
                                    value={selectedClubPlayerByRequest[request.id] ?? ''}
                                    onChange={(e) => setSelectedClubPlayerByRequest((prev) => ({ ...prev, [request.id]: e.target.value }))}
                                  >
                                    <option value="">No link</option>
                                    {availableRosterLinks.map((p) => (
                                      <option key={p.id} value={String(p.id)}>{p.full_name}</option>
                                    ))}
                                  </select>
                                </div>
                              )}
                              <div className={styles.individualClubFormField}>
                                <label className={styles.individualClubFormLabel}>Review note</label>
                                <input
                                  className={styles.individualClubInput}
                                  type="text"
                                  placeholder="Optional note for the applicant"
                                  value={reviewNoteByRequest[request.id] ?? ''}
                                  onChange={(e) => setReviewNoteByRequest((prev) => ({ ...prev, [request.id]: e.target.value }))}
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className={styles.individualClubInviteForm}>
                    <div className={styles.individualClubPanelHead} style={{ marginBottom: '0.65rem' }}>
                      <h3 className={styles.individualClubPanelTitle} style={{ fontSize: '0.85rem' }}>Send invitation</h3>
                    </div>
                    <div className={styles.individualClubFormGrid}>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Email</label>
                        <input className={styles.individualClubInput} type="email" value={inviteEmailInput} onChange={(e) => setInviteEmailInput(e.target.value)} placeholder="user@example.com" />
                      </div>
                      <div className={styles.individualClubFormField}>
                        <label className={styles.individualClubFormLabel}>Role</label>
                        <select className={styles.individualClubSelect} value={inviteRole} onChange={(e) => setInviteRole(e.target.value as Exclude<ClubMembershipRole, 'owner'>)}>
                          {STAFF_INVITE_ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                        </select>
                      </div>
                    </div>
                    <button className={styles.individualClubPrimaryBtn} style={{ width: '100%', marginTop: '0.5rem' }} type="button" disabled={loadingKey === 'create-invitation'} onClick={handleCreateInvitation}>
                      {loadingKey === 'create-invitation' ? 'Sending…' : 'Send Invitation'}
                    </button>
                  </div>
                </div>
              )}

              {reviewAccess && !club.is_trashed && reviewInvitations.length > 0 && (
                <div className={styles.individualClubPanel}>
                  <div className={styles.individualClubPanelHead}>
                    <h2 className={styles.individualClubPanelTitle}>Invitations sent</h2>
                  </div>
                  <div className={styles.individualClubWorkflowList}>
                    {reviewInvitations.map((invitation) => (
                      <div key={invitation.id} className={styles.individualClubWorkflowCard}>
                        <div className={styles.individualClubWorkflowRow}>
                          <div>
                            <div className={styles.individualClubWorkflowTitle}>{invitation.invited_user_email}</div>
                            <div className={styles.individualClubWorkflowMeta}>
                              {invitation.invited_role} · {getInvitationStatusLabel(invitation.status)}
                            </div>
                          </div>
                        </div>
                        {invitation.status === 'pending' && (
                          <div className={styles.individualClubInlineActions}>
                            <input
                              className={styles.individualClubInput}
                              type="text"
                              placeholder="Revoke note (optional)"
                              value={revokeNoteByInvitation[invitation.id] ?? ''}
                              onChange={(e) => setRevokeNoteByInvitation((prev) => ({ ...prev, [invitation.id]: e.target.value }))}
                            />
                            <button
                              className={styles.individualClubGhostBtn}
                              disabled={loadingKey === `revoke-${invitation.id}`}
                              onClick={() => handleRevokeInvitation(invitation)}
                            >
                              {loadingKey === `revoke-${invitation.id}` ? 'Revoking…' : 'Revoke'}
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!club.is_trashed && !isMember && requestCanBeSubmitted && (
                <div className={styles.individualClubPanel}>
                  <h2 className={styles.individualClubPanelTitle} style={{ marginBottom: '0.75rem' }}>Join this club</h2>
                  <textarea className={styles.individualClubTextarea} value={requestMessage} onChange={(e) => setRequestMessage(e.target.value)} placeholder="Optional note to the reviewer" rows={3} />
                  <button className={styles.individualClubPrimaryBtn} style={{ marginTop: '0.6rem', width: '100%' }} type="button" disabled={loadingKey === `request-${club.id}`} onClick={handleRequestToJoin}>
                    {loadingKey === `request-${club.id}` ? 'Submitting…' : 'Request to Join'}
                  </button>
                </div>
              )}

            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
