import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { tacticsBoardApi } from '../../../services/api';
import type { TacticsBoardListItem, TacticsBoardType, TacticsPitchOrientation } from '../../../types/tactics';
import { useAuth } from '../../../context/useAuth';

const formatBoardType = (value: TacticsBoardListItem['board_type']) => {
  return value === 'animated' ? 'Animated' : 'Static';
};

const formatUpdatedAt = (value: string) => {
  return new Date(value).toLocaleString('en-IE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatExpiry = (value: string | null) => {
  if (!value) return null;
  return new Date(value).toLocaleDateString('en-IE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
};

const getFormationContext = (board: TacticsBoardListItem) => {
  const formations: string[] = [];

  if (board.home_formation) {
    formations.push(`Home ${board.home_formation}`);
  }

  if (board.away_formation) {
    formations.push(`Away ${board.away_formation}`);
  }

  if (formations.length === 0) {
    return board.linked_teamsheet
      ? 'Linked to a teamsheet'
      : 'No formation context';
  }

  return formations.join(' · ');
};

const TacticsBoardListPage: React.FC = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const currentUserId = typeof user?.id === 'number' ? user.id : null;

  const numericClubId = useMemo(() => Number(clubId), [clubId]);
  const activeView = searchParams.get('view') === 'trash' ? 'trash' : 'active';
  const isTrashView = activeView === 'trash';

  const [boards, setBoards] = useState<TacticsBoardListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createTitle, setCreateTitle] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createOrientation, setCreateOrientation] = useState<TacticsPitchOrientation>('vertical');
  const [createBoardType, setCreateBoardType] = useState<TacticsBoardType>('static');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);

  const loadBoards = async () => {
    if (!Number.isInteger(numericClubId) || numericClubId <= 0) {
      setBoards([]);
      setError('Invalid club ID.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await tacticsBoardApi.listBoards(
        numericClubId,
        isTrashView ? { trash: 'only' } : undefined
      );
      setBoards(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tactics boards.');
      setBoards([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadBoards();
  }, [numericClubId, isTrashView]);

  const handleBack = () => {
    navigate(`/clubs/${numericClubId}`);
  };

  const handleOpenBoard = (boardId: number, isTrashed = false) => {
    navigate(
      `/clubs/${numericClubId}/tactics-boards/${boardId}${isTrashed ? '?view=trash' : ''}`
    );
  };

  const handleOpenCreateModal = () => {
    setCreateTitle('');
    setCreateDescription('');
    setCreateOrientation('vertical');
    setCreateBoardType('static');
    setCreateError(null);
    setShowCreateModal(true);
    setTimeout(() => titleInputRef.current?.focus(), 0);
  };

  const handleCloseCreateModal = () => {
    if (!creating) setShowCreateModal(false);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createTitle.trim()) {
      setCreateError('Title is required.');
      return;
    }

    setCreating(true);
    setCreateError(null);

    try {
      const board = await tacticsBoardApi.createBoard(numericClubId, {
        title: createTitle.trim(),
        description: createDescription.trim() || undefined,
        pitch_orientation: createOrientation,
        board_type: createBoardType,
      });
      navigate(`/clubs/${numericClubId}/tactics-boards/${board.id}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create board.');
      setCreating(false);
    }
  };

  const handleMoveToTrash = async (boardId: number) => {
    const confirmed = window.confirm('Move this tactics board to trash?');
    if (!confirmed) return;

    try {
      setActionLoadingId(boardId);
      setActionError(null);
      await tacticsBoardApi.trashBoard(numericClubId, boardId);
      await loadBoards();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to move board to trash.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRestore = async (boardId: number) => {
    try {
      setActionLoadingId(boardId);
      setActionError(null);
      await tacticsBoardApi.restoreBoard(numericClubId, boardId);
      await loadBoards();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to restore board.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handlePermanentDelete = async (boardId: number) => {
    const confirmed = window.confirm(
      'Delete this tactics board permanently? This cannot be undone.'
    );
    if (!confirmed) return;

    try {
      setActionLoadingId(boardId);
      setActionError(null);
      await tacticsBoardApi.permanentDeleteBoard(numericClubId, boardId);
      await loadBoards();
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : 'Failed to permanently delete board.'
      );
    } finally {
      setActionLoadingId(null);
    }
  };

  const setView = (view: 'active' | 'trash') => {
    setActionError(null);
    if (view === 'trash') {
      setSearchParams({ view: 'trash' });
      return;
    }
    setSearchParams({});
  };

  const newBoardButton = !isTrashView ? (
    <button
      type="button"
      onClick={handleOpenCreateModal}
      style={{
        padding: '8px 16px',
        borderRadius: '8px',
        border: 'none',
        background: '#16a34a',
        color: '#fff',
        fontWeight: 600,
        cursor: 'pointer',
      }}
    >
      + New Board
    </button>
  ) : null;

  const createModal = showCreateModal ? (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-board-title"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleCloseCreateModal();
      }}
    >
      <div
        style={{
          background: '#1f2937',
          color: '#f9fafb',
          borderRadius: '12px',
          padding: '24px',
          width: '100%',
          maxWidth: '440px',
        }}
      >
        <h2 id="create-board-title" style={{ margin: '0 0 20px 0' }}>
          New Tactics Board
        </h2>

        <form onSubmit={(e) => { void handleCreate(e); }}>
          <div style={{ marginBottom: '16px' }}>
            <label
              htmlFor="create-title"
              style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}
            >
              Title <span aria-hidden="true">*</span>
            </label>
            <input
              id="create-title"
              ref={titleInputRef}
              type="text"
              value={createTitle}
              onChange={(e) => setCreateTitle(e.target.value)}
              placeholder="e.g. High Press vs 4-4-2"
              disabled={creating}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: '6px',
                border: '1px solid #374151',
                background: '#111827',
                color: '#f9fafb',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label
              htmlFor="create-description"
              style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}
            >
              Description
            </label>
            <textarea
              id="create-description"
              value={createDescription}
              onChange={(e) => setCreateDescription(e.target.value)}
              placeholder="Optional"
              rows={2}
              disabled={creating}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: '6px',
                border: '1px solid #374151',
                background: '#111827',
                color: '#f9fafb',
                resize: 'vertical',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
            <div style={{ flex: 1 }}>
              <label
                htmlFor="create-orientation"
                style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}
              >
                Pitch orientation
              </label>
              <select
                id="create-orientation"
                value={createOrientation}
                onChange={(e) => setCreateOrientation(e.target.value as TacticsPitchOrientation)}
                disabled={creating}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: '6px',
                  border: '1px solid #374151',
                  background: '#111827',
                  color: '#f9fafb',
                }}
              >
                <option value="vertical">Vertical</option>
                <option value="horizontal">Horizontal</option>
              </select>
            </div>

            <div style={{ flex: 1 }}>
              <label
                htmlFor="create-board-type"
                style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}
              >
                Board type
              </label>
              <select
                id="create-board-type"
                value={createBoardType}
                onChange={(e) => setCreateBoardType(e.target.value as TacticsBoardType)}
                disabled={creating}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: '6px',
                  border: '1px solid #374151',
                  background: '#111827',
                  color: '#f9fafb',
                }}
              >
                <option value="static">Static</option>
                <option value="animated">Animated</option>
              </select>
            </div>
          </div>

          {createError ? (
            <div
              style={{
                marginBottom: '16px',
                padding: '10px 12px',
                borderRadius: '8px',
                background: 'rgba(220, 38, 38, 0.12)',
                border: '1px solid rgba(248, 113, 113, 0.35)',
                color: '#fecaca',
              }}
            >
              {createError}
            </div>
          ) : null}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              onClick={handleCloseCreateModal}
              disabled={creating}
              style={{
                padding: '8px 14px',
                borderRadius: '8px',
                border: '1px solid #4b5563',
                background: 'transparent',
                color: '#f9fafb',
                cursor: creating ? 'not-allowed' : 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating}
              style={{
                padding: '8px 14px',
                borderRadius: '8px',
                border: 'none',
                background: '#2563eb',
                color: '#fff',
                fontWeight: 600,
                cursor: creating ? 'not-allowed' : 'pointer',
              }}
            >
              {creating ? 'Creating…' : 'Create board'}
            </button>
          </div>
        </form>
      </div>
    </div>
  ) : null;

  if (loading) {
    return (
      <div style={{ padding: '32px', color: '#f9fafb' }}>
        Loading tactics boards…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '32px', color: '#fca5a5' }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ padding: '32px', color: '#f9fafb' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '16px',
          marginBottom: '24px',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <button
            type="button"
            onClick={handleBack}
            style={{
              marginBottom: '12px',
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid #334155',
              background: '#111827',
              color: '#f9fafb',
              cursor: 'pointer',
            }}
          >
            ← Back to Club
          </button>

          <h1 style={{ margin: 0, fontSize: '2rem', fontWeight: 700 }}>
            Tactics Boards
          </h1>
          <p style={{ margin: '8px 0 0 0', color: '#cbd5e1' }}>
            {isTrashView
              ? 'Restore deleted boards or permanently remove them.'
              : 'Create, open, and manage your active club tactics boards.'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div
            style={{
              display: 'flex',
              gap: '8px',
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '10px',
              padding: '6px',
            }}
          >
            <button
              type="button"
              onClick={() => setView('active')}
              style={{
                padding: '8px 12px',
                borderRadius: '8px',
                border: 'none',
                background: !isTrashView ? '#2563eb' : 'transparent',
                color: '#f9fafb',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Active
            </button>
            <button
              type="button"
              onClick={() => setView('trash')}
              style={{
                padding: '8px 12px',
                borderRadius: '8px',
                border: 'none',
                background: isTrashView ? '#2563eb' : 'transparent',
                color: '#f9fafb',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Trash
            </button>
          </div>

          {newBoardButton}
        </div>
      </div>

      {actionError ? (
        <div
          style={{
            marginBottom: '20px',
            padding: '12px 14px',
            borderRadius: '10px',
            background: 'rgba(220, 38, 38, 0.12)',
            border: '1px solid rgba(248, 113, 113, 0.35)',
            color: '#fecaca',
          }}
        >
          {actionError}
        </div>
      ) : null}

      {boards.length === 0 ? (
        <div
          style={{
            padding: '24px',
            borderRadius: '12px',
            background: '#111827',
            border: '1px solid #1f2937',
            color: '#cbd5e1',
          }}
        >
          {isTrashView
            ? 'No tactics boards are currently in trash.'
            : 'No tactics boards yet. Create your first board to get started.'}
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gap: '16px',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
          }}
        >
          {boards.map((board) => {
            const isBusy = actionLoadingId === board.id;
            const canManageTrash = board.created_by === currentUserId;

            return (
              <article
                key={board.id}
                style={{
                  background: '#111827',
                  border: '1px solid #1f2937',
                  borderRadius: '14px',
                  padding: '18px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                <div
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleOpenBoard(board.id, board.is_trashed)}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: '12px',
                      alignItems: 'flex-start',
                    }}
                  >
                    <div>
                      <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                        {board.title}
                      </h2>
                      <p style={{ margin: '6px 0 0 0', color: '#94a3b8' }}>
                        {formatBoardType(board.board_type)} · {board.pitch_orientation}
                      </p>
                    </div>

                    {board.is_template ? (
                      <span
                        style={{
                          padding: '4px 10px',
                          borderRadius: '999px',
                          background: 'rgba(59, 130, 246, 0.16)',
                          color: '#bfdbfe',
                          fontSize: '0.78rem',
                          fontWeight: 700,
                        }}
                      >
                        Template
                      </span>
                    ) : null}
                  </div>

                  {board.description ? (
                    <p style={{ margin: '10px 0 0 0', color: '#e5e7eb', lineHeight: 1.5 }}>
                      {board.description}
                    </p>
                  ) : null}

                  <p style={{ margin: '10px 0 0 0', color: '#94a3b8' }}>
                    {getFormationContext(board)}
                  </p>

                  <p style={{ margin: '8px 0 0 0', color: '#94a3b8', fontSize: '0.9rem' }}>
                    Updated {formatUpdatedAt(board.updated_at)}
                  </p>

                  {board.is_trashed && board.trash_expires_at ? (
                    <p style={{ margin: '8px 0 0 0', color: '#fecaca', fontSize: '0.88rem' }}>
                      In trash until {formatExpiry(board.trash_expires_at)}
                    </p>
                  ) : null}
                </div>

                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  {!board.is_trashed ? (
                    canManageTrash ? (
                      <button
                        type="button"
                        onClick={() => void handleMoveToTrash(board.id)}
                        disabled={isBusy}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: 'none',
                          background: 'rgba(239, 68, 68, 0.18)',
                          color: '#fecaca',
                          cursor: isBusy ? 'not-allowed' : 'pointer',
                          fontWeight: 600,
                        }}
                      >
                        {isBusy ? 'Moving…' : 'Move to Trash'}
                      </button>
                    ) : null
                  ) : canManageTrash ? (
                    <>
                      <button
                        type="button"
                        onClick={() => void handleRestore(board.id)}
                        disabled={isBusy}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: 'none',
                          background: 'rgba(34, 197, 94, 0.18)',
                          color: '#bbf7d0',
                          cursor: isBusy ? 'not-allowed' : 'pointer',
                          fontWeight: 600,
                        }}
                      >
                        {isBusy ? 'Restoring…' : 'Restore'}
                      </button>

                      <button
                        type="button"
                        onClick={() => void handlePermanentDelete(board.id)}
                        disabled={isBusy}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: 'none',
                          background: 'rgba(239, 68, 68, 0.18)',
                          color: '#fecaca',
                          cursor: isBusy ? 'not-allowed' : 'pointer',
                          fontWeight: 600,
                        }}
                      >
                        {isBusy ? 'Deleting…' : 'Delete Permanently'}
                      </button>
                    </>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {createModal}
    </div>
  );
};

export default TacticsBoardListPage;