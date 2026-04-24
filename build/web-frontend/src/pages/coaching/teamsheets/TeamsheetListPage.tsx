import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { teamsheetApi } from '../../../services/api';
import type { TeamsheetListItem } from '../../../types/teamsheet';
import { getTeamsheetStatus } from '../../../utils/teamsheetStatus';
import styles from './css/TeamsheetListPage.module.css';
import { useAuth } from '../../../context/useAuth';

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

  useEffect(() => {
    void fetchTeamsheets();
  }, [fetchTeamsheets]);

  const templates = useMemo(
    () => teamsheets.filter((teamsheet) => teamsheet.is_template),
    [teamsheets]
  );

  const matches = useMemo(
    () => teamsheets.filter((teamsheet) => !teamsheet.is_template),
    [teamsheets]
  );

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'No date';
    return new Date(dateStr).toLocaleDateString('en-IE', {
      day: 'numeric',
      month: 'short',
    });
  };

  const formatExpiry = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('en-IE', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  const openTeamsheet = (teamsheet: TeamsheetListItem) => {
    const suffix = teamsheet.is_trashed ? '?view=trash' : '';
    navigate(`/clubs/${clubId}/teamsheets/${teamsheet.id}${suffix}`);
  };

  const setView = (view: 'active' | 'trash') => {
    setActionError(null);
    if (view === 'trash') {
      setSearchParams({ view: 'trash' });
      return;
    }
    setSearchParams({});
  };

  const handleMoveToTrash = async (teamsheetId: number) => {
    if (!clubId) return;

    const confirmed = window.confirm('Move this teamsheet to trash?');
    if (!confirmed) return;

    try {
      setActionLoadingId(teamsheetId);
      setActionError(null);
      await teamsheetApi.trash(Number(clubId), teamsheetId);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to move teamsheet to trash.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRestore = async (teamsheetId: number) => {
    if (!clubId) return;

    try {
      setActionLoadingId(teamsheetId);
      setActionError(null);
      await teamsheetApi.restore(Number(clubId), teamsheetId);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to restore teamsheet.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handlePermanentDelete = async (teamsheetId: number) => {
    if (!clubId) return;

    const confirmed = window.confirm(
      'Delete this teamsheet permanently? This cannot be undone.'
    );
    if (!confirmed) return;

    try {
      setActionLoadingId(teamsheetId);
      setActionError(null);
      await teamsheetApi.permanentDelete(Number(clubId), teamsheetId);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : 'Failed to permanently delete teamsheet.'
      );
    } finally {
      setActionLoadingId(null);
    }
  };

  const renderCard = (teamsheet: TeamsheetListItem) => {
    const status = getTeamsheetStatus(teamsheet.starter_count, teamsheet.match_date);
    const isBusy = actionLoadingId === teamsheet.id;
    const canManageTrash = teamsheet.created_by === currentUserId;

    return (
      <article
        key={teamsheet.id}
        className={styles.card}
        onClick={() => openTeamsheet(teamsheet)}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openTeamsheet(teamsheet);
          }
        }}
      >
        <div className={styles.cardHeader}>
          <span className={styles.formation}>{teamsheet.formation_display}</span>
          {teamsheet.is_template ? (
            <span className={styles.templateBadge}>Template</span>
          ) : teamsheet.match_date ? (
            <span className={styles.date}>{formatDate(teamsheet.match_date)}</span>
          ) : null}
        </div>

        <h3 className={styles.cardTitle}>{teamsheet.title}</h3>

        {teamsheet.opponent && (
          <p className={styles.opponent}>vs {teamsheet.opponent}</p>
        )}

        <div className={styles.cardMeta}>
          <span className={styles[status.key]}>{status.label}</span>
        </div>

        {teamsheet.is_trashed && teamsheet.trash_expires_at && (
          <p className={styles.trashNotice}>
            In trash until {formatExpiry(teamsheet.trash_expires_at)}
          </p>
        )}

        <div className={styles.cardActions}>
          {!teamsheet.is_trashed ? (
            canManageTrash ? (
              <button
                type="button"
                className={styles.ghostButton}
                disabled={isBusy}
                onClick={(event) => {
                  event.stopPropagation();
                  void handleMoveToTrash(teamsheet.id);
                }}
              >
                {isBusy ? 'Moving...' : 'Move to Trash'}
              </button>
            ) : null
          ) : canManageTrash ? (
            <>
              <button
                type="button"
                className={styles.restoreButton}
                disabled={isBusy}
                onClick={(event) => {
                  event.stopPropagation();
                  void handleRestore(teamsheet.id);
                }}
              >
                {isBusy ? 'Restoring...' : 'Restore'}
              </button>

              <button
                type="button"
                className={styles.dangerButton}
                disabled={isBusy}
                onClick={(event) => {
                  event.stopPropagation();
                  void handlePermanentDelete(teamsheet.id);
                }}
              >
                {isBusy ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </>
          ) : null}
        </div>
      </article>
    );
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading teamsheets...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>{error}</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Teamsheets</h1>
          <p className={styles.sectionCopy}>
            {isTrashView
              ? 'Restore deleted teamsheets or remove them permanently.'
              : 'Create and manage active match teamsheets and templates.'}
          </p>
        </div>

        <div className={styles.headerActions}>
          <div className={styles.tabs}>
            <button
              type="button"
              className={`${styles.tab} ${!isTrashView ? styles.tabActive : ''}`}
              onClick={() => setView('active')}
            >
              Active
            </button>
            <button
              type="button"
              className={`${styles.tab} ${isTrashView ? styles.tabActive : ''}`}
              onClick={() => setView('trash')}
            >
              Trash
            </button>
          </div>

          {!isTrashView && (
            <Link to={`/clubs/${clubId}/teamsheets/new`} className={styles.createButton}>
              + New Teamsheet
            </Link>
          )}
        </div>
      </div>

      {actionError && <div className={styles.error}>{actionError}</div>}

      {isTrashView ? (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Trashed Teamsheets</h2>
          {teamsheets.length === 0 ? (
            <div className={styles.empty}>
              <p>No teamsheets in trash.</p>
            </div>
          ) : (
            <div className={styles.grid}>{teamsheets.map(renderCard)}</div>
          )}
        </section>
      ) : (
        <>
          {templates.length > 0 && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Templates</h2>
              <div className={styles.grid}>{templates.map(renderCard)}</div>
            </section>
          )}

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Match Teamsheets</h2>
            {matches.length === 0 ? (
              <div className={styles.empty}>
                <p>No match teamsheets yet.</p>
                <Link to={`/clubs/${clubId}/teamsheets/new`} className={styles.emptyLink}>
                  Create your first teamsheet
                </Link>
              </div>
            ) : (
              <div className={styles.grid}>{matches.map(renderCard)}</div>
            )}
          </section>
        </>
      )}
    </div>
  );
};

export default TeamsheetListPage;