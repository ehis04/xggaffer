import React from 'react';
import type { TeamsheetPlayer } from '../../types/teamsheet';
import styles from './PlayerDetailPanel.module.css';

interface PlayerDetailPanelProps {
  player: TeamsheetPlayer;
  onClose: () => void;
  onSwap?: () => void;
  onRemove?: () => void;
}

const getPositionColor = (position: string): string => {
  if (position === 'GK') return '#f59e0b';
  if (['CB', 'RB', 'LB', 'RWB', 'LWB'].includes(position)) return '#3b82f6';
  if (['CM', 'CDM', 'CAM', 'RM', 'LM'].includes(position)) return '#22c55e';
  if (['ST', 'CF', 'RW', 'LW'].includes(position)) return '#ef4444';
  return '#6b7280';
};

const PlayerDetailPanel: React.FC<PlayerDetailPanelProps> = ({
  player,
  onClose,
  onSwap,
  onRemove,
}) => {
  return (
    <div className={styles.playerDetailPanelRoot}>
      <div className={styles.playerDetailPanelHeader}>
        <h3 className={styles.playerDetailPanelTitle}>Player Details</h3>
        <button className={styles.playerDetailPanelCloseButton} onClick={onClose}>
          ×
        </button>
      </div>

      <div className={styles.playerDetailPanelContent}>
        <div className={styles.playerDetailPanelPlayerInfo}>
          {player.display_photo_url ? (
            <img
              src={player.display_photo_url}
              alt={player.display_name}
              className={styles.playerDetailPanelPhoto}
            />
          ) : (
            <div
              className={styles.playerDetailPanelPhotoPlaceholder}
              style={{ backgroundColor: getPositionColor(player.position_label) }}
            >
              {player.display_number || player.slot_number}
            </div>
          )}

          <div className={styles.playerDetailPanelDetails}>
            <span className={styles.playerDetailPanelName}>
              {player.display_name || `Player ${player.slot_number}`}
            </span>
            <span className={styles.playerDetailPanelNumber}>
              #{player.display_number || '—'}
            </span>
          </div>
        </div>

        <div className={styles.playerDetailPanelStats}>
          <div className={styles.playerDetailPanelStatItem}>
            <span className={styles.playerDetailPanelStatLabel}>Position</span>
            <span
              className={styles.playerDetailPanelStatValue}
              style={{ color: getPositionColor(player.position_label) }}
            >
              {player.position_label}
            </span>
          </div>

          <div className={styles.playerDetailPanelStatItem}>
            <span className={styles.playerDetailPanelStatLabel}>Slot</span>
            <span className={styles.playerDetailPanelStatValue}>
              {player.slot_number}
            </span>
          </div>

          <div className={styles.playerDetailPanelStatItem}>
            <span className={styles.playerDetailPanelStatLabel}>Status</span>
            <span className={styles.playerDetailPanelStatValue}>
              {player.is_substitute ? 'Substitute' : 'Starter'}
            </span>
          </div>

          <div className={styles.playerDetailPanelStatItem}>
            <span className={styles.playerDetailPanelStatLabel}>Type</span>
            <span className={styles.playerDetailPanelStatValue}>
              {player.is_linked ? 'Club Player' : 'Custom'}
            </span>
          </div>
        </div>

        <div className={styles.playerDetailPanelPosition}>
          <span className={styles.playerDetailPanelPosLabel}>
            Position on Pitch
          </span>
          <div className={styles.playerDetailPanelCoords}>
            <span>X: {player.position_x.toFixed(1)}</span>
            <span>Y: {player.position_y.toFixed(1)}</span>
          </div>
        </div>

        {(onSwap || onRemove) && (
          <div className={styles.playerDetailPanelActions}>
            {onSwap && (
              <button
                className={styles.playerDetailPanelActionButton}
                onClick={onSwap}
              >
                Swap
              </button>
            )}
            {onRemove && (
              <button
                className={`${styles.playerDetailPanelActionButton} ${styles.playerDetailPanelDanger}`}
                onClick={onRemove}
              >
                Remove
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PlayerDetailPanel;