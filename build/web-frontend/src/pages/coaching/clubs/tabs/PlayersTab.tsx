import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { clubsApi } from '../../../../services/api';
import { playerdataApi } from '../../../../services/api/playerdataApi';
import CompactPlayerPreview from '../../../../components/playerdata/CompactPlayerPreview';
import { InjuryModal } from '../../../../components/Clubs/InjuryModal';
import { ManualStatsPanel } from '../../../../components/Clubs/ManualStatsPanel';
import type { ClubContext } from '../IndividualClubBase';
import type {
  ClubPlayer,
  CreateClubPlayerPayload,
  UpdateClubPlayerPayload,
} from '../../../../types/clubPlayers';
import type { ClubPlayerInjury, ClubPlayerManualStats } from '../../../../types/club';
import type { PlayerDataFilters, PlayerDataMetric, PlayerSeasonSummary } from '../../../../types/playerdata';
import { statusConfig } from '../../../../components/Dashboard/functions/statusConfig';
import { getCurrentFootballSeason } from '../../../../utils/footballSeason';
import styles from './css/PlayersTab.module.css';
import { SectionSkeleton } from '../../../../common/components/SectionSkeleton';
import { InlineRetry } from '../../../../common/components/InlineRetry';

interface Props { ctx: ClubContext }

interface PlayerFormState {
  first_name: string; last_name: string; display_name: string;
  squad_number: string; primary_position: string; secondary_positions: string;
  preferred_foot: string; date_of_birth: string; height_cm: string;
  is_public: boolean; is_active: boolean;
}

const POSITION_OPTIONS = [
  'GK','RB','RWB','CB','RCB','LCB','LB','LWB',
  'CDM','RDM','LDM','CM','RM','LM','CAM','RAM','LAM','RW','LW','CF','ST',
];
const FOOT_OPTIONS = [
  { value: '', label: 'Not set' },{ value: 'l', label: 'Left' },
  { value: 'r', label: 'Right' },{ value: 'b', label: 'Both' },
];

const emptyForm = (): PlayerFormState => ({
  first_name: '', last_name: '', display_name: '', squad_number: '',
  primary_position: '', secondary_positions: '', preferred_foot: '',
  date_of_birth: '', height_cm: '', is_public: false, is_active: true,
});

const toFormState = (p: ClubPlayer): PlayerFormState => ({
  first_name: p.first_name || '', last_name: p.last_name || '',
  display_name: p.display_name || '',
  squad_number: p.squad_number?.toString() || '',
  primary_position: p.primary_position || '',
  secondary_positions: (p.secondary_positions || []).join(', '),
  preferred_foot: p.preferred_foot || '', date_of_birth: p.date_of_birth || '',
  height_cm: p.height_cm?.toString() || '',
  is_public: Boolean(p.is_public), is_active: Boolean(p.is_active),
});

const getLabel = (p: ClubPlayer): string =>
  p.display_name?.trim() || p.full_name?.trim() ||
  `${p.first_name} ${p.last_name}`.trim() || `Player #${p.id}`;

const parsePos = (v: string): string[] =>
  v.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean);

const normalizeError = (err: unknown): string => {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  if (err && typeof err === 'object') {
    const vals = Object.values(err as Record<string, unknown>)
      .flatMap((v) => Array.isArray(v) ? v.map(String) : [String(v)]);
    if (vals.length) return vals.join(' ');
  }
  return 'Something went wrong.';
};

const fmtSync = (v?: string | null): string => {
  if (!v) return 'Never synced';
  const d = new Date(v);
  return isNaN(d.getTime())
    ? 'Sync unavailable'
    : `Last synced ${d.toLocaleString('en-IE', { dateStyle: 'medium', timeStyle: 'short' })}`;
};

const latestSync = (players: ClubPlayer[]): string | null => {
  const ts = players.map((p) => p.last_synced_at)
    .filter((v): v is string => Boolean(v))
    .map((v) => new Date(v).getTime()).filter((v) => !isNaN(v));
  return ts.length ? new Date(Math.max(...ts)).toISOString() : null;
};

