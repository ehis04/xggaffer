import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { teamsheetApi } from '../../../services/api';
import type { TeamsheetListItem } from '../../../types/teamsheet';
import { getTeamsheetStatus } from '../../../utils/teamsheetStatus';
import styles from './css/TeamsheetListPage.module.css';
import { useAuth } from '../../../context/useAuth';
import { Sidebar } from '../../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';
import { CoachingNavBar } from '../../../components/Navigation/CoachingNavBar';

const TeamsheetListPage: React.FC = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const currentUserId = typeof user?.id === 'number' ? user.id : null;

  const [teamsheets, setTeamsheets] = useState<TeamsheetListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  const activeView = searchParams.get('view') === 'trash' ? 'trash' : 'active';
  const isTrashView = activeView === 'trash';

  const fetchTeamsheets = useCallback(async () => {
    if (!clubId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await teamsheetApi.list(Number(clubId), {
        ...(isTrashView ? { trash: 'only' } : {}),
      });
      setTeamsheets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load teamsheets');
    } finally {
      setLoading(false);
    }
  }, [clubId, isTrashView]);

  useEffect(() => { void fetchTeamsheets(); }, [fetchTeamsheets]);

  const templates = useMemo(() => teamsheets.filter((t) => t.is_template), [teamsheets]);
  const matches   = useMemo(() => teamsheets.filter((t) => !t.is_template), [teamsheets]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'No date';
    return new Date(dateStr).toLocaleDateString('en-IE', { day: 'numeric', month: 'short' });
  };

  const formatExpiry = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('en-IE', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const openTeamsheet = (teamsheet: TeamsheetListItem) => {
    const suffix = teamsheet.is_trashed ? '?view=trash' : '';
    navigate(`/clubs/${clubId}/teamsheets/${teamsheet.id}${suffix}`);
  };

  const setView = (view: 'active' | 'trash') => {
    setActionError(null);
    view === 'trash' ? setSearchParams({ view: 'trash' }) : setSearchParams({});
  };

  const handleMoveToTrash = async (teamsheetId: number) => {
    if (!clubId || !window.confirm('Move this teamsheet to trash?')) return;
    try {
      setActionLoadingId(teamsheetId); setActionError(null);
      await teamsheetApi.trash(Number(clubId), teamsheetId);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to move teamsheet to trash.');
    } finally { setActionLoadingId(null); }
  };

  const handleRestore = async (teamsheetId: number) => {
    if (!clubId) return;
    try {
      setActionLoadingId(teamsheetId); setActionError(null);
      await teamsheetApi.restore(Number(clubId), teamsheetId);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to restore teamsheet.');
    } finally { setActionLoadingId(null); }
  };

  const handlePermanentDelete = async (teamsheetId: number) => {
    if (!clubId || !window.confirm('Delete this teamsheet permanently? This cannot be undone.')) return;
    try {
      setActionLoadingId(teamsheetId); setActionError(null);
      await teamsheetApi.permanentDelete(Number(clubId), teamsheetId);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to permanently delete teamsheet.');
    } finally { setActionLoadingId(null); }
  };

  const renderCard = (teamsheet: TeamsheetListItem) => {
    const status = getTeamsheetStatus(teamsheet.starter_count, teamsheet.match_date);
    const isBusy = actionLoadingId === teamsheet.id;
    const canManageTrash = teamsheet.created_by === currentUserId;

    return (
      <article
        key={teamsheet.id}
        className={styles.TSLCard}
        onClick={() => openTeamsheet(teamsheet)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openTeamsheet(teamsheet); }
        }}
      >
        <div className={styles.TSLCardTop}>
          <span className={styles.TSLFormation}>{teamsheet.formation_display}</span>
          {teamsheet.is_template ? (
            <span className={styles.TSLTemplateBadge}>Template</span>
          ) : teamsheet.match_date ? (
            <span className={styles.TSLDate}>{formatDate(teamsheet.match_date)}</span>
          ) : null}
        </div>

        <h3 className={styles.TSLCardTitle}>{teamsheet.title}</h3>
        {teamsheet.opponent && (
          <p className={styles.TSLOpponent}>vs {teamsheet.opponent}</p>
        )}

        <div className={styles.TSLCardMeta}>
          <span className={`${styles.TSLStatus} ${styles[`TSLStatus_${status.key}`] ?? ''}`}>
            {status.label}
          </span>
        </div>

        {teamsheet.is_trashed && teamsheet.trash_expires_at && (
          <p className={styles.TSLTrashNotice}>
            In trash until {formatExpiry(teamsheet.trash_expires_at)}
          </p>
        )}

        <div className={styles.TSLCardActions} onClick={(e) => e.stopPropagation()}>
          {!teamsheet.is_trashed ? (
            canManageTrash && (
              <button
                type="button"
                className={styles.TSLGhostBtn}
                disabled={isBusy}
                onClick={() => void handleMoveToTrash(teamsheet.id)}
              >
                {isBusy ? 'Moving…' : 'Move to Trash'}
              </button>
            )
          ) : canManageTrash ? (
            <>
              <button
                type="button"
                className={styles.TSLRestoreBtn}
                disabled={isBusy}
                onClick={() => void handleRestore(teamsheet.id)}
              >
                {isBusy ? 'Restoring…' : 'Restore'}
              </button>
              <button
                type="button"
                className={styles.TSLDangerBtn}
                disabled={isBusy}
                onClick={() => void handlePermanentDelete(teamsheet.id)}
              >
                {isBusy ? 'Deleting…' : 'Delete Permanently'}
              </button>
            </>
          ) : null}
        </div>
      </article>
    );
  };

  return (
    <div className={styles.TSLShell}>
      <div className="sidebar-section"><Sidebar /></div>

      <div className={styles.TSLMain}>

        <header className={styles.TSLHeader}>
          <div className={styles.TSLHeaderLeft}>
            <span className={styles.TSLHeaderLabel}>Coaching</span>
            <span className={styles.TSLHeaderSep}>·</span>
            <span className={styles.TSLHeaderTitle}>Teamsheets</span>
          </div>
          <div className={styles.TSLHeaderMiddle}><CoachingNavBar /></div>
          <div className={styles.TSLHeaderRight}><SocialUserButtons /></div>
        </header>

        <div className={styles.TSLContent}>

          <div className={styles.TSLPageHead}>
            <div>
              <h1 className={styles.TSLPageTitle}>Teamsheets</h1>
              <p className={styles.TSLPageSub}>
                {isTrashView
                  ? 'Restore deleted teamsheets or remove them permanently.'
                  : 'Create and manage active match teamsheets and templates.'}
              </p>
            </div>
            <div className={styles.TSLPageHeadRight}>
              <div className={styles.TSLTabs}>
                <button
                  type="button"
                  className={`${styles.TSLTab} ${!isTrashView ? styles.TSLTabActive : ''}`}
                  onClick={() => setView('active')}
                >Active</button>
                <button
                  type="button"
                  className={`${styles.TSLTab} ${isTrashView ? styles.TSLTabActive : ''}`}
                  onClick={() => setView('trash')}
                >Trash</button>
              </div>
              {!isTrashView && (
                <Link to={`/clubs/${clubId}/teamsheets/new`} className={styles.TSLCreateBtn}>
                  + New Teamsheet
                </Link>
              )}
            </div>
          </div>

          {error       && <div className={styles.TSLError}>{error}</div>}
          {actionError && <div className={styles.TSLError}>{actionError}</div>}

          {loading ? (
            <div className={styles.TSLLoading}>Loading teamsheets…</div>
          ) : isTrashView ? (
            <section className={styles.TSLSection}>
              <h2 className={styles.TSLSectionTitle}>Trashed Teamsheets</h2>
              {teamsheets.length === 0 ? (
                <div className={styles.TSLEmpty}><p>No teamsheets in trash.</p></div>
              ) : (
                <div className={styles.TSLGrid}>{teamsheets.map(renderCard)}</div>
              )}
            </section>
          ) : (
            <>
              {templates.length > 0 && (
                <section className={styles.TSLSection}>
                  <h2 className={styles.TSLSectionTitle}>Templates</h2>
                  <div className={styles.TSLGrid}>{templates.map(renderCard)}</div>
                </section>
              )}

              <section className={styles.TSLSection}>
                <h2 className={styles.TSLSectionTitle}>Match Teamsheets</h2>
                {matches.length === 0 ? (
                  <div className={styles.TSLEmpty}>
                    <p>No match teamsheets yet.</p>
                    <Link to={`/clubs/${clubId}/teamsheets/new`} className={styles.TSLEmptyLink}>
                      Create your first teamsheet →
                    </Link>
                  </div>
                ) : (
                  <div className={styles.TSLGrid}>{matches.map(renderCard)}</div>
                )}
              </section>
            </>
          )}

        </div>
      </div>
    </div>
  );
};

export default TeamsheetListPage;