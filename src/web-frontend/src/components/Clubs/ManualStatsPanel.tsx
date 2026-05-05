import { useState } from 'react';
import { clubsApi } from '../../services/api';
import type { ClubPlayer } from '../../types/clubPlayers';
import type { ClubPlayerManualStats, CreateOrUpdateClubPlayerManualStatsPayload } from '../../types/club';
import styles from './css/ManualStatsPanel.module.css';

interface Props {
  clubId: number;
  player: ClubPlayer;
  currentStats: ClubPlayerManualStats | null;
  canManage: boolean;
  onUpdate: (stats: ClubPlayerManualStats) => void;
}

interface StatGroup {
  label: string;
  fields: { key: keyof ClubPlayerManualStats & string; label: string; decimal?: boolean }[];
}

const STAT_GROUPS: StatGroup[] = [
  {
    label: 'General',
    fields: [
      { key: 'season', label: 'Season' },
      { key: 'appearances', label: 'Apps' },
      { key: 'minutes_played', label: 'Minutes' },
      { key: 'goals', label: 'Goals' },
      { key: 'assists', label: 'Assists' },
    ],
  },
  {
    label: 'Attacking',
    fields: [
      { key: 'xg', label: 'xG', decimal: true },
      { key: 'npxg', label: 'npxG', decimal: true },
      { key: 'xa', label: 'xA', decimal: true },
      { key: 'shots', label: 'Shots' },
      { key: 'shots_on_target', label: 'On target' },
      { key: 'key_passes', label: 'Key passes' },
      { key: 'dribbles_completed', label: 'Dribbles' },
    ],
  },
  {
    label: 'Progression',
    fields: [
      { key: 'progressive_passes', label: 'Prog. passes' },
      { key: 'progressive_carries', label: 'Prog. carries' },
    ],
  },
  {
    label: 'Defending',
    fields: [
      { key: 'tackles', label: 'Tackles' },
      { key: 'interceptions', label: 'Interceptions' },
      { key: 'aerials_won', label: 'Aerials won' },
      { key: 'clearances', label: 'Clearances' },
      { key: 'blocks', label: 'Blocks' },
    ],
  },
  {
    label: 'Goalkeeping',
    fields: [
      { key: 'saves', label: 'Saves' },
      { key: 'save_percentage', label: 'Save %', decimal: true },
      { key: 'clean_sheets', label: 'Clean sheets' },
      { key: 'goals_conceded', label: 'Goals conceded' },
    ],
  },
];

const fmt = (v: string | number | null | undefined, decimal?: boolean): string => {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  return isNaN(n) ? String(v) : decimal ? n.toFixed(2) : String(n);
};

type FormValues = Partial<Record<keyof ClubPlayerManualStats & string, string>>;

const statsToForm = (s: ClubPlayerManualStats): FormValues => {
  const out: FormValues = {};
  (Object.keys(s) as Array<keyof ClubPlayerManualStats>).forEach((k) => {
    const v = s[k];
    out[k] = v !== null && v !== undefined ? String(v) : '';
  });
  return out;
};

const CURRENT_SEASON = (() => {
  const now = new Date();
  const y = now.getFullYear();
  return now.getMonth() >= 7 ? `${y}/${y + 1}` : `${y - 1}/${y}`;
})();

export const ManualStatsPanel = ({ clubId, player, currentStats, canManage, onUpdate }: Props) => {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<FormValues>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeGroup, setActiveGroup] = useState('General');

  const startEditing = () => {
    setForm(currentStats ? statsToForm(currentStats) : { season: CURRENT_SEASON });
    setEditing(true);
    setError(null);
  };

  const handleChange = (key: keyof ClubPlayerManualStats, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    if (!form.season?.trim()) { setError('Season is required (e.g. 2024/25).'); return; }
    try {
      setSaving(true); setError(null);
      const payload: CreateOrUpdateClubPlayerManualStatsPayload = { season: form.season.trim() };
      STAT_GROUPS.forEach((g) => {
        g.fields.forEach(({ key }) => {
          if (key === 'season') return;
          const v = form[key];
          if (v !== undefined && v !== '') {
            (payload as Record<string, unknown>)[key] = Number(v);
          }
        });
      });
      const updated = await clubsApi.manualStats.upsert(clubId, player.id, payload);
      onUpdate(updated);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save stats.');
    } finally {
      setSaving(false);
    }
  };

  const playerName = player.display_name || `${player.first_name} ${player.last_name}`.trim();

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div>
          <span className={styles.title}>Manual stats</span>
          {currentStats && (
            <span className={styles.season}>{currentStats.season}</span>
          )}
        </div>
        {canManage && (
          <button type="button" className={styles.editBtn} onClick={editing ? () => setEditing(false) : startEditing}>
            {editing ? 'Cancel' : currentStats ? 'Edit' : 'Add stats'}
          </button>
        )}
      </div>

      {!currentStats && !editing && (
        <p className={styles.empty}>No stats recorded for {playerName}.</p>
      )}

      {error && <div className={styles.error}>{error}</div>}

      {editing ? (
        <div className={styles.editArea}>
          <div className={styles.groupTabs}>
            {STAT_GROUPS.map((g) => (
              <button key={g.label} type="button"
                className={`${styles.groupTab}${activeGroup === g.label ? ' ' + styles.groupTabActive : ''}`}
                onClick={() => setActiveGroup(g.label)}>
                {g.label}
              </button>
            ))}
          </div>

          {STAT_GROUPS.filter((g) => g.label === activeGroup).map((g) => (
            <div key={g.label} className={styles.fieldGrid}>
              {g.fields.map(({ key, label }) => (
                <div key={key} className={styles.fieldGroup}>
                  <label className={styles.label} htmlFor={`ms_${key}`}>{label}</label>
                  <input id={`ms_${key}`} type={key === 'season' ? 'text' : 'number'}
                    step={key === 'xg' || key === 'npxg' || key === 'xa' || key === 'save_percentage' ? '0.001' : '1'}
                    min="0" className={styles.input}
                    value={form[key] ?? ''}
                    onChange={(e) => handleChange(key, e.target.value)}
                    placeholder={key === 'season' ? 'e.g. 2024/25' : '—'}
                  />
                </div>
              ))}
            </div>
          ))}

          <div className={styles.actions}>
            <button type="button" className={styles.saveBtn} disabled={saving} onClick={handleSave}>
              {saving ? 'Saving...' : 'Save stats'}
            </button>
          </div>
        </div>
      ) : currentStats && (
        <div className={styles.statView}>
          <div className={styles.groupTabs}>
            {STAT_GROUPS.map((g) => (
              <button key={g.label} type="button"
                className={`${styles.groupTab}${activeGroup === g.label ? ' ' + styles.groupTabActive : ''}`}
                onClick={() => setActiveGroup(g.label)}>
                {g.label}
              </button>
            ))}
          </div>

          {STAT_GROUPS.filter((g) => g.label === activeGroup).map((g) => (
            <div key={g.label} className={styles.statGrid}>
              {g.fields.filter((f) => f.key !== 'season').map(({ key, label, decimal }) => (
                <div key={key} className={styles.statItem}>
                  <span className={styles.statLabel}>{label}</span>
                  <span className={styles.statValue}>
                    {fmt(currentStats[key as keyof ClubPlayerManualStats] as string | number | null, decimal)}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};