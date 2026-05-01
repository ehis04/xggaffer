import { useCallback, useEffect, useMemo, useState } from 'react';
import { trainingApi } from '../../../../services/api';
import { AttendanceTable } from '../../../../components/training/AttendanceTable';
import { TrainingBlockEditor } from '../../../../components/training/TrainingBlockEditor';
import { TrainingPlayerSelector } from '../../../../components/training/TrainingPlayerSelector';
import { TrainingSessionCard } from '../../../../components/training/TrainingSessionCard';
import type { ClubContext } from '../IndividualClubBase';
import type {
  CreateTrainingSessionPayload,
  TrainingAttendanceUpdate,
  TrainingSession,
  TrainingSessionListItem,
  TrainingSessionStatus,
  TrainingSessionType,
} from '../../../../types/training';
import styles from './css/TrainingTab.module.css';

interface Props {
  ctx: ClubContext;
}

interface FormState {
  title: string;
  status: TrainingSessionStatus;
  session_type: TrainingSessionType;
  intensity: 'low' | 'medium' | 'high';
  start_datetime: string;
  end_datetime: string;
  location: string;
  is_mandatory: boolean;
  main_objective: string;
  secondary_objectives: string;
  notes: string;
}

const emptyForm = (): FormState => {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  start.setHours(start.getHours() + 1);
  const end = new Date(start);
  end.setHours(end.getHours() + 1);

  return {
    title: '',
    status: 'draft',
    session_type: 'tactical',
    intensity: 'medium',
    start_datetime: start.toISOString().slice(0, 16),
    end_datetime: end.toISOString().slice(0, 16),
    location: '',
    is_mandatory: true,
    main_objective: '',
    secondary_objectives: '',
    notes: '',
  };
};

const toDatetimeLocal = (value: string | null) => value ? value.slice(0, 16) : '';

const payloadFromForm = (form: FormState): CreateTrainingSessionPayload => ({
  title: form.title.trim(),
  status: form.status,
  session_type: form.session_type,
  intensity: form.intensity,
  start_datetime: new Date(form.start_datetime).toISOString(),
  end_datetime: form.end_datetime ? new Date(form.end_datetime).toISOString() : null,
  location: form.location.trim(),
  is_mandatory: form.is_mandatory,
  main_objective: form.main_objective.trim(),
  secondary_objectives: form.secondary_objectives.trim(),
  notes: form.notes.trim(),
});

const sessionTypeOptions: { value: TrainingSessionType; label: string }[] = [
  { value: 'technical', label: 'Technical' },
  { value: 'tactical', label: 'Tactical' },
  { value: 'fitness', label: 'Fitness' },
  { value: 'set_pieces', label: 'Set pieces' },
  { value: 'recovery', label: 'Recovery' },
  { value: 'match_preparation', label: 'Match preparation' },
  { value: 'goalkeeper', label: 'Goalkeeper' },
  { value: 'other', label: 'Other' },
];

