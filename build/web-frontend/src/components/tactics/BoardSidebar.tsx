import React from 'react';
import type {
  TacticsBoard,
  TacticsBoardItem,
  TacticsNonPlayerItem,
  UpdateTacticsBoardItemPayload,
} from '../../types/tactics';
import ObjectProperties from './ObjectProperties';

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
    <aside
      style={{
        border: '1px solid #d1d5db',
        borderRadius: '14px',
        padding: '16px',
        minWidth: '280px',
      }}
    >
      <section>
        <h2 style={{ marginTop: 0, marginBottom: '12px' }}>Board Details</h2>

        <p>
          <strong>Type:</strong> {board.board_type}
        </p>
        <p>
          <strong>Orientation:</strong> {board.pitch_orientation}
        </p>
        <p>
          <strong>Active frame:</strong> {activeFrameIndex}
        </p>
        <p>
          <strong>Players shown:</strong> {playerCount}
        </p>
        <p>
          <strong>Home formation:</strong> {board.home_formation || '—'}
        </p>
        <p>
          <strong>Away formation:</strong> {board.away_formation || '—'}
        </p>
      </section>

      {error ? (
        <section
          style={{
            marginTop: '18px',
            padding: '12px',
            border: '1px solid #ef4444',
            borderRadius: '10px',
            background: 'rgba(239, 68, 68, 0.04)',
          }}
        >
          <strong>Last action failed</strong>
          <p style={{ margin: '8px 0 0 0' }}>{error}</p>
        </section>
      ) : null}

      <section style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '10px' }}>Selected Object</h3>

        {!selectedItem ? (
          <div
            style={{
              padding: '12px',
              border: '1px dashed #9ca3af',
              borderRadius: '10px',
            }}
          >
            <p style={{ margin: 0 }}>
              No object selected.
            </p>
            <p style={{ margin: '8px 0 0 0', color: '#4b5563' }}>
              Select an annotation to edit it, or choose a drawing tool and place a new one.
            </p>
          </div>
        ) : (
          <div>
            <p>
              <strong>Type:</strong> {selectedItem.item_type}
            </p>
            <p>
              <strong>Team side:</strong> {selectedItem.team_side}
            </p>
            <p>
              <strong>Name:</strong> {getSelectedItemName(selectedItem)}
            </p>
            <p>
              <strong>Coordinates:</strong>{' '}
              x {selectedItem.x.toFixed(1)} · y {selectedItem.y.toFixed(1)}
            </p>

            {selectedItem.item_type === 'player' ? (
              <div
                style={{
                  marginTop: '12px',
                  padding: '12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '10px',
                }}
              >
                <p style={{ margin: 0 }}>
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
                  style={{
                    marginTop: '12px',
                    padding: '9px 14px',
                    borderRadius: '999px',
                    border: '1px solid #b91c1c',
                    background: '#b91c1c',
                    color: '#ffffff',
                    fontWeight: 600,
                    cursor: isDeletingItem ? 'default' : 'pointer',
                  }}
                >
                  {isDeletingItem ? 'Deleting...' : 'Delete item'}
                </button>

                <p style={{ margin: '10px 0 0 0', color: '#4b5563' }}>
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