const buildProfileUrl = (
  playerId: number, clubId: number, clubPlayerId: number | null,
  filters: PlayerDataFilters | null,
): string => {
  const p = new URLSearchParams({ playerId: String(playerId) });
  if (clubId > 0) p.set('fromClubId', String(clubId));
  if (clubPlayerId && clubPlayerId > 0) p.set('clubPlayerId', String(clubPlayerId));
  if (filters?.season) p.set('season', filters.season);
  if (filters?.provider) p.set('provider', filters.provider);
  if (filters?.competition_code) p.set('competition_code', filters.competition_code);
  if (filters?.competition_name) p.set('competition_name', filters.competition_name);
  return `/coaching/playerdata/player?${p.toString()}`;
};

const resolveCanonicalId = (p?: ClubPlayer | null): number | null => {
  if (!p) return null;
  const v = p.canonical_player_id ?? p.player_id ?? null;
  return typeof v === 'number' && v > 0 ? v : null;
};

const UNDERSTAT_PREFERRED_KEYS = new Set(['xg', 'npxg', 'xa']);

const mergePlayerSummaries = (
  understat: PlayerSeasonSummary | null,
  sofascore: PlayerSeasonSummary | null,
): PlayerSeasonSummary | null => {
  if (!understat && !sofascore) return null;
  const metricsMap = new Map<string, PlayerDataMetric>();
  (sofascore?.metrics ?? []).forEach((m) => metricsMap.set(m.key, m));
  (understat?.metrics ?? []).forEach((m) => {
    if (UNDERSTAT_PREFERRED_KEYS.has(m.key) || !metricsMap.has(m.key)) {
      metricsMap.set(m.key, m);
    }
  });
  return { ...(understat ?? sofascore!), metrics: Array.from(metricsMap.values()) };
};

