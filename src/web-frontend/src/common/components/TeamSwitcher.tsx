import { useEffect, useState } from 'react';
import { getTacticalTeams, getTeams } from '../../services/api/predictionsApi';
import { PREDICTION_LEAGUE_OPTIONS } from '../../utils/footballSeason';
import styles from './TeamSwitcher.module.css';

interface Props {
  currentTeam: string;
  onSelect: (team: string) => void;
  tactical?: boolean;
}

export function TeamSwitcher({ currentTeam, onSelect, tactical = false }: Props) {
  const [league, setLeague] = useState(PREDICTION_LEAGUE_OPTIONS[0].value);
  const [teams, setTeams] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setTeams([]);
    setError(false);
    const request = tactical ? getTacticalTeams() : getTeams(league, '2025').then(env => env.data?.teams ?? []);
    request
      .then(options => { if (!cancelled) setTeams(options); })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [league, tactical]);

  return (
    <div className={styles.switcher}>
      <span className={styles.label}>{currentTeam ? 'Switch team' : 'Choose a team'}</span>
      {!tactical && <select
        aria-label="League"
        className={styles.select}
        value={league}
        onChange={e => setLeague(e.target.value)}
      >
        {PREDICTION_LEAGUE_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>}
      <select
        aria-label="Team"
        className={styles.select}
        value=""
        disabled={loading || teams.length === 0}
        onChange={e => { if (e.target.value) onSelect(e.target.value); }}
      >
        <option value="">{loading ? 'Loading…' : error ? 'Teams unavailable' : teams.length ? 'Select team' : 'No teams available'}</option>
        {teams.filter(t => t !== currentTeam).map(t => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
    </div>
  );
}
