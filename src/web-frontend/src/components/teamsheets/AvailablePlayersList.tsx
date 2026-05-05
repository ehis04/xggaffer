import React, { useState } from 'react';
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

  const filtered = players.filter(p => {
    if (selectedIds.includes(p.id)) return false;
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      return (
        p.full_name.toLowerCase().includes(s) ||
        (p.display_name?.toLowerCase().includes(s) ?? false)
      );
    }
    return true;
  });

  const clubPlayers   = filtered.filter(p => p.source_type === 'club_member');
  const publicPlayers = filtered.filter(p => p.source_type === 'public');

  return (
    <div className={styles.AvailablePlayersListContainer}>
      <div className={styles.AvailablePlayersListHeader}>
        <h3 className={styles.AvailablePlayersListTitle}>Available Players</h3>
      </div>

      <div className={styles.AvailablePlayersListFilters}>
        <input
          type="text"
          placeholder="Search players…"
          className={styles.AvailablePlayersListSearch}
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
        />
        {positions.length > 0 && onPositionFilterChange && (
          <select
            className={styles.AvailablePlayersListSelect}
            value={positionFilter ?? ''}
            onChange={e => onPositionFilterChange(e.target.value)}
          >
            <option value="" className={styles.AvailablePlayersListOption}>All Positions</option>
            {positions.map(pos => (
              <option key={pos.value} value={pos.value} className={styles.AvailablePlayersListOption}>{pos.label}</option>
            ))}
          </select>
        )}
      </div>

      {loading ? (
        <div className={styles.AvailablePlayersListLoading}>Loading players…</div>
      ) : (
        <div className={styles.AvailablePlayersListScroll}>
          <button
            type="button"
            className={styles.AvailablePlayersListDefaultBtn}
            onClick={onUseDefault}
          >
            <span className={styles.AvailablePlayersListDefaultIcon}>+</span>
            <span>Use Default Player</span>
          </button>

          {clubPlayers.length > 0 && (
            <div className={styles.AvailablePlayersListSection}>
              <h4 className={styles.AvailablePlayersListSectionTitle}>Club Members</h4>
              {clubPlayers.map(p => (
                <AvailablePlayersListPlayerRow
                  key={p.id}
                  player={p}
                  onSelect={() => onSelect(p)}
                />
              ))}
            </div>
          )}

          {publicPlayers.length > 0 && (
            <div className={styles.AvailablePlayersListSection}>
              <h4 className={styles.AvailablePlayersListSectionTitle}>Public Players</h4>
              {publicPlayers.map(p => (
                <AvailablePlayersListPlayerRow
                  key={p.id}
                  player={p}
                  onSelect={() => onSelect(p)}
                />
              ))}
            </div>
          )}

          {clubPlayers.length === 0 && publicPlayers.length === 0 && (
            <div className={styles.AvailablePlayersListEmpty}>
              No players found. Use the default player option above.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface AvailablePlayersListPlayerRowProps {
  player: AvailablePlayer;
  onSelect: () => void;
}

const AvailablePlayersListPlayerRow: React.FC<AvailablePlayersListPlayerRowProps> = ({
  player,
  onSelect,
}) => (
  <button
    type="button"
    className={styles.AvailablePlayersListRow}
    onClick={onSelect}
  >
    <div className={styles.AvailablePlayersListAvatar}>
      {player.photo ? (
        <img
          src={player.photo}
          alt=""
          className={styles.AvailablePlayersListPhoto}
        />
      ) : (
        <span>
          {player.first_name?.[0] ?? player.display_name?.[0] ?? '?'}
        </span>
      )}
    </div>

    <div className={styles.AvailablePlayersListInfo}>
      <span className={styles.AvailablePlayersListName}>
        {player.display_name ?? player.full_name}
      </span>
      <span className={styles.AvailablePlayersListMeta}>
        {player.primary_position}
        {player.squad_number ? ` · #${player.squad_number}` : ''}
      </span>
    </div>

    {player.source_type === 'public' && (
      <span className={styles.AvailablePlayersListPublicBadge}>Public</span>
    )}
  </button>
);

export default AvailablePlayersList;