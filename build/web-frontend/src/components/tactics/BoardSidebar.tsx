import React from 'react';
import type {
  TacticsBoard,
  TacticsBoardItem,
  TacticsNonPlayerItem,
  UpdateTacticsBoardItemPayload,
} from '../../types/tactics';
import ObjectProperties from './ObjectProperties';
import styles from './BoardSidebar.module.css';

interface BoardSidebarProps {
  board: TacticsBoard;
  activeFrameIndex: number;
  playerCount: number;
  selectedItem: TacticsBoardItem | null;
  error: string | null;
  isUpdatingProperties: boolean;
  onUpdateSelectedItemProperties: (
    payload: UpdateTacticsBoardItemPayload
  ) => void;
  isDeletingItem: boolean;
  onDeleteSelectedItem: () => void;
}

const getSelectedItemName = (item: TacticsBoardItem) => {
  return (
    item.player_summary?.display_name ||
    item.player_summary?.full_name ||
    item.label ||
    'Unnamed item'
  );
};

const BoardSidebar: React.FC<BoardSidebarProps> = ({
  board,
  activeFrameIndex,
  playerCount,
  selectedItem,
  error,
  isUpdatingProperties,
  onUpdateSelectedItemProperties,
  isDeletingItem,
  onDeleteSelectedItem,
}) => {
  const selectedNonPlayerItem =
    selectedItem && selectedItem.item_type !== 'player'
      ? (selectedItem as TacticsNonPlayerItem)
      : null;

  return (
    <aside className={styles.sidebar}>
      <section>
        <h2 className={styles.sectionTitle}>Board Details</h2>

        <p className={styles.detailRow}>
          <strong>Type:</strong> {board.board_type}
        </p>
        <p className={styles.detailRow}>
          <strong>Orientation:</strong> {board.pitch_orientation}
        </p>
        <p className={styles.detailRow}>
          <strong>Active frame:</strong> {activeFrameIndex}
        </p>
        <p className={styles.detailRow}>
          <strong>Players shown:</strong> {playerCount}
        </p>
        <p className={styles.detailRow}>
          <strong>Home formation:</strong> {board.home_formation || '—'}
        </p>
        <p className={styles.detailRow}>
          <strong>Away formation:</strong> {board.away_formation || '—'}
        </p>
      </section>

      {error ? (
        <section className={styles.errorCard}>
          <strong>Last action failed</strong>
          <p className={styles.errorText}>{error}</p>
        </section>
      ) : null}

      <section className={styles.selectionSection}>
        <h3 className={styles.subsectionTitle}>Selected Object</h3>

        {!selectedItem ? (
          <div className={styles.emptyState}>
            <p className={styles.emptyLead}>
              No object selected.
            </p>
            <p className={styles.emptyText}>
              Select an annotation to edit it, or choose a drawing tool and place a new one.
            </p>
          </div>
        ) : (
          <div className={styles.selectedBlock}>
            <p className={styles.detailRow}>
              <strong>Type:</strong> {selectedItem.item_type}
            </p>
            <p className={styles.detailRow}>
              <strong>Team side:</strong> {selectedItem.team_side}
            </p>
            <p className={styles.detailRow}>
              <strong>Name:</strong> {getSelectedItemName(selectedItem)}
            </p>
            <p className={styles.detailRow}>
              <strong>Coordinates:</strong>{' '}
              x {selectedItem.x.toFixed(1)} · y {selectedItem.y.toFixed(1)}
            </p>

            {selectedItem.item_type === 'player' ? (
              <div className={styles.playerNotice}>
                <p className={styles.playerNoticeText}>
                  Player editing in this phase stays limited to dragging and saving position changes.
                </p>
              </div>
            ) : (
              <>
                <ObjectProperties
                  item={selectedNonPlayerItem!}
                  isSubmitting={isUpdatingProperties}
                  onApplyProperties={onUpdateSelectedItemProperties}
                />

                <button
                  type="button"
                  onClick={onDeleteSelectedItem}
                  disabled={isDeletingItem}
                  className={styles.deleteButton}
                >
                  {isDeletingItem ? 'Deleting...' : 'Delete item'}
                </button>

                <p className={styles.deleteHint}>
                  You can also press Delete when this object is selected.
                </p>
              </>
            )}
          </div>
        )}
      </section>
    </aside>
  );
};

export default BoardSidebar;