const groupedStatuses: { value: TrainingSessionStatus; label: string }[] = [
  { value: 'published', label: 'Upcoming' },
  { value: 'draft', label: 'Drafts' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

const formatDetailDate = (value: string) =>
  new Date(value).toLocaleString('en-IE', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });

const TrainingTab = ({ ctx }: Props) => {
  const { clubId, clubPlayers, canManage } = ctx;
  const [sessions, setSessions] = useState<TrainingSessionListItem[]>([]);
  const [selected, setSelected] = useState<TrainingSession | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(() => emptyForm());
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await trainingApi.listSessions(clubId, search ? { search } : undefined);
      setSessions(data);
      if (!selectedId && data.length > 0) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load training sessions.');
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, [clubId, search, selectedId]);

  const loadSelected = useCallback(async () => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    try {
      setDetailLoading(true);
      setActionError(null);
      const data = await trainingApi.getSession(clubId, selectedId);
      setSelected(data);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to load session details.');
      setSelected(null);
    } finally {
      setDetailLoading(false);
    }
  }, [clubId, selectedId]);

  useEffect(() => { void loadSessions(); }, [loadSessions]);
  useEffect(() => { void loadSelected(); }, [loadSelected]);

  const grouped = useMemo(() => {
    const map = new Map<TrainingSessionStatus, TrainingSessionListItem[]>();
    groupedStatuses.forEach((status) => map.set(status.value, []));
    sessions.forEach((session) => {
      map.get(session.status)?.push(session);
    });
    return map;
  }, [sessions]);

  const assignedIds = useMemo(
    () => selected?.players.map((player) => player.club_player) ?? [],
    [selected]
  );

  const fillEditForm = (session: TrainingSession) => {
    setForm({
      title: session.title,
      status: session.status,
      session_type: session.session_type,
      intensity: session.intensity,
      start_datetime: toDatetimeLocal(session.start_datetime),
      end_datetime: toDatetimeLocal(session.end_datetime),
      location: session.location,
      is_mandatory: session.is_mandatory,
      main_objective: session.main_objective,
      secondary_objectives: session.secondary_objectives,
      notes: session.notes,
    });
    setEditingId(session.id);
    setShowCreate(true);
  };

  const resetForm = () => {
    setForm(emptyForm());
    setEditingId(null);
    setShowCreate(true);
  };

  const submitSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    try {
      setSaving(true);
      setActionError(null);
      const payload = payloadFromForm(form);
      const saved = editingId
        ? await trainingApi.updateSession(clubId, editingId, payload)
        : await trainingApi.createSession(clubId, payload);
      setSelectedId(saved.id);
      setSelected(saved);
      setShowCreate(false);
      setEditingId(null);
      setForm(emptyForm());
      await loadSessions();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to save training session.');
    } finally {
      setSaving(false);
    }
  };

  const deleteSelected = async () => {
    if (!selected || !window.confirm('Delete this training session?')) return;
    try {
      setSaving(true);
      await trainingApi.deleteSession(clubId, selected.id);
      setSelected(null);
      setSelectedId(null);
      await loadSessions();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete training session.');
    } finally {
      setSaving(false);
    }
  };

  const refreshDetailAndList = async () => {
    await Promise.all([loadSelected(), loadSessions()]);
  };

  const completeSession = async () => {
    if (!selected) return;
    try {
      setSaving(true);
      const updated = await trainingApi.completeSession(clubId, selected.id, {
        what_went_well: selected.what_went_well,
        needs_improvement: selected.needs_improvement,
        next_focus: selected.next_focus,
        squad_notes: selected.squad_notes,
      });
      setSelected(updated);
      await loadSessions();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to complete session.');
    } finally {
      setSaving(false);
    }
  };

  const updateReviewField = (field: keyof Pick<TrainingSession, 'what_went_well' | 'needs_improvement' | 'next_focus' | 'squad_notes'>, value: string) => {
    setSelected((prev) => prev ? { ...prev, [field]: value } : prev);
  };

  return (
    <div className={styles.tabContent}>
      <div className={styles.topBar}>
        <div>
          <h2 className={styles.title}>Training Sessions</h2>
          <p className={styles.subtitle}>Plan sessions, assign players, record attendance, and close the loop after training.</p>
        </div>
        {canManage && (
          <button type="button" className={styles.primaryBtn} onClick={resetForm}>
            New session
          </button>
        )}
      </div>

      {actionError && <div className={styles.noticeError}>{actionError}</div>}

      <div className={styles.toolbar}>
        <input
          className={styles.input}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by title, objective, location, opponent"
        />
      </div>

      {showCreate && canManage && (
        <form className={styles.panel} onSubmit={submitSession}>
          <div className={styles.formGrid}>
            <input className={styles.input} value={form.title} onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))} placeholder="Session title" />
            <select className={styles.select} value={form.status} onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as TrainingSessionStatus }))}>
              {groupedStatuses.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
            </select>
            <select className={styles.select} value={form.session_type} onChange={(e) => setForm((p) => ({ ...p, session_type: e.target.value as TrainingSessionType }))}>
              {sessionTypeOptions.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>
            <select className={styles.select} value={form.intensity} onChange={(e) => setForm((p) => ({ ...p, intensity: e.target.value as FormState['intensity'] }))}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            <input className={styles.input} type="datetime-local" value={form.start_datetime} onChange={(e) => setForm((p) => ({ ...p, start_datetime: e.target.value }))} />
            <input className={styles.input} type="datetime-local" value={form.end_datetime} onChange={(e) => setForm((p) => ({ ...p, end_datetime: e.target.value }))} />
            <input className={styles.input} value={form.location} onChange={(e) => setForm((p) => ({ ...p, location: e.target.value }))} placeholder="Location" />
            <label className={styles.checkboxLabel}>
              <input type="checkbox" checked={form.is_mandatory} onChange={(e) => setForm((p) => ({ ...p, is_mandatory: e.target.checked }))} />
              Mandatory
            </label>
            <textarea className={`${styles.textarea} ${styles.fullWidth}`} value={form.main_objective} onChange={(e) => setForm((p) => ({ ...p, main_objective: e.target.value }))} placeholder="Main objective" />
            <textarea className={`${styles.textarea} ${styles.fullWidth}`} value={form.secondary_objectives} onChange={(e) => setForm((p) => ({ ...p, secondary_objectives: e.target.value }))} placeholder="Secondary objectives" />
            <textarea className={`${styles.textarea} ${styles.fullWidth}`} value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} placeholder="Notes" />
          </div>
          <div className={styles.actions}>
            <button type="submit" className={styles.primaryBtn} disabled={saving || !form.title.trim()}>
              {saving ? 'Saving...' : 'Save session'}
            </button>
            <button type="button" className={styles.ghostBtn} onClick={() => { setShowCreate(false); setEditingId(null); }} disabled={saving}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className={styles.layout}>
        <aside className={styles.listColumn}>
          {loading ? (
            <div className={styles.empty}>Loading training sessions...</div>
          ) : error ? (
            <div className={styles.noticeError}>{error}</div>
          ) : sessions.length === 0 ? (
            <div className={styles.empty}>No training sessions yet.</div>
          ) : (
            groupedStatuses.map((group) => {
              const groupSessions = grouped.get(group.value) ?? [];
              if (groupSessions.length === 0) return null;
              return (
                <section key={group.value} className={styles.sessionGroup}>
                  <h3 className={styles.groupTitle}>{group.label}</h3>
                  {groupSessions.map((session) => (
                    <TrainingSessionCard
                      key={session.id}
                      session={session}
                      active={selectedId === session.id}
                      onSelect={() => setSelectedId(session.id)}
                    />
                  ))}
                </section>
              );
            })
          )}
        </aside>

        <section className={styles.detailColumn}>
          {detailLoading ? (
            <div className={styles.panel}>Loading session...</div>
          ) : !selected ? (
            <div className={styles.empty}>Select a session to review the plan.</div>
          ) : (
            <>
              <div className={styles.panel}>
                <div className={styles.detailHeader}>
                  <div>
                    <h2 className={styles.detailTitle}>{selected.title}</h2>
                    <p className={styles.detailMeta}>
                      {formatDetailDate(selected.start_datetime)} · {selected.session_type_display} · {selected.intensity_display}
                    </p>
                  </div>
                  {canManage && (
                    <div className={styles.actions}>
                      <button type="button" className={styles.ghostBtn} onClick={() => fillEditForm(selected)}>Edit</button>
                      <button type="button" className={styles.dangerBtn} onClick={deleteSelected}>Delete</button>
                    </div>
                  )}
                </div>
                {selected.main_objective && <p className={styles.objective}>{selected.main_objective}</p>}
                <div className={styles.detailStats}>
                  <span>{selected.assigned_player_count} assigned</span>
                  <span>{selected.attended_count} attended</span>
                  <span>{selected.block_count} blocks</span>
                  {selected.location && <span>{selected.location}</span>}
                </div>
              </div>

              <div className={styles.panel}>
                <h3 className={styles.panelTitle}>Plan blocks</h3>
                <TrainingBlockEditor
                  blocks={selected.blocks}
                  disabled={!canManage}
                  onCreate={async (payload) => {
                    await trainingApi.createBlock(clubId, selected.id, payload);
                    await refreshDetailAndList();
                  }}
                  onDelete={async (blockId) => {
                    await trainingApi.deleteBlock(clubId, selected.id, blockId);
                    await refreshDetailAndList();
                  }}
                />
              </div>

              <div className={styles.panel}>
                <h3 className={styles.panelTitle}>Assign players</h3>
                <TrainingPlayerSelector
                  players={clubPlayers}
                  assignedIds={assignedIds}
                  disabled={!canManage}
                  onAssignAll={async () => {
                    const updated = await trainingApi.assignPlayers(clubId, selected.id, { mode: 'all' });
                    setSelected(updated);
                    await loadSessions();
                  }}
                  onAssignSelected={async (ids) => {
                    const updated = await trainingApi.assignPlayers(clubId, selected.id, { mode: 'selected', club_player_ids: ids });
                    setSelected(updated);
                    await loadSessions();
                  }}
                />
              </div>

              <div className={styles.panel}>
                <h3 className={styles.panelTitle}>Attendance</h3>
                <AttendanceTable
                  players={selected.players}
                  disabled={!canManage}
                  onSave={async (updates: TrainingAttendanceUpdate[]) => {
                    const updated = await trainingApi.updateAttendance(clubId, selected.id, updates);
                    setSelected(updated);
                    await loadSessions();
                  }}
                />
              </div>

              <div className={styles.panel}>
                <h3 className={styles.panelTitle}>Post-session review</h3>
                <div className={styles.reviewGrid}>
                  <textarea className={styles.textarea} value={selected.what_went_well} onChange={(e) => updateReviewField('what_went_well', e.target.value)} placeholder="What went well" disabled={!canManage} />
                  <textarea className={styles.textarea} value={selected.needs_improvement} onChange={(e) => updateReviewField('needs_improvement', e.target.value)} placeholder="Needs improvement" disabled={!canManage} />
                  <textarea className={styles.textarea} value={selected.next_focus} onChange={(e) => updateReviewField('next_focus', e.target.value)} placeholder="Next session focus" disabled={!canManage} />
                  <textarea className={styles.textarea} value={selected.squad_notes} onChange={(e) => updateReviewField('squad_notes', e.target.value)} placeholder="Squad notes" disabled={!canManage} />
                </div>
                {canManage && (
                  <div className={styles.actions}>
                    <button type="button" className={styles.primaryBtn} onClick={completeSession} disabled={saving}>
                      Complete session
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};

export default TrainingTab;
