import { useState } from 'react';
import { clubsApi } from '../../services/api';
import type { ClubPlayer } from '../../types/clubPlayers';
import type { ClubPlayerInjury, CreateClubPlayerInjuryPayload, PlayerAvailabilityStatus } from '../../types/club';
import styles from './css/InjuryModal.module.css';

interface Props {
  clubId: number;
  player: ClubPlayer;
  currentInjury: ClubPlayerInjury | null;
  onClose: () => void;
  onSaved: () => void;
}

const INJURY_TYPES = [
  { value: 'muscle', label: 'Muscle' },
  { value: 'ligament', label: 'Ligament' },
  { value: 'bone', label: 'Bone/Fracture' },
  { value: 'tendon', label: 'Tendon' },
  { value: 'cartilage', label: 'Cartilage' },
  { value: 'head', label: 'Head/Concussion' },
  { value: 'illness', label: 'Illness' },
  { value: 'suspension', label: 'Suspension' },
  { value: 'other', label: 'Other' },
];

const SEVERITY_OPTIONS = [
  { value: 'minor', label: 'Minor' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'severe', label: 'Severe' },
];

const STATUS_OPTIONS: { value: Exclude<PlayerAvailabilityStatus, 'AV'>; label: string }[] = [
  { value: 'IN', label: 'Injured' },
  { value: 'DO', label: 'In doubt' },
  { value: 'SU', label: 'Suspended' },
];

const today = () => new Date().toISOString().slice(0, 10);

export const InjuryModal = ({ clubId, player, currentInjury, onClose, onSaved }: Props) => {
  const [injuryType, setInjuryType] = useState(currentInjury?.injury_type ?? 'muscle');
  const [severity, setSeverity] = useState(currentInjury?.severity ?? 'minor');
  const [availStatus, setAvailStatus] = useState<Exclude<PlayerAvailabilityStatus, 'AV'>>(
    (currentInjury?.availability_status as Exclude<PlayerAvailabilityStatus, 'AV'>) ?? 'IN',
  );
  const [injuredAt, setInjuredAt] = useState(currentInjury?.injured_at ?? today());
  const [estimatedReturn, setEstimatedReturn] = useState(currentInjury?.estimated_return ?? '');
  const [notes, setNotes] = useState(currentInjury?.notes ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const playerName = player.display_name || `${player.first_name} ${player.last_name}`.trim();

  const handleSave = async () => {
    if (!injuredAt) { setError('Injury date is required.'); return; }
    try {
      setSaving(true);
      setError(null);
      const payload: CreateClubPlayerInjuryPayload = {
        injury_type: injuryType as CreateClubPlayerInjuryPayload['injury_type'],
        severity: severity as CreateClubPlayerInjuryPayload['severity'],
        availability_status: availStatus,
        injured_at: injuredAt,
        estimated_return: estimatedReturn || null,
        notes: notes.trim(),
      };
      await clubsApi.injuries.create(clubId, player.id, payload);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save injury.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <span className={styles.title}>
            {currentInjury ? 'Update injury' : 'Log injury'} — {playerName}
          </span>
          <button type="button" className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Availability status</label>
          <div className={styles.radioRow}>
            {STATUS_OPTIONS.map((opt) => (
              <label key={opt.value} className={styles.radioLabel}>
                <input type="radio" name="avail_status" value={opt.value}
                  checked={availStatus === opt.value}
                  onChange={() => setAvailStatus(opt.value)} />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <div className={styles.row}>
          <div className={styles.fieldGroup}>
            <label className={styles.label} htmlFor="inj_type">Injury type</label>
            <select id="inj_type" className={styles.select}
              value={injuryType} onChange={(e) => setInjuryType(e.target.value as CreateClubPlayerInjuryPayload['injury_type'])}>
              {INJURY_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div className={styles.fieldGroup}>
            <label className={styles.label} htmlFor="inj_severity">Severity</label>
            <select id="inj_severity" className={styles.select}
              value={severity} onChange={(e) => setSeverity(e.target.value as CreateClubPlayerInjuryPayload['severity'])}>
              {SEVERITY_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>

        <div className={styles.row}>
          <div className={styles.fieldGroup}>
            <label className={styles.label} htmlFor="inj_date">Injury date</label>
            <input id="inj_date" type="date" className={styles.input}
              value={injuredAt} onChange={(e) => setInjuredAt(e.target.value)} />
          </div>
          <div className={styles.fieldGroup}>
            <label className={styles.label} htmlFor="inj_return">Estimated return</label>
            <input id="inj_return" type="date" className={styles.input}
              value={estimatedReturn} onChange={(e) => setEstimatedReturn(e.target.value)} />
          </div>
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label} htmlFor="inj_notes">Notes</label>
          <textarea id="inj_notes" className={styles.textarea} rows={3}
            value={notes} onChange={(e) => setNotes(e.target.value)}
            placeholder="Optional notes..." />
        </div>

        <div className={styles.actions}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button type="button" className={styles.saveBtn} disabled={saving} onClick={handleSave}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};