import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { tacticsBoardApi } from '../../../../services/api';
import { useAuth } from '../../../../context/useAuth';
import type { TacticsBoardListItem, TacticsBoardType, TacticsPitchOrientation } from '../../../../types/tactics';
import type { ClubContext } from '../IndividualClubBase';
import styles from './css/TacticsTab.module.css';
import { SectionSkeleton } from '../../../../common/components/SectionSkeleton';
import { InlineRetry } from '../../../../common/components/InlineRetry';

interface Props {
  ctx: ClubContext;
}

type SubView = 'active' | 'trash';

const fmtUpdated = (v: string): string =>
  new Date(v).toLocaleString('en-IE', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });

const fmtExpiry = (v: string | null): string | null => {
  if (!v) return null;
  return new Date(v).toLocaleDateString('en-IE', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
};

const getFormationContext = (board: TacticsBoardListItem): string => {
  const parts: string[] = [];
  if (board.home_formation) parts.push(`Home ${board.home_formation}`);
  if (board.away_formation) parts.push(`Away ${board.away_formation}`);
  if (parts.length === 0) {
    return board.linked_teamsheet ? 'Linked to teamsheet' : 'No formation context';
  }
  return parts.join(' · ');
};

const TacticsTab = ({ ctx }: Props) => {
  const { clubId } = ctx;
  const navigate = useNavigate();
  const { user } = useAuth();
  const currentUserId = typeof user?.id === 'number' ? user.id : null;

  const [boards, setBoards] = useState<TacticsBoardListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [subView, setSubView] = useState<SubView>('active');

  const [showModal, setShowModal] = useState(false);
  const [createTitle, setCreateTitle] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [createOrientation, setCreateOrientation] = useState<TacticsPitchOrientation>('vertical');
  const [createBoardType, setCreateBoardType] = useState<TacticsBoardType>('static');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const titleRef = useRef<HTMLInputElement>(null);

  const isTrashView = subView === 'trash';

  const loadBoards = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await tacticsBoardApi.listBoards(
        clubId,
        isTrashView ? { trash: 'only' } : undefined
      );
      setBoards(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tactics boards.');
      setBoards([]);
    } finally {
      setLoading(false);
    }
  }, [clubId, isTrashView]);

  useEffect(() => { void loadBoards(); }, [loadBoards]);

  const openBoard = (boardId: number, isTrashed = false) => {
    navigate(`/clubs/${clubId}/tactics-boards/${boardId}${isTrashed ? '?view=trash' : ''}`);
  };

  const openCreateModal = () => {
    setCreateTitle('');
    setCreateDesc('');
    setCreateOrientation('vertical');
    setCreateBoardType('static');
    setCreateError(null);
    setShowModal(true);
    setTimeout(() => titleRef.current?.focus(), 0);
  };

  const closeModal = () => { if (!creating) setShowModal(false); };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createTitle.trim()) { setCreateError('Title is required.'); return; }
    try {
      setCreating(true);
      setCreateError(null);
      const board = await tacticsBoardApi.createBoard(clubId, {
        title: createTitle.trim(),
        description: createDesc.trim() || undefined,
        pitch_orientation: createOrientation,
        board_type: createBoardType,
      });
      navigate(`/clubs/${clubId}/tactics-boards/${board.id}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create board.');
      setCreating(false);
    }
  };

  const handleMoveToTrash = async (boardId: number) => {
    if (!window.confirm('Move this tactics board to trash?')) return;
    try {
      setActionLoadingId(boardId);
      setActionError(null);
      await tacticsBoardApi.trashBoard(clubId, boardId);
      await loadBoards();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to move to trash.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRestore = async (boardId: number) => {
    try {
      setActionLoadingId(boardId);
      setActionError(null);
      await tacticsBoardApi.restoreBoard(clubId, boardId);
      await loadBoards();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to restore.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handlePermanentDelete = async (boardId: number) => {
    if (!window.confirm('Delete this board permanently? This cannot be undone.')) return;
    try {
      setActionLoadingId(boardId);
      setActionError(null);
      await tacticsBoardApi.permanentDeleteBoard(clubId, boardId);
      await loadBoards();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete.');
    } finally {
      setActionLoadingId(null);
    }
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
          <button type="button" className={styles.primaryBtn} onClick={openCreateModal}>
            + New board
          </button>
        )}
      </div>

      {actionError && <div className={styles.errorNotice}>{actionError}</div>}

      {loading ? (
        <SectionSkeleton rows={3} height="80px" gap="12px" />
      ) : error ? (
        <InlineRetry
          message={error}
          onRetry={loadBoards}
          retrying={loading}
        />
      ) : boards.length === 0 ? (
        <div className={styles.empty}>
          {isTrashView
            ? 'No tactics boards in trash.'
            : 'No tactics boards yet. Create your first board to get started.'}
        </div>
      ) : (
        <div className={styles.grid}>
          {boards.map((board) => {
            const isBusy = actionLoadingId === board.id;
            const canManageTrash = board.created_by === currentUserId;

            return (
              <article key={board.id} className={styles.card}>
                <div
                  className={styles.cardClickable}
                  onClick={() => openBoard(board.id, board.is_trashed)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      openBoard(board.id, board.is_trashed);
                    }
                  }}
                >
                  <div className={styles.cardHeader}>
                    <div>
                      <h3 className={styles.cardTitle}>{board.title}</h3>
                      <p className={styles.cardMeta}>
                        {board.board_type === 'animated' ? 'Animated' : 'Static'} · {board.pitch_orientation}
                      </p>
                    </div>
                    {board.is_template && (
                      <span className={styles.templateBadge}>Template</span>
                    )}
                  </div>

                  {board.description && (
                    <p className={styles.cardDesc}>{board.description}</p>
                  )}

                  <p className={styles.cardFormation}>{getFormationContext(board)}</p>
                  <p className={styles.cardUpdated}>Updated {fmtUpdated(board.updated_at)}</p>

                  {board.is_trashed && board.trash_expires_at && (
                    <p className={styles.trashNotice}>
                      In trash until {fmtExpiry(board.trash_expires_at)}
                    </p>
                  )}
                </div>

                <div className={styles.cardActions}>
                  {!board.is_trashed ? (
                    canManageTrash && (
                      <button
                        type="button"
                        className={styles.ghostBtn}
                        disabled={isBusy}
                        onClick={() => void handleMoveToTrash(board.id)}
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
                        onClick={() => void handleRestore(board.id)}
                      >
                        {isBusy ? 'Restoring...' : 'Restore'}
                      </button>
                      <button
                        type="button"
                        className={styles.dangerBtn}
                        disabled={isBusy}
                        onClick={() => void handlePermanentDelete(board.id)}
                      >
                        {isBusy ? 'Deleting...' : 'Delete permanently'}
                      </button>
                    </>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {showModal && (
        <div
          className={styles.overlay}
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <span className={styles.modalTitle}>New tactics board</span>
              <button type="button" className={styles.closeBtn} onClick={closeModal}>✕</button>
            </div>

            <form onSubmit={handleCreate} className={styles.modalForm}>
              {createError && <div className={styles.errorNotice}>{createError}</div>}

              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="tb_title">Title</label>
                <input
                  id="tb_title"
                  ref={titleRef}
                  className={styles.input}
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  placeholder="e.g. High press vs 4-4-2"
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="tb_desc">Description (optional)</label>
                <textarea
                  id="tb_desc"
                  className={styles.textarea}
                  rows={2}
                  value={createDesc}
                  onChange={(e) => setCreateDesc(e.target.value)}
                  placeholder="Optional notes about this board"
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="tb_orientation">Orientation</label>
                  <select
                    id="tb_orientation"
                    className={styles.select}
                    value={createOrientation}
                    onChange={(e) => setCreateOrientation(e.target.value as TacticsPitchOrientation)}
                  >
                    <option value="vertical">Vertical</option>
                    <option value="horizontal">Horizontal</option>
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="tb_type">Board type</label>
                  <select
                    id="tb_type"
                    className={styles.select}
                    value={createBoardType}
                    onChange={(e) => setCreateBoardType(e.target.value as TacticsBoardType)}
                  >
                    <option value="static">Static</option>
                    <option value="animated">Animated</option>
                  </select>
                </div>
              </div>

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={closeModal} disabled={creating}>
                  Cancel
                </button>
                <button type="submit" className={styles.primaryBtn} disabled={creating}>
                  {creating ? 'Creating...' : 'Create board'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TacticsTab;