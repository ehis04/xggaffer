import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { teamsheetApi } from '../../../../services/api';
import { useAuth } from '../../../../context/useAuth';
import { getTeamsheetStatus } from '../../../../utils/teamsheetStatus';
import type { TeamsheetListItem } from '../../../../types/teamsheet';
import type { ClubContext } from '../IndividualClubBase';
import styles from './css/FormationsTab.module.css';

interface Props {
  ctx: ClubContext;
}

type SubView = 'active' | 'trash';

const formatDate = (v: string | null): string => {
  if (!v) return 'No date';
  return new Date(v).toLocaleDateString('en-IE', { day: 'numeric', month: 'short' });
};

const formatExpiry = (v: string | null): string | null => {
  if (!v) return null;
  return new Date(v).toLocaleDateString('en-IE', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
};

const FormationsTab = ({ ctx }: Props) => {
  const { clubId } = ctx;
  const navigate = useNavigate();
  const { user } = useAuth();
  const currentUserId = typeof user?.id === 'number' ? user.id : null;

  const [teamsheets, setTeamsheets] = useState<TeamsheetListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [subView, setSubView] = useState<SubView>('active');

  const isTrashView = subView === 'trash';

  const fetchTeamsheets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await teamsheetApi.list(clubId, {
        ...(isTrashView ? { trash: 'only' } : {}),
      });
      setTeamsheets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load teamsheets.');
    } finally {
      setLoading(false);
    }
  }, [clubId, isTrashView]);

  useEffect(() => {
    void fetchTeamsheets();
  }, [fetchTeamsheets]);

  const templates = useMemo(() => teamsheets.filter((t) => t.is_template), [teamsheets]);
  const matches = useMemo(() => teamsheets.filter((t) => !t.is_template), [teamsheets]);

  const openTeamsheet = (t: TeamsheetListItem) => {
    const suffix = t.is_trashed ? '?view=trash' : '';
    navigate(`/clubs/${clubId}/teamsheets/${t.id}${suffix}`);
  };

  const handleMoveToTrash = async (id: number) => {
    if (!window.confirm('Move this teamsheet to trash?')) return;
    try {
      setActionLoadingId(id);
      setActionError(null);
      await teamsheetApi.trash(clubId, id);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to move to trash.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRestore = async (id: number) => {
    try {
      setActionLoadingId(id);
      setActionError(null);
      await teamsheetApi.restore(clubId, id);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to restore.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handlePermanentDelete = async (id: number) => {
    if (!window.confirm('Delete this teamsheet permanently? This cannot be undone.')) return;
    try {
      setActionLoadingId(id);
      setActionError(null);
      await teamsheetApi.permanentDelete(clubId, id);
      await fetchTeamsheets();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const renderCard = (t: TeamsheetListItem) => {
    const status = getTeamsheetStatus(t.starter_count, t.match_date);
    const isBusy = actionLoadingId === t.id;
    const canManageTrash = t.created_by === currentUserId;

    return (
      <article
        key={t.id}
        className={styles.card}
        onClick={() => openTeamsheet(t)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openTeamsheet(t);
          }
        }}
      >
        <div className={styles.cardHeader}>
          <span className={styles.formationBadge}>{t.formation_display}</span>
          {t.is_template ? (
            <span className={styles.templateBadge}>Template</span>
          ) : t.match_date ? (
            <span className={styles.dateBadge}>{formatDate(t.match_date)}</span>
          ) : null}
        </div>

        <h3 className={styles.cardTitle}>{t.title}</h3>

        {t.opponent && (
          <p className={styles.opponent}>vs {t.opponent}</p>
        )}

        <div className={styles.cardMeta}>
          <span className={styles[status.key as keyof typeof styles]}>{status.label}</span>
        </div>

        {t.is_trashed && t.trash_expires_at && (
          <p className={styles.trashNotice}>
            In trash until {formatExpiry(t.trash_expires_at)}
          </p>
        )}

        <div className={styles.cardActions}>
          {!t.is_trashed ? (
            canManageTrash && (
              <button
                type="button"
                className={styles.ghostBtn}
                disabled={isBusy}
                onClick={(e) => { e.stopPropagation(); void handleMoveToTrash(t.id); }}
              >
                {isBusy ? 'Moving...' : 'Move to trash'}
              </button>
            )
          ) : canManageTrash ? (
            <>
              <button
                type="button"
                className={styles.restoreBtn}
                disabled={isBusy}
                onClick={(e) => { e.stopPropagation(); void handleRestore(t.id); }}
              >
                {isBusy ? 'Restoring...' : 'Restore'}
              </button>
              <button
                type="button"
                className={styles.dangerBtn}
                disabled={isBusy}
                onClick={(e) => { e.stopPropagation(); void handlePermanentDelete(t.id); }}
              >
                {isBusy ? 'Deleting...' : 'Delete permanently'}
              </button>
            </>
          ) : null}
        </div>
      </article>
    );
  };

  return (
    <div className={styles.tabContent}>
      <div className={styles.topBar}>
        <div className={styles.subViewTabs}>
          <button
            type="button"
            className={`${styles.subTab}${subView === 'active' ? ' ' + styles.subTabActive : ''}`}
            onClick={() => { setSubView('active'); setActionError(null); }}
          >
            Active
          </button>
          <button
            type="button"
            className={`${styles.subTab}${subView === 'trash' ? ' ' + styles.subTabActive : ''}`}
            onClick={() => { setSubView('trash'); setActionError(null); }}
          >
            Trash
          </button>
        </div>

        {!isTrashView && (
          <button
            type="button"
            className={styles.primaryBtn}
            onClick={() => navigate(`/clubs/${clubId}/teamsheets/new`)}
          >
            + New teamsheet
          </button>
        )}
      </div>

      {actionError && (
        <div className={styles.errorNotice}>{actionError}</div>
      )}

      {loading ? (
        <div className={styles.loading}>Loading teamsheets...</div>
      ) : error ? (
        <div className={styles.errorNotice}>{error}</div>
      ) : isTrashView ? (
        <section className={styles.section}>
          <span className={styles.sectionLabel}>Trashed teamsheets</span>
          {teamsheets.length === 0 ? (
            <p className={styles.emptyText}>No teamsheets in trash.</p>
          ) : (
            <div className={styles.grid}>{teamsheets.map(renderCard)}</div>
          )}
        </section>
      ) : (
        <>
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionLabel}>Templates</span>
              <span className={styles.badge}>{templates.length}</span>
            </div>
            {templates.length === 0 ? (
              <p className={styles.emptyText}>
                No templates yet — create a teamsheet and mark it as a template.
              </p>
            ) : (
              <div className={styles.grid}>{templates.map(renderCard)}</div>
            )}
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionLabel}>Match teamsheets</span>
              <span className={styles.badge}>{matches.length}</span>
            </div>
            {matches.length === 0 ? (
              <p className={styles.emptyText}>
                No match teamsheets yet.{' '}
                <button
                  type="button"
                  className={styles.inlineLink}
                  onClick={() => navigate(`/clubs/${clubId}/teamsheets/new`)}
                >
                  Create your first teamsheet
                </button>
              </p>
            ) : (
              <div className={styles.grid}>{matches.map(renderCard)}</div>
            )}
          </section>
        </>
      )}
    </div>
  );
};

export default FormationsTab;