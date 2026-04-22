import { useEffect, useState, lazy, Suspense } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { clubsApi } from '../../../services/api';
import { Sidebar } from '../../../components/Navigation/SideBar';
import { CoachingNavBar } from '../../../components/Navigation/CoachingNavBar';
import type { ClubTab } from '../../../components/Navigation/CoachingNavBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';
import { useAuth } from '../../../context/useAuth';
import type { Club, ClubMembershipRole } from '../../../types/club';
import styles from './css/IndividualClubBase.module.css';

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
  onClubUpdate: (updated: Club) => void;
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

export const IndividualClubBase = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  const numericClubId = Number(clubId);
  const isTrashView = searchParams.get('view') === 'trash';

  const [club, setClub] = useState<Club | null>(null);
  const [myClubIds, setMyClubIds] = useState<number[]>([]);
  const [reviewAccess, setReviewAccess] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(numericClubId)) return;

    const fetchClub = async () => {
      try {
        setLoading(true);
        setError(null);

        const [clubData, myClubsData] = await Promise.all([
          clubsApi.get(numericClubId, isTrashView ? { trash: 'only' } : undefined),
          clubsApi.myClubs(),
        ]);

        setClub(clubData);
        setMyClubIds(myClubsData.map((c) => c.id));

        try {
          await clubsApi.listClubJoinRequests(clubData.id);
          setReviewAccess(true);
        } catch {
          setReviewAccess(false);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load club.');
      } finally {
        setLoading(false);
      }
    };

    void fetchClub();
  }, [numericClubId, isTrashView]);

  const handleClubUpdate = (updated: Club) => setClub(updated);

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.sidebarSection}>
          <Sidebar />
        </div>
        <div className={styles.pageBody}>
          <div className={styles.loadingState}>Loading club...</div>
        </div>
      </div>
    );
  }

  if (error || !club) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.sidebarSection}>
          <Sidebar />
        </div>
        <div className={styles.pageBody}>
          <div className={styles.errorState}>
            {error ?? 'Club not found.'}
            <button
              type="button"
              className={styles.backButton}
              onClick={() => navigate('/clubs')}
            >
              Back to clubs
            </button>
          </div>
        </div>
      </div>
    );
  }

  const isMember = myClubIds.includes(club.id);
  const isOwner = typeof user?.id === 'number' && club.creator === user.id;
  const canManage = isMember && (isOwner || reviewAccess);

  const myRole = resolveMyRole(myClubIds, club.id, reviewAccess, club, user?.id);

  const ctx: ClubContext = {
    club,
    clubId: numericClubId,
    myRole,
    isMember,
    canManage,
    isOwner,
    isTrashView,
    onClubUpdate: handleClubUpdate,
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
              className={styles.clubNameButton}
              onClick={() => navigate('/clubs')}
            >
              ← {club.name}
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