import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Sidebar } from '../../components/Navigation/SideBar';
import { clubsApi } from '../../services/api';
import { teamsheetApi } from '../../services/api/teamsheetApi';
import { tacticsBoardApi } from '../../services/api/tacticsApi';
import type { TrashListItem, TrashSection } from '../../types/club';
import './css/TrashPage.css';

const SECTION_OPTIONS: Array<{ value: TrashSection; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'clubs', label: 'Clubs' },
  { value: 'teamsheets', label: 'Teamsheets' },
  { value: 'tactics', label: 'Tactics' },
];

const formatDateTime = (value: string | null) => {
  if (!value) {
    return '—';
  }

  return new Date(value).toLocaleString('en-IE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatSectionLabel = (section: TrashListItem['section']) => {
  switch (section) {
    case 'clubs':
      return 'Club';
    case 'teamsheets':
      return 'Teamsheet';
    case 'tactics':
      return 'Tactics';
    default:
      return section;
  }
};

const TrashPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const sectionParam = (searchParams.get('section') || 'all').toLowerCase();
  const activeSection: TrashSection = (
    ['all', 'clubs', 'teamsheets', 'tactics'].includes(sectionParam)
      ? sectionParam
      : 'all'
  ) as TrashSection;

  const [items, setItems] = useState<TrashListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionLoadingKey, setActionLoadingKey] = useState<string | null>(null);

  const loadTrashItems = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await clubsApi.listTrashItems(
        activeSection === 'all' ? undefined : { section: activeSection }
      );

      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trash items.');
    } finally {
      setLoading(false);
    }
  }, [activeSection]);

  useEffect(() => {
    void loadTrashItems();
  }, [loadTrashItems]);

  const handleSectionChange = (section: TrashSection) => {
    setActionMessage(null);

    if (section === 'all') {
      setSearchParams({});
      return;
    }

    setSearchParams({ section });
  };

  const handleOpenItem = (item: TrashListItem) => {
    navigate(item.route_path);
  };

  const handleRestore = async (item: TrashListItem) => {
    const actionKey = `restore-${item.section}-${item.id}`;

    try {
      setActionLoadingKey(actionKey);
      setActionMessage(null);

      if (item.section === 'clubs') {
        await clubsApi.restore(item.id);
      } else if (item.section === 'teamsheets') {
        if (!item.club_id) {
          throw new Error('Missing parent club for this teamsheet.');
        }
        await teamsheetApi.restore(item.club_id, item.id);
      } else if (item.section === 'tactics') {
        if (!item.club_id) {
          throw new Error('Missing parent club for this tactics board.');
        }
        await tacticsBoardApi.restoreBoard(item.club_id, item.id);
      }

      setActionMessage('Item restored successfully.');
      await loadTrashItems();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Failed to restore item.');
    } finally {
      setActionLoadingKey(null);
    }
  };

  const handlePermanentDelete = async (item: TrashListItem) => {
    const confirmed = window.confirm(
      `Delete “${item.title}” permanently? This cannot be undone.`
    );
    if (!confirmed) {
      return;
    }

    const actionKey = `delete-${item.section}-${item.id}`;

    try {
      setActionLoadingKey(actionKey);
      setActionMessage(null);

      if (item.section === 'clubs') {
        await clubsApi.permanentDelete(item.id);
      } else if (item.section === 'teamsheets') {
        if (!item.club_id) {
          throw new Error('Missing parent club for this teamsheet.');
        }
        await teamsheetApi.permanentDelete(item.club_id, item.id);
      } else if (item.section === 'tactics') {
        if (!item.club_id) {
          throw new Error('Missing parent club for this tactics board.');
        }
        await tacticsBoardApi.permanentDeleteBoard(item.club_id, item.id);
      }

      setActionMessage('Item deleted permanently.');
      await loadTrashItems();
    } catch (err) {
      setActionMessage(
        err instanceof Error ? err.message : 'Failed to permanently delete item.'
      );
    } finally {
      setActionLoadingKey(null);
    }
  };

  const itemCountLabel = useMemo(() => {
    if (activeSection === 'all') {
      return `${items.length} items`;
    }

    const option = SECTION_OPTIONS.find((entry) => entry.value === activeSection);
    return `${items.length} ${option?.label.toLowerCase() ?? 'items'}`;
  }, [activeSection, items.length]);

  return (
    <div className="trash-page">
      <aside className="trash-page__sidebar">
        <Sidebar />
      </aside>

      <main className="trash-page__main">
        <header className="trash-page__hero">
          <div>
            <h1 className="trash-page__title">Trash</h1>
            <p className="trash-page__subtitle">
              Recover or permanently remove deleted clubs, teamsheets, and tactics boards from one place.
            </p>
          </div>

          <div className="trash-page__count-pill">{itemCountLabel}</div>
        </header>

        <section className="trash-page__filters">
          {SECTION_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`trash-page__filter-button ${
                activeSection === option.value ? 'trash-page__filter-button--active' : ''
              }`}
              onClick={() => handleSectionChange(option.value)}
            >
              {option.label}
            </button>
          ))}
        </section>

        {error && <div className="trash-page__error">{error}</div>}
        {actionMessage && <div className="trash-page__notice">{actionMessage}</div>}

        {loading ? (
          <div className="trash-page__empty">Loading trash items…</div>
        ) : items.length === 0 ? (
          <div className="trash-page__empty">
            No deleted items found for this filter.
          </div>
        ) : (
          <section className="trash-page__list">
            {items.map((item) => {
              const restoreKey = `restore-${item.section}-${item.id}`;
              const deleteKey = `delete-${item.section}-${item.id}`;
              const isRestoring = actionLoadingKey === restoreKey;
              const isDeleting = actionLoadingKey === deleteKey;

              return (
                <article key={`${item.section}-${item.id}`} className="trash-page__card">
                  <div className="trash-page__card-header">
                    <div>
                      <div className="trash-page__section-pill">
                        {formatSectionLabel(item.section)}
                      </div>
                      <h2 className="trash-page__card-title">{item.title}</h2>
                    </div>

                    <button
                      type="button"
                      className="trash-page__open-button"
                      onClick={() => handleOpenItem(item)}
                    >
                      Open
                    </button>
                  </div>

                  {item.club_name && (
                    <p className="trash-page__meta">
                      <strong>Club:</strong> {item.club_name}
                    </p>
                  )}

                  {item.secondary_text && (
                    <p className="trash-page__meta">{item.secondary_text}</p>
                  )}

                  <div className="trash-page__dates">
                    <span>
                      <strong>Trashed:</strong> {formatDateTime(item.trashed_at)}
                    </span>
                    <span>
                      <strong>Expires:</strong> {formatDateTime(item.trash_expires_at)}
                    </span>
                  </div>

                  <div className="trash-page__actions">
                    <button
                      type="button"
                      className="trash-page__restore-button"
                      disabled={isRestoring || isDeleting}
                      onClick={() => void handleRestore(item)}
                    >
                      {isRestoring ? 'Restoring...' : 'Restore'}
                    </button>

                    <button
                      type="button"
                      className="trash-page__delete-button"
                      disabled={isDeleting || isRestoring}
                      onClick={() => void handlePermanentDelete(item)}
                    >
                      {isDeleting ? 'Deleting...' : 'Delete Permanently'}
                    </button>
                  </div>
                </article>
              );
            })}
          </section>
        )}
      </main>
    </div>
  );
};

export default TrashPage;