const PlayersTab = ({ ctx }: Props) => {
  const { clubId, canManage } = ctx;
  const navigate = useNavigate();

  const [players, setPlayers] = useState<ClubPlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [syncErr, setSyncErr] = useState<string | null>(null);
  const [editingPlayer, setEditingPlayer] = useState<ClubPlayer | null>(null);
  const [form, setForm] = useState<PlayerFormState>(emptyForm());
  const [showAddForm, setShowAddForm] = useState(false);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [summary, setSummary] = useState<PlayerSeasonSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryErr, setSummaryErr] = useState<string | null>(null);
  const [manualStats, setManualStats] = useState<ClubPlayerManualStats | null>(null);
  const [injuries, setInjuries] = useState<ClubPlayerInjury[]>([]);

  const [showInjuryModal, setShowInjuryModal] = useState(false);

  const loadPlayers = useCallback(async () => {
    const data = await clubsApi.listPlayers(clubId);
    setPlayers(data);
  }, [clubId]);

  useEffect(() => {
    const init = async () => {
      try { setLoading(true); await loadPlayers(); }
      catch (err) { setError(normalizeError(err)); }
      finally { setLoading(false); }
    };
    void init();
  }, [loadPlayers]);

  const selectedPlayer = useMemo(() => players.find((p) => p.id === selectedId) ?? null, [players, selectedId]);
  const canonicalId = useMemo(() => resolveCanonicalId(selectedPlayer), [selectedPlayer]);
  const currentSeason = getCurrentFootballSeason();

  useEffect(() => {
    if (!selectedPlayer) {
      setManualStats(null); setInjuries([]); return;
    }

    void Promise.allSettled([
      clubsApi.manualStats.list(clubId, selectedPlayer.id),
      clubsApi.injuries.list(clubId, selectedPlayer.id),
    ]).then(([stats, inj]) => {
      setManualStats(stats.status === 'fulfilled' ? (stats.value[0] ?? null) : null);
      setInjuries(inj.status === 'fulfilled' ? inj.value : []);
    });
  }, [selectedPlayer, clubId]);

  useEffect(() => {
    if (!selectedPlayer || !canonicalId) {
      setSummary(null);
      setSummaryErr(null);
      setSummaryLoading(false);
      return;
    }
    let active = true;
    const load = async () => {
      setSummaryLoading(true); setSummaryErr(null);
      try {
        const [uResult, ssResult] = await Promise.allSettled([
          playerdataApi.getPlayerSeasonSummary(canonicalId, { season: currentSeason, provider: 'understat' }),
          playerdataApi.getPlayerSeasonSummary(canonicalId, { season: currentSeason, provider: 'sofascore' }),
        ]);
        const merged = mergePlayerSummaries(
          uResult.status === 'fulfilled' ? uResult.value : null,
          ssResult.status === 'fulfilled' ? ssResult.value : null,
        );
        if (active) {
          setSummary(merged);
          if (!merged) setSummaryErr(`No ${currentSeason} data available for this player.`);
        }
      } catch (err) { if (active) { setSummary(null); setSummaryErr(normalizeError(err)); } }
      finally { if (active) setSummaryLoading(false); }
    };
    void load();
    return () => { active = false; };
  }, [selectedPlayer, canonicalId, currentSeason]);

  const resetForm = () => { setForm(emptyForm()); setEditingPlayer(null); setFormError(null); setShowAddForm(false); };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      setForm((prev) => ({ ...prev, [name]: (e.target as HTMLInputElement).checked }));
    } else {
      setForm((prev) => ({ ...prev, [name]: value }));
    }
  };

  const buildPayload = (): CreateClubPlayerPayload | UpdateClubPlayerPayload => {
    const base: UpdateClubPlayerPayload = {
      first_name: form.first_name.trim(), last_name: form.last_name.trim(),
      display_name: form.display_name.trim() || '',
      squad_number: form.squad_number ? Number(form.squad_number) : null,
      primary_position: form.primary_position || '',
      secondary_positions: parsePos(form.secondary_positions),
      preferred_foot: form.preferred_foot || '',
      date_of_birth: form.date_of_birth || null,
      height_cm: form.height_cm ? Number(form.height_cm) : null,
      is_public: form.is_public,
    };
    if (editingPlayer) base.is_active = form.is_active;
    return base;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.first_name.trim() || !form.last_name.trim()) { setFormError('First and last name required.'); return; }
    try {
      setSaving(true); setFormError(null);
      if (editingPlayer) await clubsApi.updatePlayer(clubId, editingPlayer.id, buildPayload());
      else await clubsApi.createPlayer(clubId, buildPayload());
      await loadPlayers(); resetForm();
    } catch (err) { setFormError(normalizeError(err)); }
    finally { setSaving(false); }
  };

  const handleSync = async () => {
    try {
      setSyncing(true); setSyncErr(null); setSyncMsg(null);
      const r = await clubsApi.syncClubSquad(clubId);
      await loadPlayers();
      setSyncMsg(`Sync done — ${r.players_created} created, ${r.players_updated} updated.`);
    } catch (err) { setSyncErr(normalizeError(err)); }
    finally { setSyncing(false); }
  };

  const handleResolveInjury = async (injuryId: number) => {
    if (!selectedPlayer) return;
    await clubsApi.injuries.resolve(clubId, selectedPlayer.id, injuryId);
    const [fresh, freshPlayers] = await Promise.all([
      clubsApi.injuries.list(clubId, selectedPlayer.id),
      clubsApi.listPlayers(clubId),
    ]);
    setInjuries(fresh); setPlayers(freshPlayers);
  };

  const syncTime = useMemo(() => latestSync(players), [players]);
  const linkedCount = useMemo(() => players.filter((p) => p.is_linked_to_player).length, [players]);
  const currentInjury = injuries.find((i) => i.is_current) ?? null;
  const avail = (selectedPlayer?.availability_status ?? 'AV') as keyof typeof statusConfig;
  const dot = statusConfig[avail];

  const summaryFilters: PlayerDataFilters | null = summary
    ? {
        provider: summary.context?.provider ?? undefined,
        season: summary.context?.season ?? undefined,
        competition_code: summary.context?.competition_code ?? undefined,
        competition_name: summary.context?.competition_name ?? undefined,
      }
    : null;

  if (loading) return <SectionSkeleton rows={5} height="56px" gap="8px" />;
  if (error) {
    return (
      <InlineRetry
        message={error}
        retrying={retrying}
        onRetry={async () => {
          setRetrying(true);
          setError(null);
          try { await loadPlayers(); } catch (err) { setError(normalizeError(err)); }
          finally { setRetrying(false); }
        }}
      />
    );
  }

  return (
    <div className={styles.tabContent}>
      <div className={styles.topBar}>
        <span className={styles.sectionLabel}>
          {players.length} players · {linkedCount} linked · {fmtSync(syncTime)}
        </span>
        <div className={styles.topBarRight}>
          {canManage && (
            <>
              <button type="button" className={styles.secondaryBtn} onClick={handleSync} disabled={syncing}>
                {syncing ? 'Syncing...' : 'Sync squad'}
              </button>
              <button type="button" className={styles.primaryBtn}
                onClick={() => { setShowAddForm(true); setEditingPlayer(null); setForm(emptyForm()); }}>
                + Add player
              </button>
            </>
          )}
        </div>
      </div>

      {syncErr && <div className={`${styles.notice} ${styles.noticeError}`}>{syncErr}</div>}
      {syncMsg && <div className={styles.notice}>{syncMsg}</div>}

      <div className={styles.layout}>
        <div className={styles.leftCol}>
          {showAddForm && canManage && (
            <div className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>{editingPlayer ? `Edit — ${getLabel(editingPlayer)}` : 'Add player'}</span>
                <button type="button" className={styles.ghostBtn} onClick={resetForm}>Cancel</button>
              </div>
              <form onSubmit={handleSubmit} className={styles.form}>
                {formError && <div className={`${styles.notice} ${styles.noticeError}`}>{formError}</div>}
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="pt_first_name">First name</label>
                    <input id="pt_first_name" name="first_name" className={styles.input} value={form.first_name} onChange={handleInput} required />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="pt_last_name">Last name</label>
                    <input id="pt_last_name" name="last_name" className={styles.input} value={form.last_name} onChange={handleInput} required />
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="pt_display_name">Display name</label>
                  <input id="pt_display_name" name="display_name" className={styles.input} value={form.display_name} onChange={handleInput} placeholder="Optional" />
                </div>
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="pt_squad">Squad no.</label>
                    <input id="pt_squad" name="squad_number" type="number" min="1" max="99" className={styles.input} value={form.squad_number} onChange={handleInput} />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="pt_pos">Position</label>
                    <select id="pt_pos" name="primary_position" className={styles.select} value={form.primary_position} onChange={handleInput}>
                      <option value="">Select</option>
                      {POSITION_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="pt_sec_pos">Secondary positions (comma-separated)</label>
                  <input id="pt_sec_pos" name="secondary_positions" className={styles.input} value={form.secondary_positions} onChange={handleInput} placeholder="e.g. RB, RWB" />
                </div>
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="pt_foot">Preferred foot</label>
                    <select id="pt_foot" name="preferred_foot" className={styles.select} value={form.preferred_foot} onChange={handleInput}>
                      {FOOT_OPTIONS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="pt_dob">Date of birth</label>
                    <input id="pt_dob" name="date_of_birth" type="date" className={styles.input} value={form.date_of_birth} onChange={handleInput} />
                  </div>
                </div>
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="pt_height">Height (cm)</label>
                    <input id="pt_height" name="height_cm" type="number" min="1" className={styles.input} value={form.height_cm} onChange={handleInput} />
                  </div>
                  <div className={styles.checkboxGroup}>
                    <label className={styles.checkboxLabel}>
                      <input type="checkbox" name="is_public" checked={form.is_public} onChange={handleInput} />Public
                    </label>
                    {editingPlayer && (
                      <label className={styles.checkboxLabel}>
                        <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleInput} />Active
                      </label>
                    )}
                  </div>
                </div>
                <div className={styles.formActions}>
                  <button type="submit" className={styles.primaryBtn} disabled={saving}>
                    {saving ? (editingPlayer ? 'Saving...' : 'Creating...') : (editingPlayer ? 'Save changes' : 'Create player')}
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>Roster</span>
              <span className={styles.badge}>{players.length}</span>
            </div>
            {players.length === 0 ? (
              <p className={styles.emptyText}>No players yet.</p>
            ) : (
              <div className={styles.playerList}>
                {players.map((p) => {
                  const isSelected = selectedId === p.id;
                  const pavail = (p.availability_status ?? 'AV') as keyof typeof statusConfig;
                  const pdot = statusConfig[pavail];
                  return (
                    <div key={p.id}
                      className={`${styles.playerRow}${isSelected ? ' ' + styles.playerRowSelected : ''}`}
                      onClick={() => setSelectedId((prev) => prev === p.id ? null : p.id)}>
                      <div className={styles.playerRowLeft}>
                        <div className={styles.availDot} style={{ background: pdot.colour }} title={pdot.label} />
                        <div>
                          <span className={styles.playerName}>{getLabel(p)}</span>
                          <span className={styles.playerMeta}>
                            {p.primary_position || '—'}{p.squad_number ? ` · #${p.squad_number}` : ''}{p.is_linked_to_player ? ' · Linked' : ' · Local'}
                          </span>
                        </div>
                      </div>
                      {canManage && (
                        <button type="button" className={styles.ghostBtn}
                          onClick={(e) => { e.stopPropagation(); setEditingPlayer(p); setForm(toFormState(p)); setShowAddForm(true); }}>
                          Edit
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className={styles.rightCol}>
          {!selectedPlayer ? (
            <div className={`${styles.panel} ${styles.emptyPanel}`}>
              <span className={styles.emptyText}>Select a player to view details.</span>
            </div>
          ) : (
            <>
              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <span className={styles.panelTitle}>{getLabel(selectedPlayer)}</span>
                    <div className={styles.availRow}>
                      <div className={styles.availDot} style={{ background: dot.colour }} />
                      <span className={styles.availLabel}>{dot.label}</span>
                      {currentInjury && (
                        <span className={styles.injuryBadge}>
                          {currentInjury.injury_type_display}{currentInjury.estimated_return ? ` · return ${currentInjury.estimated_return}` : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  {canManage && (
                    <button type="button" className={styles.secondaryBtn} onClick={() => setShowInjuryModal(true)}>
                      {currentInjury ? 'Update injury' : 'Log injury'}
                    </button>
                  )}
                </div>
                <div className={styles.metaGrid}>
                  {[
                    ['Position', selectedPlayer.primary_position || '—'],
                    ['Squad no.', selectedPlayer.squad_number ?? '—'],
                    ['DoB', selectedPlayer.date_of_birth ?? '—'],
                    ['Height', selectedPlayer.height_cm ? `${selectedPlayer.height_cm} cm` : '—'],
                    ['Foot', selectedPlayer.preferred_foot || '—'],
                    ['Status', selectedPlayer.is_active ? 'Active' : 'Inactive'],
                  ].map(([label, value]) => (
                    <div key={label} className={styles.metaItem}>
                      <span className={styles.metaLabel}>{label}</span>
                      <span className={styles.metaValue}>{value}</span>
                    </div>
                  ))}
                </div>
                {(selectedPlayer.secondary_positions?.length ?? 0) > 0 && (
                  <p className={styles.secondaryPos}>Also plays: {selectedPlayer.secondary_positions.join(', ')}</p>
                )}
              </div>

              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <span className={styles.panelTitle}>Season stats</span>
                  {canonicalId && (
                    <button type="button" className={styles.ghostBtn}
                      onClick={() => navigate(buildProfileUrl(canonicalId, clubId, selectedPlayer.id, summaryFilters))}>
                      Full profile →
                    </button>
                  )}
                </div>
                <CompactPlayerPreview
                  player={selectedPlayer} summary={summary} isLoading={summaryLoading}
                  error={summaryErr} canonicalPlayerId={canonicalId}
                  onOpenReadPage={canonicalId && !summaryLoading
                    ? () => navigate(buildProfileUrl(canonicalId, clubId, selectedPlayer.id, summaryFilters))
                    : null}
                />
              </div>

              {canManage && (
                <ManualStatsPanel
                  clubId={clubId} player={selectedPlayer} currentStats={manualStats}
                  canManage={canManage} onUpdate={setManualStats}
                />
              )}

              {injuries.length > 0 && (
                <div className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelTitle}>Injury log</span>
                    <span className={styles.badge}>{injuries.length}</span>
                  </div>
                  <div className={styles.injuryList}>
                    {injuries.map((inj) => (
                      <div key={inj.id} className={styles.injuryRow}>
                        <div>
                          <span className={styles.injuryType}>{inj.injury_type_display} · {inj.severity_display}</span>
                          <span className={styles.injuryMeta}>
                            {inj.injured_at}{inj.estimated_return ? ` → ${inj.estimated_return}` : ''}{inj.notes ? ` · ${inj.notes}` : ''}
                          </span>
                        </div>
                        {inj.is_current && canManage && (
                          <button type="button" className={styles.ghostBtn} onClick={() => handleResolveInjury(inj.id)}>
                            Resolve
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {showInjuryModal && selectedPlayer && (
        <InjuryModal
          clubId={clubId} player={selectedPlayer} currentInjury={currentInjury}
          onClose={() => setShowInjuryModal(false)}
          onSaved={async () => {
            setShowInjuryModal(false);
            const [fresh, freshPlayers] = await Promise.all([
              clubsApi.injuries.list(clubId, selectedPlayer.id),
              clubsApi.listPlayers(clubId),
            ]);
            setInjuries(fresh); setPlayers(freshPlayers);
          }}
        />
      )}
    </div>
  );
};

export default PlayersTab;
