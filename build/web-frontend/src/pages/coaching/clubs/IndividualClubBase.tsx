import { useEffect, useState, lazy, Suspense, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { clubsApi } from '../../../services/api';
import { Sidebar } from '../../../components/Navigation/SideBar';
import { CoachingNavBar } from '../../../components/Navigation/CoachingNavBar';
import type { ClubTab } from '../../../components/Navigation/CoachingNavBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';
import { useAuth } from '../../../context/useAuth';
import type {
  Club,
  ClubInvitation,
  ClubJoinRequest,
  ClubMembershipRole,
} from '../../../types/club';
import type { ClubPlayer } from '../../../types/clubPlayers';
import styles from './css/IndividualClubBase.module.css';
import { AppError } from '../../../common/AppError';
import { FullPageLoader } from '../../../common/components/FullPageLoader';
import { StatusBlock } from '../../../common/components/StatusBlock';
import { ResourceNotFoundPage } from '../../status/ResourceNotFoundpage';

const DashboardTab  = lazy(() => import('./tabs/DashboardTab'));
const PlayersTab    = lazy(() => import('./tabs/PlayersTab'));
const FormationsTab = lazy(() => import('./tabs/FormationsTab'));
const ScheduleTab   = lazy(() => import('./tabs/ScheduleTab'));
const SeasonTab     = lazy(() => import('./tabs/SeasonTab'));
const MembersTab    = lazy(() => import('./tabs/MembersTab'));
const TacticsTab    = lazy(() => import('./tabs/TacticsTab'));

export interface ClubContext {
  club: Club;
  clubId: number;
  myRole: ClubMembershipRole | null;
  isMember: boolean;
  canManage: boolean;
  isOwner: boolean;
  isTrashView: boolean;
  myJoinRequests: ClubJoinRequest[];
  reviewJoinRequests: ClubJoinRequest[];
  reviewInvitations: ClubInvitation[];
  clubPlayers: ClubPlayer[];
  reviewAccess: boolean;
  onClubUpdate: (updated: Club) => void;
  reloadWorkflowData: () => Promise<void>;
}

const resolveMyRole = (
  myClubIds: number[],
  clubId: number,
  reviewAccess: boolean,
  club: Club,
  userId: number | undefined,
): ClubMembershipRole | null => {
  if (!myClubIds.includes(clubId)) return null;
  if (userId !== undefined && club.creator === userId) return 'owner';
  if (reviewAccess) return 'coach';
  return 'player';
};

export const fixtureTypeColors: Record<string, string> = {
  League: '#3b82f6', Cup: '#a78bfa', Friendly: '#f59e0b', Training: '#22c55e',
};

export const IndividualClubBase = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  const numericClubId = Number(clubId);
  const isTrashView = searchParams.get('view') === 'trash';

  const [club, setClub]                 = useState<Club | null>(null);
  const [myClubIds, setMyClubIds]       = useState<number[]>([]);
  const [reviewAccess, setReviewAccess] = useState(false);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<AppError | null>(null);

  const [myJoinRequests, setMyJoinRequests]         = useState<ClubJoinRequest[]>([]);
  const [reviewJoinRequests, setReviewJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [reviewInvitations, setReviewInvitations]   = useState<ClubInvitation[]>([]);
  const [clubPlayers, setClubPlayers]               = useState<ClubPlayer[]>([]);

  const loadWorkflowData = useCallback(async (clubRecord: Club) => {
    const myRequestsPromise = clubsApi.listMyJoinRequests();
    const myClubsPromise    = clubsApi.myClubs();

    let reviewerRequests: ClubJoinRequest[]   = [];
    let reviewerInvitations: ClubInvitation[] = [];
    let players: ClubPlayer[]                 = [];
    let hasReviewAccess = false;

    try {
      reviewerRequests    = await clubsApi.listClubJoinRequests(clubRecord.id);
      reviewerInvitations = await clubsApi.listClubInvitations(clubRecord.id);
      players             = await clubsApi.listPlayers(clubRecord.id);
      hasReviewAccess     = true;
    } catch {
      hasReviewAccess = false;
    }

    const [myRequestsData, myClubsData] = await Promise.all([myRequestsPromise, myClubsPromise]);

    setMyJoinRequests(myRequestsData);
    setMyClubIds(myClubsData.map(c => c.id));
    setReviewJoinRequests(reviewerRequests);
    setReviewInvitations(reviewerInvitations);
    setClubPlayers(players);
    setReviewAccess(hasReviewAccess);
  }, []);

  const fetchClub = useCallback(async () => {
    if (!Number.isFinite(numericClubId)) return;
    try {
      setLoading(true);
      setError(null);
      const clubData = await clubsApi.get(
        numericClubId,
        isTrashView ? { trash: 'only' } : undefined,
      );
      setClub(clubData);
      await loadWorkflowData(clubData);
    } catch (err) {
      setError(err instanceof AppError ? err : new AppError(0, 'UNKNOWN', 'Failed to load club.'));
    } finally {
      setLoading(false);
    }
  }, [numericClubId, isTrashView, loadWorkflowData]);

  useEffect(() => { void fetchClub(); }, [fetchClub]);

  const handleClubUpdate = (updated: Club) => setClub(updated);

  const reloadWorkflowData = useCallback(async () => {
    if (club) await loadWorkflowData(club);
  }, [club, loadWorkflowData]);

  if (loading) return <FullPageLoader label="Loading club" />;

  if (error?.code === 'NOT_FOUND' || !club) {
    return (
      <ResourceNotFoundPage backPath="/clubs" backLabel="Back to Clubs" />
    );
  }

  if (error) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.sidebarSection}><Sidebar /></div>
        <div className={styles.pageBody}>
          <StatusBlock
            variant="error"
            message={error.detail}
            actions={
              <button type="button" className={styles.retryButton} onClick={fetchClub}>
                Retry
              </button>
            }
          />
        </div>
      </div>
    );
  }

  const isMember  = myClubIds.includes(club.id);
  const isOwner   = typeof user?.id === 'number' && club.creator === user.id;
  const canManage = isMember && (isOwner || reviewAccess);
  const myRole    = resolveMyRole(myClubIds, club.id, reviewAccess, club, user?.id);

  const ctx: ClubContext = {
    club, clubId: numericClubId, myRole, isMember, canManage, isOwner, isTrashView,
    myJoinRequests, reviewJoinRequests, reviewInvitations, clubPlayers, reviewAccess,
    onClubUpdate: handleClubUpdate, reloadWorkflowData,
  };

  const activeTab = (searchParams.get('tab') as ClubTab) ?? 'dashboard';

  const renderTab = () => {
    switch (activeTab) {
      case 'players':    return <PlayersTab    ctx={ctx} />;
      case 'formations': return <FormationsTab ctx={ctx} />;
      case 'schedule':   return <ScheduleTab   ctx={ctx} />;
      case 'season':     return <SeasonTab     ctx={ctx} />;
      case 'members':    return <MembersTab    ctx={ctx} />;
      case 'tactics':    return <TacticsTab    ctx={ctx} />;
      default:           return <DashboardTab  ctx={ctx} />;
    }
  };

  return (
    <div className={styles.pageContainer}>
      <div className={styles.sidebarSection}>
        <Sidebar />
      </div>

      <div className={styles.pageBody}>
        <header className={styles.pageHeader}>
          <div className={styles.headerLeft}>
            <button
              type="button"
              className={styles.backButton}
              onClick={() => navigate('/clubs')}
            >
              ←
            </button>
          </div>

          <div className={styles.headerCenter}>
            <CoachingNavBar />
          </div>

          <div className={styles.headerRight}>
            <SocialUserButtons />
          </div>
        </header>

        <main className={styles.pageContent}>
          <Suspense fallback={<div className={styles.tabLoading}>Loading...</div>}>
            {renderTab()}
          </Suspense>
        </main>
      </div>
    </div>
  );
};

export default IndividualClubBase;