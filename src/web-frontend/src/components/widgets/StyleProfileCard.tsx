import NullStatePlaceholder from './NullStatePlaceholder';
import type { StyleCluster } from '../../services/api/widgetApi';
import styles from './css/StyleProfileCard.module.css';

const MAX_SIMILAR_TEAMS_DISPLAYED = 4;

const STYLE_LABEL_DISPLAY: Record<string, string> = {
  elite_final_third_possession: 'Elite Final-Third Possession',
  league_average_buildup: 'League Average Build-up',
  deep_central_control: 'Deep Central Control',
  unknown: 'Unknown Style',
};

interface StyleProfileCardProps {
  styleCluster: StyleCluster | null;
}

function formatLabel(raw: string): string {
  return STYLE_LABEL_DISPLAY[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export default function StyleProfileCard({ styleCluster }: StyleProfileCardProps) {
  if (!styleCluster) {
    return (
      <NullStatePlaceholder
        icon="shield"
        message="Style profile not available"
      />
    );
  }

  const displayedTeams = styleCluster.similar_teams.slice(0, MAX_SIMILAR_TEAMS_DISPLAYED);

  return (
    <div className={styles.card}>
      <p className={styles.clusterLabel}>{formatLabel(styleCluster.label)}</p>
      {displayedTeams.length > 0 && (
        <div className={styles.similarTeams}>
          <p className={styles.similarLabel}>Similar style to</p>
          <div className={styles.teamChips}>
            {displayedTeams.map(team => (
              <span key={team} className={styles.teamChip}>{team}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}