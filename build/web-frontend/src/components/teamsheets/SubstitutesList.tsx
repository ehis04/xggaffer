import React from 'react';
import type { TeamsheetPlayer } from '../../types/teamsheet';
import styles from './SubstitutesList.module.css';

interface SubstitutesListProps {
  players: TeamsheetPlayer[];
  selectedPlayerId?: number | null;
  onPlayerClick?: (player: TeamsheetPlayer) => void;
}

const getPositionColor = (position: string): string => {
  if (position === 'GK') return '#f59e0b';
  if (['CB', 'RB', 'LB', 'RWB', 'LWB'].includes(position)) return '#3b82f6';
  if (['CM', 'CDM', 'CAM', 'RM', 'LM'].includes(position)) return '#22c55e';
  if (['ST', 'CF', 'RW', 'LW'].includes(position)) return '#ef4444';
  return '#6b7280';
};

const SubstitutesList: React.FC<SubstitutesListProps> = ({
  players,
  selectedPlayerId,
  onPlayerClick,
}) => {
  const substitutes = players.filter(p => p.is_substitute);

  if (substitutes.length === 0) {
    return (
      <div className={styles.container}>
        <h3 className={styles.title}>Substitutes</h3>
        <p className={styles.empty}>No substitutes added</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Substitutes ({substitutes.length})</h3>
      <div className={styles.list}>
        {substitutes.map(player => (
          <div
            key={player.id}
            className={`${styles.player} ${selectedPlayerId === player.id ? styles.selected : ''}`}
            onClick={() => onPlayerClick?.(player)}
          >
            <div
              className={styles.number}
              style={{ backgroundColor: getPositionColor(player.position_label) }}
            >
              {player.display_number || player.slot_number}
            </div>
            <div className={styles.info}>
              <span className={styles.name}>
                {player.display_name || `Player ${player.slot_number}`}
              </span>
              <span className={styles.position}>{player.position_label}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SubstitutesList;