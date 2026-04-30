import { useNavigate } from 'react-router-dom';
import styles from './css/PredictionsHub.module.css';

interface Section {
  icon: string;
  title: string;
  description: string;
  label: string;
  path?: string;
  getPath?: () => string;
}

const TACTICAL_TEAM_EXAMPLES = [
  'Arsenal',
  'Real Madrid',
  'Barcelona',
  'Liverpool',
  'Atlético Madrid',
] as const;

const TRUST_LEAGUE_EXAMPLES = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1'] as const;

interface FixtureExample {
  home: string;
  away: string;
  league: string;
  date: string;
}

const FIXTURE_EXAMPLES: FixtureExample[] = [
  { home: 'Arsenal', away: 'Chelsea', league: 'EPL', date: '2026-05-15' },
  { home: 'Liverpool', away: 'Manchester United', league: 'EPL', date: '2026-05-10' },
  { home: 'Manchester City', away: 'Liverpool', league: 'EPL', date: '2026-05-20' },
  { home: 'Real Madrid', away: 'Barcelona', league: 'La_Liga', date: '2026-05-18' },
  { home: 'Bayern Munich', away: 'Dortmund', league: 'Bundesliga', date: '2026-05-12' },
  { home: 'PSG', away: 'Marseille', league: 'Ligue_1', date: '2026-05-14' },
  { home: 'Juventus', away: 'AC Milan', league: 'Serie_A', date: '2026-05-16' },
] as const;

function randomFrom<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

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
    getPath: () => {
      const fixture = randomFrom(FIXTURE_EXAMPLES);
      return `/match/lookup?home=${encodeURIComponent(fixture.home)}&away=${encodeURIComponent(fixture.away)}&league=${encodeURIComponent(fixture.league)}&date=${encodeURIComponent(fixture.date)}&example=1`;
    },
  },
  {
    icon: '📈',
    title: 'Season Projection',
    description: 'Explore projected league standings, title races, and relegation battles for the current season.',
    label: 'View Projections',
    path: '/season/PL',
  },
  {
    icon: '🎯',
    title: 'Tactical Scouting',
    description: "Analyse a team's formation tendencies, pressing intensity, and in/out-of-possession shape.",
    label: 'Scout a Team',
    getPath: () => {
      const team = encodeURIComponent(randomFrom(TACTICAL_TEAM_EXAMPLES));
      return `/tactics/${team}?example=1`;
    },
  },
  {
    icon: '👥',
    title: 'Squad Intelligence',
    description: 'Deep-dive into squad composition, injury risk, and player availability for any team.',
    label: 'View Squad',
    getPath: () => {
      const team = encodeURIComponent(randomFrom(TACTICAL_TEAM_EXAMPLES));
      return `/squad/${team}?example=1`;
    },
  },
  {
    icon: '🏅',
    title: 'Model Trust Centre',
    description: 'Review model accuracy, calibration bands, and biggest hits and misses over the season.',
    label: 'Open Trust Centre',
    getPath: () => {
      const league = encodeURIComponent(randomFrom(TRUST_LEAGUE_EXAMPLES));
      return `/trust?league=${league}&example=1`;
    },
  },
];

// NOTE: Tactical Scouting (/tactics/:teamSlug) and Squad Intelligence (/squad/:teamSlug)
// require a team slug — access them via Match Intelligence where team context is established.

export default function PredictionsHub() {
  const navigate = useNavigate();
  const resolveSectionPath = (section: Section): string =>
    section.getPath ? section.getPath() : (section.path ?? '/predictions/hub');

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