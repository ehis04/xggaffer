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
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3 className={styles.title}>Player Details</h3>
        <button className={styles.closeButton} onClick={onClose}>
          ×
        </button>
      </div>

      <div className={styles.content}>
        <div className={styles.playerInfo}>
          {player.display_photo_url ? (
            <img
              src={player.display_photo_url}
              alt={player.display_name}
              className={styles.photo}
            />
          ) : (
            <div
              className={styles.photoPlaceholder}
              style={{ backgroundColor: getPositionColor(player.position_label) }}
            >
              {player.display_number || player.slot_number}
            </div>
          )}

          <div className={styles.details}>
            <span className={styles.name}>
              {player.display_name || `Player ${player.slot_number}`}
            </span>
            <span className={styles.number}>
              #{player.display_number || '-'}
            </span>
          </div>
        </div>

        <div className={styles.stats}>
          <div className={styles.statItem}>
            <span className={styles.statLabel}>Position</span>
            <span
              className={styles.statValue}
              style={{ color: getPositionColor(player.position_label) }}
            >
              {player.position_label}
            </span>
          </div>

          <div className={styles.statItem}>
            <span className={styles.statLabel}>Slot</span>
            <span className={styles.statValue}>{player.slot_number}</span>
          </div>

          <div className={styles.statItem}>
            <span className={styles.statLabel}>Status</span>
            <span className={styles.statValue}>
              {player.is_substitute ? 'Substitute' : 'Starter'}
            </span>
          </div>

          <div className={styles.statItem}>
            <span className={styles.statLabel}>Type</span>
            <span className={styles.statValue}>
              {player.is_linked ? 'Club Player' : 'Custom'}
            </span>
          </div>
        </div>

        <div className={styles.position}>
          <span className={styles.posLabel}>Position on Pitch</span>
          <div className={styles.coords}>
            <span>X: {player.position_x.toFixed(1)}</span>
            <span>Y: {player.position_y.toFixed(1)}</span>
          </div>
        </div>

        {(onSwap || onRemove) && (
          <div className={styles.actions}>
            {onSwap && (
              <button className={styles.actionButton} onClick={onSwap}>
                Swap Position
              </button>
            )}
            {onRemove && (
              <button className={`${styles.actionButton} ${styles.danger}`} onClick={onRemove}>
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