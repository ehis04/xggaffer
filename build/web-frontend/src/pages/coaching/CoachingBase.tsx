import { useNavigate } from 'react-router-dom';
import styles from './css/CoachingBase.module.css';

interface Section {
  icon: string;
  title: string;
  description: string;
  label: string;
  path: string;
}

const SECTIONS: Section[] = [
  {
    icon: '🏟',
    title: 'My Clubs',
    description: 'Manage your clubs, track memberships, invitations, and join requests.',
    label: 'Go to Clubs',
    path: '/clubs',
  },
  {
    icon: '🔍',
    title: 'Discover Clubs',
    description: 'Browse listed professional and user clubs. Copy a pro club to use as your own template.',
    label: 'Browse Clubs',
    path: '/clubs/browse',
  },
  {
    icon: '👤',
    title: 'Player Data',
    description: 'Search and view individual player profiles with Understat and Sofascore stats.',
    label: 'View Players',
    path: '/coaching/playerdata/player',
  },
  {
    icon: '⚖️',
    title: 'Player Comparison',
    description: 'Compare two players side by side across all available stat categories.',
    label: 'Compare Players',
    path: '/coaching/playerdata/compare',
  },
  {
    icon: '📋',
    title: 'Teamsheets',
    description: 'Build, duplicate, and manage teamsheets for your clubs and fixtures.',
    label: 'View Teamsheets',
    path: '/coaching/teamsheets',
  },
  {
    icon: '🎯',
    title: 'Predictions',
    description: 'Run match outcome predictions powered by historical data and Elo ratings.',
    label: 'Open Predictions',
    path: '/coaching/predictions',
  },
  {
    icon: '📡',
    title: 'Live Football',
    description: 'Follow live competitions, league tables, and up-to-date match data.',
    label: 'Go to Live Football',
    path: '/livefootball',
  },
];

export const CoachingBase = () => {
  const navigate = useNavigate();

  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <div>
          <h1 className={styles.title}>Coaching Hub</h1>
          <p className={styles.subtitle}>
            Everything you need to manage your clubs, analyse players, build teamsheets, and track live football.
          </p>
        </div>
      </section>

      <div className={styles.grid}>
        {SECTIONS.map((section) => (
          <div key={section.path} className={styles.card}>
            <div className={styles.cardIcon}>{section.icon}</div>
            <h2 className={styles.cardTitle}>{section.title}</h2>
            <p className={styles.cardDescription}>{section.description}</p>
            <button
              className={styles.cardButton}
              type="button"
              onClick={() => navigate(section.path)}
            >
              {section.label}
              <span className={styles.cardButtonArrow}>→</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
