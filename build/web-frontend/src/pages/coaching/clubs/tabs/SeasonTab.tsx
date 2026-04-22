import { useEffect, useState } from 'react';
import { clubsApi } from '../../../../services/api';
import { liveFootballApi } from '../../../../services/api/livefootballApi';
import type { ClubContext } from '../IndividualClubBase';
import type {
  ClubSeasonResult,
  CreateClubSeasonResultPayload,
  SeasonResultVenue,
  ClubUnderstatSeasonSummaryResponse,
} from '../../../../types/club';
import type {
  CompetitionTableResponse,
  CompetitionFixtureItem,
  CompetitionListItem,
} from '../../../../types/livefootball';
import styles from './css/SeasonTab.module.css';

interface Props {
  ctx: ClubContext;
}

type MatchOutcome = 'W' | 'D' | 'L';

interface ResultFormState {
  opponent_name: string;
  venue: SeasonResultVenue;
  competition: string;
  match_date: string;
  goals_for: string;
  goals_against: string;
  notes: string;
}

const VENUE_OPTIONS: { value: SeasonResultVenue; label: string }[] = [
  { value: 'home', label: 'Home' },
  { value: 'away', label: 'Away' },
  { value: 'neutral', label: 'Neutral' },
];

const emptyForm = (): ResultFormState => ({
  opponent_name: '', venue: 'home', competition: '',
  match_date: '', goals_for: '', goals_against: '', notes: '',
});

