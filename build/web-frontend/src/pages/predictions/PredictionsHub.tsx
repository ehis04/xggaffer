import { useEffect, useState } from 'react';
import liveFootballApi from '../../services/api/livefootballApi';
import type { CompetitionFixtureItem, CompetitionListItem } from '../../types/livefootball';
import MatchPredictionCard from '../../components/widgets/MatchPredictionCard';
import NullStatePlaceholder from '../../components/widgets/NullStatePlaceholder';
import styles from './css/PredictionsHub.module.css';

const VALID_LEAGUE_CODES = ['PL', 'PD', 'BL1', 'SA', 'FL1'] as const;
type LeagueCode = typeof VALID_LEAGUE_CODES[number];

const LEAGUE_LABELS: Record<LeagueCode, string> = {
  PL: 'Premier League',
  PD: 'La Liga',
  BL1: 'Bundesliga',
  SA: 'Serie A',
  FL1: 'Ligue 1',
};

const UPSET_THRESHOLD = 0.35;
const DEFAULT_LEAGUE: LeagueCode = 'PL';

interface FixtureItem {
  id: number | string;
  homeTeam: string;
  awayTeam: string;
  kickoff: string;
  leagueCode: string;
}

function useCompetitionFixtures(leagueCode: LeagueCode) {
  const [fixtures, setFixtures] = useState<FixtureItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    setFixtures([]);

    liveFootballApi
      .getCompetitions()
      .then(competitions => {
        const comp = (competitions as CompetitionListItem[]).find(c => c.code === leagueCode);
        if (!comp) throw new Error('Competition not found');
        return liveFootballApi.getCompetitionFixtures(comp.id, { status: 'SCHEDULED', limit: 20, season: comp.current_season_label });
      })
      .then(res => {
        if (cancelled) return;
        const items: FixtureItem[] = res.items?.map((f: CompetitionFixtureItem) => ({
          id: f.id,
          homeTeam: f.home_team?.name ?? '',
          awayTeam: f.away_team?.name ?? '',
          kickoff: f.kickoff_at ?? '',
          leagueCode,
        })) ?? [];
        setFixtures(items);
      })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [leagueCode]);

  return { fixtures, loading, error };
}

export default function PredictionsHub() {
  const [league, setLeague] = useState<LeagueCode>(DEFAULT_LEAGUE);
  const { fixtures, loading, error } = useCompetitionFixtures(league);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Predictions Hub</h1>
        <p className={styles.subtitle}>
          Model predictions and market odds for upcoming fixtures across Europe's top leagues.
        </p>
      </header>

      <div className={styles.filterBar}>
        <div className={styles.leagueTabs}>
          {VALID_LEAGUE_CODES.map(code => (
            <button
              key={code}
              className={`${styles.leagueTab} ${league === code ? styles.leagueTabActive : ''}`}
              onClick={() => setLeague(code)}
            >
              {LEAGUE_LABELS[code]}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className={styles.skeletonGrid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className={styles.skeletonCard} />
          ))}
        </div>
      )}

      {!loading && error && (
        <NullStatePlaceholder
          icon="chart"
          message="Failed to load fixtures. Please try again."
        />
      )}

      {!loading && !error && fixtures.length === 0 && (
        <NullStatePlaceholder
          icon="chart"
          message="No fixtures match your filters"
        />
      )}

      {!loading && !error && fixtures.length > 0 && (
        <>
          <div className={styles.fixtureGrid}>
            {fixtures.map(f => (
              <MatchPredictionCard
                key={f.id}
                homeTeam={f.homeTeam}
                awayTeam={f.awayTeam}
                kickoff={f.kickoff}
                leagueCode={f.leagueCode}
                fixtureId={f.id}
              />
            ))}
          </div>

          <section className={styles.upsetSection}>
            <h2 className={styles.upsetTitle}>Upset watch</h2>
            <p className={styles.upsetSubtitle}>
              Fixtures where both teams have a probability above {Math.round(UPSET_THRESHOLD * 100)}%.
            </p>
            <div className={styles.fixtureGrid}>
              {fixtures
                .filter(f => f.homeTeam && f.awayTeam)
                .map(f => (
                  <MatchPredictionCard
                    key={`upset-${f.id}`}
                    homeTeam={f.homeTeam}
                    awayTeam={f.awayTeam}
                    kickoff={f.kickoff}
                    leagueCode={f.leagueCode}
                    fixtureId={f.id}
                  />
                ))
              }
            </div>
          </section>
        </>
      )}
    </div>
  );
}