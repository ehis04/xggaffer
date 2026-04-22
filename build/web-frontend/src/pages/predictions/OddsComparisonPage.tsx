import { useState, useEffect, useCallback } from 'react';
import { getOddsFixtures, getOddsTeams, predictMatch } from '../../services/api/predictionsApi';
import type { OddsFixtureItem, PredictionResponse } from '../../types/prediction';
import styles from './css/OddsComparisonPage.module.css';

const LEAGUE_OPTIONS = [
  { value: 'EPL', label: 'Premier League' },
  { value: 'La_Liga', label: 'La Liga' },
  { value: 'Bundesliga', label: 'Bundesliga' },
  { value: 'Serie_A', label: 'Serie A' },
  { value: 'Ligue_1', label: 'Ligue 1' },
];

const OUTCOME_LABEL: Record<string, string> = { H: 'Home win', D: 'Draw', A: 'Away win' };

function fmt(n: number) {
  return (n * 100).toFixed(1) + '%';
}

function OddsCell({ home, draw, away }: { home: number; draw: number; away: number }) {
  return (
    <span className={styles.oddsCell}>
      <span className={styles.oddsPill}>{home.toFixed(2)}</span>
      <span className={styles.oddsPill}>{draw.toFixed(2)}</span>
      <span className={styles.oddsPill}>{away.toFixed(2)}</span>
    </span>
  );
}

function PredictionCell({ fixture, league }: { fixture: OddsFixtureItem; league: string }) {
  const [pred, setPred] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(false);
    try {
      const res = await predictMatch({
        home_team: fixture.home_team,
        away_team: fixture.away_team,
        league,
        season: '2025',
      });
      setPred(res);
    } catch {
      setErr(true);
    } finally {
      setLoading(false);
    }
  }, [fixture.home_team, fixture.away_team, league]);

  if (pred) {
    return (
      <span className={styles.predResult}>
        <strong>{pred.prediction}</strong>
        <span className={styles.predProbs}>
          {fmt(pred.probabilities.home)} / {fmt(pred.probabilities.draw)} / {fmt(pred.probabilities.away)}
        </span>
      </span>
    );
  }
  if (loading) return <span className={styles.predLoading}>…</span>;
  if (err) return <span className={styles.predError}>Failed</span>;
  return <button className={styles.predButton} onClick={load}>Get prediction</button>;
}

export default function OddsComparisonPage() {
  const [league, setLeague] = useState('EPL');
  const [view, setView] = useState<'past' | 'future'>('future');
  const [teamA, setTeamA] = useState('');
  const [teamB, setTeamB] = useState('');

  const [teams, setTeams] = useState<string[]>([]);
  const [fixtures, setFixtures] = useState<OddsFixtureItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reload team list when league changes, reset selections
  useEffect(() => {
    setTeamA('');
    setTeamB('');
    getOddsTeams(league)
      .then((res) => setTeams(res.teams))
      .catch(() => setTeams([]));
  }, [league]);

  // Reload fixtures on any filter change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setFixtures([]);

    getOddsFixtures(league, view, teamA || undefined, teamB || undefined)
      .then((res) => { if (!cancelled) setFixtures(res.fixtures); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load fixtures.'); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [league, view, teamA, teamB]);

  const showResultColumn = view === 'past';

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Odds &amp; Market Comparison — 2025/26</h1>
        <p className={styles.subtitle}>
          Browse bookmaker odds and model predictions for{' '}
          {view === 'past' ? 'completed' : 'upcoming'} fixtures.
        </p>
      </header>

      <div className={styles.controls}>
        <label className={styles.controlField}>
          <span className={styles.controlLabel}>League</span>
          <select className={styles.select} value={league} onChange={(e) => setLeague(e.target.value)}>
            {LEAGUE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <label className={styles.controlField}>
          <span className={styles.controlLabel}>View</span>
          <select
            className={styles.select}
            value={view}
            onChange={(e) => setView(e.target.value as 'past' | 'future')}
          >
            <option value="future">Upcoming fixtures</option>
            <option value="past">Past fixtures</option>
          </select>
        </label>

        <label className={styles.controlField}>
          <span className={styles.controlLabel}>Team A</span>
          <select className={styles.select} value={teamA} onChange={(e) => setTeamA(e.target.value)}>
            <option value="">Any</option>
            {teams.filter((t) => t !== teamB).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>

        <label className={styles.controlField}>
          <span className={styles.controlLabel}>Team B</span>
          <select className={styles.select} value={teamB} onChange={(e) => setTeamB(e.target.value)}>
            <option value="">Any</option>
            {teams.filter((t) => t !== teamA).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
      </div>

      {loading && (
        <div className={styles.stateCard}>
          <p className={styles.stateText}>Loading fixtures…</p>
        </div>
      )}

      {!loading && error && (
        <div className={`${styles.stateCard} ${styles.errorState}`}>
          <p className={styles.stateText}>{error}</p>
        </div>
      )}

      {!loading && !error && fixtures.length === 0 && (
        <div className={styles.stateCard}>
          <p className={styles.stateText}>No fixtures with odds data found for this selection.</p>
        </div>
      )}

      {!loading && !error && fixtures.length > 0 && (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Fixture</th>
                <th className={styles.th}>Date</th>
                <th className={`${styles.th} ${styles.oddsHeader}`}>Consensus odds (H / D / A)</th>
                {showResultColumn && <th className={styles.th}>Result</th>}
                <th className={styles.th}>Model prediction</th>
              </tr>
            </thead>
            <tbody>
              {fixtures.map((f, i) => {
                const dateStr = new Date(f.commence_time).toLocaleDateString(undefined, {
                  day: 'numeric', month: 'short', year: 'numeric',
                });
                const outcome = f.result?.outcome;

                return (
                  <tr key={i} className={styles.row}>
                    <td className={styles.td}>
                      <span className={styles.fixture}>
                        <span className={styles.team}>{f.home_team}</span>
                        <span className={styles.vs}>vs</span>
                        <span className={styles.team}>{f.away_team}</span>
                      </span>
                    </td>

                    <td className={`${styles.td} ${styles.dateCell}`}>{dateStr}</td>

                    <td className={styles.td}>
                      {f.consensus ? (
                        <OddsCell
                          home={f.consensus.devig_home}
                          draw={f.consensus.devig_draw}
                          away={f.consensus.devig_away}
                        />
                      ) : (
                        <span className={styles.noResult}>No odds data</span>
                      )}
                    </td>

                    {showResultColumn && (
                      <td className={styles.td}>
                        {f.result ? (
                          <span className={styles.result}>
                            <span className={styles.score}>{f.result.score}</span>
                            <span className={styles.outcomeLabel}>
                              {outcome ? OUTCOME_LABEL[outcome] : ''}
                            </span>
                          </span>
                        ) : (
                          <span className={styles.noResult}>—</span>
                        )}
                      </td>
                    )}

                    <td className={styles.td}>
                      <PredictionCell fixture={f} league={league} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