const fmtDate = (v: string | null): string => {
  if (!v) return '—';
  return new Date(v).toLocaleDateString('en-IE', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
};

const fmtKickoff = (v: string | null | undefined): string => {
  if (!v) return 'TBC';
  return new Date(v).toLocaleString('en-IE', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
};

const getOutcomeStyle = (outcome: MatchOutcome) => {
  if (outcome === 'W') return { color: '#4ade80', background: 'rgba(74,222,128,0.12)' };
  if (outcome === 'D') return { color: '#fbbf24', background: 'rgba(251,191,36,0.12)' };
  return { color: '#f87171', background: 'rgba(248,113,113,0.12)' };
};

const getTeamLabel = (team: { name: string; short_name?: string; tla?: string }): string =>
  team.short_name?.trim() || team.tla?.trim() || team.name;

// ── Pro club path ────────────────────────────────────────────────────────────

interface ProSeasonData {
  understat: ClubUnderstatSeasonSummaryResponse | null;
  table: CompetitionTableResponse | null;
  previous: CompetitionFixtureItem[];
  upcoming: CompetitionFixtureItem[];
  competition: CompetitionListItem | null;
}

const ProSeasonView = ({ clubId, clubName }: { clubId: number; clubName: string }) => {
  const [data, setData] = useState<ProSeasonData>({
    understat: null, table: null,
    previous: [], upcoming: [], competition: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);

        const understatRaw = await clubsApi.getUnderstatSeasonSummary(clubId);
        const understat = 'wins' in understatRaw
          ? understatRaw as ClubUnderstatSeasonSummaryResponse
          : null;

        const competitionCode = understat?.competition_code ?? null;
        let table: CompetitionTableResponse | null = null;
        let previous: CompetitionFixtureItem[] = [];
        let upcoming: CompetitionFixtureItem[] = [];
        let competition: CompetitionListItem | null = null;

        if (competitionCode) {
          const competitions = await liveFootballApi.getCompetitions();
          competition = competitions.find(
            (c) => c.code?.toUpperCase() === competitionCode.toUpperCase()
          ) ?? null;

          if (competition) {
            const [tableData, splitData] = await Promise.allSettled([
              liveFootballApi.getCompetitionTable(competition.id, {
                season: understat?.season_label ?? undefined,
              }),
              liveFootballApi.getCompetitionPreviousNextFixtures(competition.id, {
                season: understat?.season_label ?? undefined,
                previous_limit: 5,
                next_limit: 5,
              }),
            ]);

            if (tableData.status === 'fulfilled') table = tableData.value;
            if (splitData.status === 'fulfilled') {
              previous = splitData.value.previous;
              upcoming = splitData.value.next;
            }
          }
        }

        setData({ understat, table, previous, upcoming, competition });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load season data.');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [clubId]);

  if (loading) return <div className={styles.loading}>Loading season data...</div>;
  if (error) return <div className={styles.errorNotice}>{error}</div>;

  const { understat, table, previous, upcoming, competition } = data;

  const highlightClub = (teamName: string): boolean =>
    teamName.toLowerCase().includes(clubName.toLowerCase().split(' ')[0].toLowerCase());

  return (
    <div className={styles.proLayout}>
      {understat && (
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>Season record</span>
            <span className={styles.badge}>
              {understat.season_label}
              {understat.competition_name ? ` · ${understat.competition_name}` : ''}
            </span>
          </div>
          <div className={styles.recordGrid}>
            <div className={styles.recordStat}>
              <span className={styles.recordValue} style={{ color: '#4ade80' }}>{understat.wins}</span>
              <span className={styles.recordLabel}>Wins</span>
            </div>
            <div className={styles.recordStat}>
              <span className={styles.recordValue} style={{ color: '#fbbf24' }}>{understat.draws}</span>
              <span className={styles.recordLabel}>Draws</span>
            </div>
            <div className={styles.recordStat}>
              <span className={styles.recordValue} style={{ color: '#f87171' }}>{understat.losses}</span>
              <span className={styles.recordLabel}>Losses</span>
            </div>
            <div className={styles.recordStat}>
              <span className={styles.recordValue}>{understat.goals_for}</span>
              <span className={styles.recordLabel}>Goals for</span>
            </div>
            <div className={styles.recordStat}>
              <span className={styles.recordValue}>{understat.goals_against}</span>
              <span className={styles.recordLabel}>Goals against</span>
            </div>
            <div className={styles.recordStat}>
              <span className={styles.recordValue}>{understat.matches_played}</span>
              <span className={styles.recordLabel}>Played</span>
            </div>
            {understat.xg && (
              <div className={styles.recordStat}>
                <span className={styles.recordValue}>{Number(understat.xg).toFixed(1)}</span>
                <span className={styles.recordLabel}>xG</span>
              </div>
            )}
            {understat.xga && (
              <div className={styles.recordStat}>
                <span className={styles.recordValue}>{Number(understat.xga).toFixed(1)}</span>
                <span className={styles.recordLabel}>xGA</span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className={styles.twoCol}>
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>
              {competition?.name ?? 'League table'}
            </span>
            {table?.season_label && (
              <span className={styles.badge}>{table.season_label}</span>
            )}
          </div>
          {!table ? (
            <p className={styles.emptyText}>Table not available.</p>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.leagueTable}>
                <thead>
                  <tr>
                    <th>Pos</th>
                    <th>Team</th>
                    <th>P</th>
                    <th>W</th>
                    <th>D</th>
                    <th>L</th>
                    <th>GD</th>
                    <th>Pts</th>
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((row) => {
                    const isHighlighted = highlightClub(row.team.name);
                    return (
                      <tr
                        key={`${row.position}-${row.team.external_id ?? row.team.name}`}
                        className={isHighlighted ? styles.highlightedRow : ''}
                      >
                        <td>{row.position}</td>
                        <td className={styles.teamCell}>
                          <span className={isHighlighted ? styles.highlightedTeam : ''}>
                            {getTeamLabel(row.team)}
                          </span>
                        </td>
                        <td>{row.played}</td>
                        <td>{row.won}</td>
                        <td>{row.drawn}</td>
                        <td>{row.lost}</td>
                        <td>{row.goal_difference > 0 ? `+${row.goal_difference}` : row.goal_difference}</td>
                        <td className={styles.ptsCell}>{row.points}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className={styles.fixtureColumns}>
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>Recent results</span>
              <span className={styles.badge}>{previous.length}</span>
            </div>
            {previous.length === 0 ? (
              <p className={styles.emptyText}>No recent results.</p>
            ) : (
              <div className={styles.fixtureList}>
                {[...previous].reverse().map((fx) => (
                  <div key={fx.id} className={styles.fixtureRow}>
                    <span className={styles.fixtureDate}>{fmtKickoff(fx.kickoff_at)}</span>
                    <span className={styles.fixtureTeams}>
                      {getTeamLabel(fx.home_team)} v {getTeamLabel(fx.away_team)}
                    </span>
                    {fx.home_score !== null && fx.away_score !== null && (
                      <span className={styles.fixtureScore}>
                        {fx.home_score}–{fx.away_score}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>Upcoming fixtures</span>
              <span className={styles.badge}>{upcoming.length}</span>
            </div>
            {upcoming.length === 0 ? (
              <p className={styles.emptyText}>No upcoming fixtures.</p>
            ) : (
              <div className={styles.fixtureList}>
                {upcoming.map((fx) => (
                  <div key={fx.id} className={styles.fixtureRow}>
                    <span className={styles.fixtureDate}>{fmtKickoff(fx.kickoff_at)}</span>
                    <span className={styles.fixtureTeams}>
                      {getTeamLabel(fx.home_team)} v {getTeamLabel(fx.away_team)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Non-pro / manual path ────────────────────────────────────────────────────

const ManualSeasonView = ({ clubId, canManage }: { clubId: number; canManage: boolean }) => {
  const [results, setResults] = useState<ClubSeasonResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ResultFormState>(emptyForm());
  const [showForm, setShowForm] = useState(false);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const loadResults = async () => {
    const data = await clubsApi.seasonResults.list(clubId);
    setResults(data);
  };

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        await loadResults();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load results.');
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, [clubId]);

  const record = clubsApi.seasonResults.deriveRecord(results);

  const handleInput = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async () => {
    if (!form.opponent_name.trim()) { setFormError('Opponent is required.'); return; }
    if (!form.match_date) { setFormError('Match date is required.'); return; }
    if (form.goals_for === '' || form.goals_against === '') {
      setFormError('Goals for and against are required.'); return;
    }
    try {
      setSaving(true); setFormError(null);
      const payload: CreateClubSeasonResultPayload = {
        opponent_name: form.opponent_name.trim(),
        venue: form.venue,
        competition: form.competition.trim(),
        match_date: form.match_date,
        goals_for: Number(form.goals_for),
        goals_against: Number(form.goals_against),
        notes: form.notes.trim(),
      };
      if (editingId !== null) {
        await clubsApi.seasonResults.update(clubId, editingId, payload);
      } else {
        await clubsApi.seasonResults.create(clubId, payload);
      }
      await loadResults();
      setForm(emptyForm()); setEditingId(null); setShowForm(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to save result.');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (r: ClubSeasonResult) => {
    setEditingId(r.id);
    setForm({
      opponent_name: r.opponent_name,
      venue: r.venue,
      competition: r.competition,
      match_date: r.match_date,
      goals_for: String(r.goals_for),
      goals_against: String(r.goals_against),
      notes: r.notes,
    });
    setShowForm(true);
    setFormError(null);
  };

  const handleDelete = async (r: ClubSeasonResult) => {
    if (!window.confirm(`Delete result vs ${r.opponent_name}?`)) return;
    try {
      setLoadingKey(`delete-${r.id}`);
      await clubsApi.seasonResults.delete(clubId, r.id);
      await loadResults();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete.');
    } finally {
      setLoadingKey(null);
    }
  };

  if (loading) return <div className={styles.loading}>Loading results...</div>;
  if (error) return <div className={styles.errorNotice}>{error}</div>;

  return (
    <div className={styles.manualLayout}>
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Season record</span>
          <span className={styles.badge}>{record.played} played</span>
        </div>
        <div className={styles.recordGrid}>
          <div className={styles.recordStat}>
            <span className={styles.recordValue} style={{ color: '#4ade80' }}>{record.wins}</span>
            <span className={styles.recordLabel}>Wins</span>
          </div>
          <div className={styles.recordStat}>
            <span className={styles.recordValue} style={{ color: '#fbbf24' }}>{record.draws}</span>
            <span className={styles.recordLabel}>Draws</span>
          </div>
          <div className={styles.recordStat}>
            <span className={styles.recordValue} style={{ color: '#f87171' }}>{record.losses}</span>
            <span className={styles.recordLabel}>Losses</span>
          </div>
          <div className={styles.recordStat}>
            <span className={styles.recordValue}>{record.goals_for}</span>
            <span className={styles.recordLabel}>Goals for</span>
          </div>
          <div className={styles.recordStat}>
            <span className={styles.recordValue}>{record.goals_against}</span>
            <span className={styles.recordLabel}>Goals against</span>
          </div>
          <div className={styles.recordStat}>
            <span className={styles.recordValue}>
              {record.goals_for - record.goals_against > 0
                ? `+${record.goals_for - record.goals_against}`
                : record.goals_for - record.goals_against}
            </span>
            <span className={styles.recordLabel}>Goal diff</span>
          </div>
        </div>
      </div>

      <div className={styles.twoCol}>
        {canManage && (
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>
                {editingId !== null ? 'Edit result' : 'Add result'}
              </span>
              {!showForm ? (
                <button type="button" className={styles.primaryBtn}
                  onClick={() => { setShowForm(true); setEditingId(null); setForm(emptyForm()); }}>
                  + Add result
                </button>
              ) : (
                <button type="button" className={styles.ghostBtn}
                  onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm()); }}>
                  Cancel
                </button>
              )}
            </div>

            {showForm && (
              <>
                {formError && <div className={styles.errorNotice}>{formError}</div>}
                <div className={styles.formGrid}>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="sr_opponent">Opponent</label>
                    <input id="sr_opponent" name="opponent_name" className={styles.input}
                      value={form.opponent_name} onChange={handleInput} placeholder="e.g. Dublin City FC" />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="sr_venue">Venue</label>
                    <select id="sr_venue" name="venue" className={styles.select}
                      value={form.venue} onChange={handleInput}>
                      {VENUE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="sr_comp">Competition</label>
                    <input id="sr_comp" name="competition" className={styles.input}
                      value={form.competition} onChange={handleInput} placeholder="e.g. League" />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="sr_date">Match date</label>
                    <input id="sr_date" name="match_date" type="date" className={styles.input}
                      value={form.match_date} onChange={handleInput} />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="sr_gf">Goals for</label>
                    <input id="sr_gf" name="goals_for" type="number" min="0" className={styles.input}
                      value={form.goals_for} onChange={handleInput} placeholder="0" />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.label} htmlFor="sr_ga">Goals against</label>
                    <input id="sr_ga" name="goals_against" type="number" min="0" className={styles.input}
                      value={form.goals_against} onChange={handleInput} placeholder="0" />
                  </div>
                  <div className={styles.formGroup} style={{ gridColumn: '1 / -1' }}>
                    <label className={styles.label} htmlFor="sr_notes">Notes</label>
                    <input id="sr_notes" name="notes" className={styles.input}
                      value={form.notes} onChange={handleInput} placeholder="Optional" />
                  </div>
                </div>
                <div className={styles.formActions}>
                  <button type="button" className={styles.primaryBtn}
                    disabled={saving} onClick={handleSubmit}>
                    {saving
                      ? (editingId !== null ? 'Saving...' : 'Creating...')
                      : (editingId !== null ? 'Save result' : 'Add result')}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>Results log</span>
            <span className={styles.badge}>{results.length}</span>
          </div>
          {results.length === 0 ? (
            <p className={styles.emptyText}>No results recorded yet.</p>
          ) : (
            <div className={styles.resultList}>
              {results.map((r) => {
                const outStyle = getOutcomeStyle(r.outcome);
                return (
                  <div key={r.id} className={styles.resultRow}>
                    <span className={styles.outcomeBadge} style={outStyle}>
                      {r.outcome}
                    </span>
                    <div className={styles.resultInfo}>
                      <span className={styles.resultOpponent}>
                        vs {r.opponent_name}
                        <span className={styles.resultScore}>
                          {' '}{r.goals_for}–{r.goals_against}
                        </span>
                      </span>
                      <span className={styles.resultMeta}>
                        {fmtDate(r.match_date)}
                        {r.competition ? ` · ${r.competition}` : ''}
                        {' · '}{r.venue_display}
                      </span>
                    </div>
                    {canManage && (
                      <div className={styles.resultActions}>
                        <button type="button" className={styles.ghostBtn}
                          onClick={() => handleEdit(r)}>Edit</button>
                        <button type="button" className={styles.dangerBtn}
                          disabled={loadingKey === `delete-${r.id}`}
                          onClick={() => handleDelete(r)}>
                          {loadingKey === `delete-${r.id}` ? '...' : 'Del'}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Main tab ─────────────────────────────────────────────────────────────────

const SeasonTab = ({ ctx }: Props) => {
  const { club, clubId, canManage } = ctx;
  const isProClub = club.club_type === 'system_professional';

  return (
    <div className={styles.tabContent}>
      {isProClub ? (
        <ProSeasonView clubId={clubId} clubName={club.name} />
      ) : (
        <ManualSeasonView clubId={clubId} canManage={canManage} />
      )}
    </div>
  );
};

export default SeasonTab;