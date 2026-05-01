import { useEffect, useState } from 'react';
import { getOddsTeams } from '../../services/api/predictionsApi';
import { PREDICTION_LEAGUE_OPTIONS } from '../../utils/footballSeason';
import styles from './TeamSwitcher.module.css';

interface Props {
  currentTeam: string;
  onSelect: (team: string) => void;
}

export function TeamSwitcher({ currentTeam, onSelect }: Props) {
  const [league, setLeague] = useState(PREDICTION_LEAGUE_OPTIONS[0].value);
  const [teams, setTeams] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setTeams([]);
    getOddsTeams(league)
      .then(env => { if (!cancelled) setTeams(env.data?.teams ?? []); })
      .catch(() => { if (!cancelled) setTeams([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [league]);

  return (
    <div className={styles.switcher}>
      <span className={styles.label}>Switch team</span>
      <select
        className={styles.select}
        value={league}
        onChange={e => setLeague(e.target.value)}
      >
        {PREDICTION_LEAGUE_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      <select
        className={styles.select}
        value=""
        disabled={loading || teams.length === 0}
        onChange={e => { if (e.target.value) onSelect(e.target.value); }}
      >
        <option value="">{loading ? 'Loading…' : 'Select team'}</option>
        {teams.filter(t => t !== currentTeam).map(t => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
    </div>
  );
}
