import { useEffect, useState } from 'react';
import type {
  TrainingAttendanceStatus,
  TrainingAttendanceUpdate,
  TrainingSessionPlayer,
} from '../../types/training';
import styles from './css/TrainingComponents.module.css';

interface Props {
  players: TrainingSessionPlayer[];
  disabled?: boolean;
  onSave: (updates: TrainingAttendanceUpdate[]) => Promise<void>;
}

const statuses: { value: TrainingAttendanceStatus; label: string }[] = [
  { value: 'invited', label: 'Invited' },
  { value: 'attended', label: 'Attended' },
  { value: 'absent', label: 'Absent' },
  { value: 'late', label: 'Late' },
  { value: 'excused', label: 'Excused' },
  { value: 'injured', label: 'Injured' },
  { value: 'not_selected', label: 'Not selected' },
];

export const AttendanceTable = ({ players, disabled = false, onSave }: Props) => {
  const [updates, setUpdates] = useState<TrainingAttendanceUpdate[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setUpdates(players.map((player) => ({
      id: player.id,
      attendance_status: player.attendance_status,
      rpe_score: player.rpe_score,
      coach_notes: player.coach_notes,
      injury_note: player.injury_note,
      performance_note: player.performance_note,
    })));
  }, [players]);

  const patchUpdate = (id: number, patch: Partial<TrainingAttendanceUpdate>) => {
    setUpdates((prev) => prev.map((item) => item.id === id ? { ...item, ...patch } : item));
  };

  const submit = async () => {
    setSaving(true);
    try {
      await onSave(updates);
    } finally {
      setSaving(false);
    }
  };

  if (players.length === 0) {
    return <div className={styles.emptyText}>Assign players before taking attendance.</div>;
  }

  return (
    <div className={styles.attendanceTable}>
      <div className={styles.attendanceHeader}>
        <span className={styles.playerMeta}>{players.length} players</span>
        <button type="button" className={styles.primaryBtn} disabled={disabled || saving} onClick={submit}>
          Save attendance
        </button>
      </div>
      {players.map((player) => {
        const update = updates.find((item) => item.id === player.id);
        return (
          <div key={player.id} className={styles.attendanceRow}>
            <div>
              <div className={styles.playerName}>{player.player_name}</div>
              <div className={styles.playerMeta}>{player.primary_position || 'No position'}</div>
            </div>
            <select
              className={styles.select}
              value={update?.attendance_status ?? player.attendance_status}
              onChange={(e) => patchUpdate(player.id, { attendance_status: e.target.value as TrainingAttendanceStatus })}
              disabled={disabled}
            >
              {statuses.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
            </select>
            <input
              className={styles.input}
              type="number"
              min={1}
              max={10}
              value={update?.rpe_score ?? ''}
              onChange={(e) => patchUpdate(player.id, { rpe_score: e.target.value ? Number(e.target.value) : null })}
              placeholder="RPE"
              disabled={disabled}
            />
            <input
              className={styles.input}
              value={update?.coach_notes ?? ''}
              onChange={(e) => patchUpdate(player.id, { coach_notes: e.target.value })}
              placeholder="Coach note"
              disabled={disabled}
            />
          </div>
        );
      })}
    </div>
  );
};

export default AttendanceTable;
