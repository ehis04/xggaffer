import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getOddsFixtures } from '../../services/api/predictionsApi';
import type { OddsFixtureItem } from '../../types/prediction';
import {
  getCurrentFootballSeason,
  predictionLeagueToLiveCompetitionCode,
  PREDICTION_LEAGUE_OPTIONS,
} from '../../utils/footballSeason';
import styles from './css/PredictionsHub.module.css';

interface HubContext {
  fixture: FixtureExample | null;
  teamExamples: string[];
  trustLeague: string;
}

interface Section {
  icon: string;
  title: string;
  description: string;
  label: string;
  path?: string;
  getPath?: (context: HubContext) => string;
}

const FALLBACK_TEAM_EXAMPLES = [
  'Arsenal',
  'Real Madrid',
  'Barcelona',
  'Liverpool',
  'Atlético Madrid',
] as const;

interface FixtureExample {
  home: string;
  away: string;
  league: string;
  date: string;
  season: string;
}

function randomFrom<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

const fixtureToExample = (fixture: OddsFixtureItem): FixtureExample => ({
  home: fixture.home_team,
  away: fixture.away_team,
  league: fixture.league,
  date: new Date(fixture.commence_time).toISOString().slice(0, 10),
  season: fixture.season || getCurrentFootballSeason(),
});

const SECTIONS: Section[] = [
  {
    icon: '🔮',
    title: 'Match Predictions',
    description: 'Run match outcome predictions powered by Elo ratings and historical data across top leagues.',
    label: 'Open Predictions',
    path: '/predictions',
  },
  {
    icon: '📊',
    title: 'Odds Comparison',
    description: 'Compare model probabilities with bookmaker odds to spot value and market discrepancies.',
    label: 'Compare Odds',
    path: '/predictions/odds',
  },
  {
    icon: '🔍',
    title: 'Match Intelligence',
    description: 'Look up pre-match intelligence for any fixture — form, availability, head-to-head, and xG context.',
    label: 'Look Up Match',
    getPath: ({ fixture }) => {
      if (!fixture) return '/match/lookup';
      return `/match/lookup?home=${encodeURIComponent(fixture.home)}&away=${encodeURIComponent(fixture.away)}&league=${encodeURIComponent(fixture.league)}&season=${encodeURIComponent(fixture.season)}&date=${encodeURIComponent(fixture.date)}&source=odds`;
    },
  },
  {
    icon: '📈',
    title: 'Season Projection',
    description: 'Explore projected league standings, title races, and relegation battles for the current season.',
    label: 'View Projections',
    getPath: ({ fixture }) => `/season/${predictionLeagueToLiveCompetitionCode(fixture?.league ?? 'EPL')}`,
  },
  {
    icon: '🎯',
    title: 'Tactical Scouting',
    description: "Analyse a team's formation tendencies, pressing intensity, and in/out-of-possession shape.",
    label: 'Scout a Team',
    getPath: ({ teamExamples }) => {
      const teams = teamExamples.length > 0 ? teamExamples : FALLBACK_TEAM_EXAMPLES;
      return `/tactics/${encodeURIComponent(randomFrom(teams))}?source=fixture`;
    },
  },
  {
    icon: '👥',
    title: 'Squad Intelligence',
    description: 'Deep-dive into squad composition, injury risk, and player availability for any team.',
    label: 'View Squad',
    getPath: ({ teamExamples }) => {
      const teams = teamExamples.length > 0 ? teamExamples : FALLBACK_TEAM_EXAMPLES;
      return `/squad/${encodeURIComponent(randomFrom(teams))}?source=fixture`;
    },
  },
  {
    icon: '🏅',
    title: 'Model Trust Centre',
    description: 'Review model accuracy, calibration bands, and biggest hits and misses over the season.',
    label: 'Open Trust Centre',
    getPath: ({ trustLeague }) => `/trust?league=${encodeURIComponent(trustLeague)}&source=odds`,
  },
];

// NOTE: Tactical Scouting (/tactics/:teamSlug) and Squad Intelligence (/squad/:teamSlug)
// require a team slug — access them via Match Intelligence where team context is established.

export default function PredictionsHub() {
  const navigate = useNavigate();
  const [fixtures, setFixtures] = useState<FixtureExample[]>([]);

  useEffect(() => {
    let cancelled = false;

    const loadFixtures = async () => {
      const results = await Promise.allSettled(
        PREDICTION_LEAGUE_OPTIONS.map((option) => getOddsFixtures(option.value, 'future')),
      );

      if (cancelled) return;

      const nextFixtures = results
        .flatMap((result) => {
          if (result.status !== 'fulfilled') return [];
          return result.value.data?.fixtures ?? [];
        })
        .filter((fixture) => fixture.commence_time)
        .sort((a, b) => new Date(a.commence_time).getTime() - new Date(b.commence_time).getTime())
        .slice(0, 12)
        .map(fixtureToExample);

      if (nextFixtures.length > 0) {
        setFixtures(nextFixtures);
      }
    };

    void loadFixtures();
    return () => {
      cancelled = true;
    };
  }, []);

  const context = useMemo<HubContext>(() => {
    const fixture = fixtures.length > 0 ? randomFrom(fixtures) : null;
    const teamExamples = fixtures.flatMap((item) => [item.home, item.away]);
    return {
      fixture,
      teamExamples,
      trustLeague: fixture?.league ?? PREDICTION_LEAGUE_OPTIONS[0].value,
    };
  }, [fixtures]);

  const resolveSectionPath = (section: Section): string =>
    section.getPath ? section.getPath(context) : (section.path ?? '/predictions/hub');

  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <div>
          <h1 className={styles.title}>Prediction & Intelligence</h1>
          <p className={styles.subtitle}>
            Model-powered match predictions, tactical scouting, squad analysis, and trust metrics — all in one place.
          </p>
        </div>
      </section>

      <div className={styles.grid}>
        {SECTIONS.map((section) => (
          <div key={`${section.title}-${section.path}`} className={styles.card}>
            <div className={styles.cardIcon}>{section.icon}</div>
            <h2 className={styles.cardTitle}>{section.title}</h2>
            <p className={styles.cardDescription}>{section.description}</p>
            <button
              className={styles.cardButton}
              type="button"
              onClick={() => navigate(resolveSectionPath(section))}
            >
              {section.label}
              <span className={styles.cardButtonArrow}>→</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
