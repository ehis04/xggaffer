import { useEffect, useMemo, useState } from 'react';
import type { ClubPlayer } from '../../types/clubPlayers';
import styles from './css/TrainingComponents.module.css';

interface Props {
  players: ClubPlayer[];
  assignedIds: number[];
  disabled?: boolean;
  onAssignAll: () => Promise<void>;
  onAssignSelected: (ids: number[]) => Promise<void>;
}

const playerLabel = (player: ClubPlayer) =>
  player.display_name || player.full_name || `${player.first_name} ${player.last_name}`.trim();

export const TrainingPlayerSelector = ({
  players,
  assignedIds,
  disabled = false,
  onAssignAll,
  onAssignSelected,
}: Props) => {
  const [query, setQuery] = useState('');
  const [position, setPosition] = useState('');
  const [selected, setSelected] = useState<number[]>(assignedIds);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setSelected(assignedIds);
  }, [assignedIds]);

  const positions = useMemo(
    () => Array.from(new Set(players.map((p) => p.primary_position).filter(Boolean))).sort(),
    [players]
  );

  const filtered = players.filter((player) => {
    const label = playerLabel(player).toLowerCase();
    const matchesQuery = !query.trim() || label.includes(query.trim().toLowerCase());
    const matchesPosition = !position || player.primary_position === position;
    return player.is_active && matchesQuery && matchesPosition;
  });

  const toggle = (id: number) => {
    setSelected((prev) => prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]);
  };

  const submitSelected = async () => {
    setSaving(true);
    try {
      await onAssignSelected(selected);
    } finally {
      setSaving(false);
    }
  };

  const submitAll = async () => {
    setSaving(true);
    try {
      await onAssignAll();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className={styles.selectorHeader}>
        <span className={styles.playerMeta}>{assignedIds.length} assigned</span>
        <button type="button" className={styles.compactBtn} disabled={disabled || saving} onClick={submitAll}>
          Assign all active
        </button>
      </div>
      <div className={styles.playerToolbar}>
        <input
          className={styles.input}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search players"
          disabled={disabled}
        />
        <select
          className={styles.select}
          value={position}
          onChange={(e) => setPosition(e.target.value)}
          disabled={disabled}
        >
          <option value="">All positions</option>
          {positions.map((pos) => <option key={pos} value={pos}>{pos}</option>)}
        </select>
        <button type="button" className={styles.primaryBtn} disabled={disabled || saving} onClick={submitSelected}>
          Save selection
        </button>
      </div>
      <div className={styles.playerList}>
        {filtered.map((player) => (
          <label key={player.id} className={styles.playerRow}>
            <input
              type="checkbox"
              checked={selected.includes(player.id)}
              onChange={() => toggle(player.id)}
              disabled={disabled}
            />
            <span>
              <span className={styles.playerName}>{playerLabel(player)}</span>
              <span className={styles.playerMeta}>{player.primary_position || 'No position'}</span>
            </span>
            <span className={styles.playerMeta}>{player.squad_number ? `#${player.squad_number}` : ''}</span>
          </label>
        ))}
        {filtered.length === 0 && <div className={styles.emptyText}>No active players match this filter.</div>}
      </div>
    </div>
  );
};

export default TrainingPlayerSelector;
