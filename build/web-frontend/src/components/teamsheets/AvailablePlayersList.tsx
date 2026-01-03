import React, { useState, useEffect } from 'react';
import type { AvailablePlayer } from '../../types/teamsheet';
import styles from './AvailablePlayersList.module.css';

interface AvailablePlayersListProps {
  players: AvailablePlayer[];
  loading: boolean;
  onSelect: (player: AvailablePlayer) => void;
  onUseDefault: () => void;
  positionFilter?: string;
  onPositionFilterChange?: (position: string) => void;
  positions?: { value: string; label: string }[];
  selectedIds?: number[];
}

const AvailablePlayersList: React.FC<AvailablePlayersListProps> = ({
  players,
  loading,
  onSelect,
  onUseDefault,
  positionFilter,
  onPositionFilterChange,
  positions = [],
  selectedIds = [],
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredPlayers = players.filter(player => {
    if (selectedIds.includes(player.id)) return false;
    
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      const matchesName = player.full_name.toLowerCase().includes(search) ||
        (player.display_name?.toLowerCase().includes(search));
      if (!matchesName) return false;
    }
    
    return true;
  });

  const clubPlayers = filteredPlayers.filter(p => p.source_type === 'club_member');
  const publicPlayers = filteredPlayers.filter(p => p.source_type === 'public');

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Available Players</h3>
      </div>

      <div className={styles.filters}>
        <input
          type="text"
          placeholder="Search players..."
          className={styles.searchInput}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />

        {positions.length > 0 && onPositionFilterChange && (
          <select
            className={styles.positionSelect}
            value={positionFilter || ''}
            onChange={(e) => onPositionFilterChange(e.target.value)}
          >
            <option value="">All Positions</option>
            {positions.map(pos => (
              <option key={pos.value} value={pos.value}>{pos.label}</option>
            ))}
          </select>
        )}
      </div>

      {loading ? (
        <div className={styles.loading}>Loading players...</div>
      ) : (
        <div className={styles.playersList}>
          <button
            type="button"
            className={styles.defaultButton}
            onClick={onUseDefault}
          >
            <span className={styles.defaultIcon}>+</span>
            <span>Use Default Player</span>
          </button>

          {clubPlayers.length > 0 && (
            <div className={styles.section}>
              <h4 className={styles.sectionTitle}>Club Members</h4>
              {clubPlayers.map(player => (
                <PlayerRow
                  key={player.id}
                  player={player}
                  onSelect={() => onSelect(player)}
                />
              ))}
            </div>
          )}

          {publicPlayers.length > 0 && (
            <div className={styles.section}>
              <h4 className={styles.sectionTitle}>Public Players</h4>
              {publicPlayers.map(player => (
                <PlayerRow
                  key={player.id}
                  player={player}
                  onSelect={() => onSelect(player)}
                />
              ))}
            </div>
          )}

          {clubPlayers.length === 0 && publicPlayers.length === 0 && (
            <div className={styles.empty}>
              No available players found. Use the default player option.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface PlayerRowProps {
  player: AvailablePlayer;
  onSelect: () => void;
}

const PlayerRow: React.FC<PlayerRowProps> = ({ player, onSelect }) => {
  return (
    <button
      type="button"
      className={styles.playerRow}
      onClick={onSelect}
    >
      <div className={styles.playerAvatar}>
        {player.photo ? (
          <img src={player.photo} alt="" className={styles.playerPhoto} />
        ) : (
          <span className={styles.avatarInitial}>
            {player.first_name?.[0] || player.display_name?.[0] || '?'}
          </span>
        )}
      </div>
      <div className={styles.playerInfo}>
        <span className={styles.playerName}>
          {player.display_name || player.full_name}
        </span>
        <span className={styles.playerMeta}>
          {player.position}
          {player.squad_number && ` • #${player.squad_number}`}
        </span>
      </div>
      {player.source_type === 'public' && (
        <span className={styles.publicBadge}>Public</span>
      )}
    </button>
  );
};

export default AvailablePlayersList;