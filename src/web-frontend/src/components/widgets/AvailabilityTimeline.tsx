import AvailabilityBadge from '../predictions/AvailabilityBadge';
import UncertaintyNote from './UncertaintyNote';
import type { AvailabilityData, PlayerAvailability } from '../../services/api/widgetApi';
import styles from './css/AvailabilityTimeline.module.css';

const RISK_GROUP_ORDER = ['unavailable', 'at_risk', 'available'] as const;

const RISK_LABEL_MAP: Record<string, string> = {
  unavailable: 'Unavailable',
  at_risk: 'At Risk',
  available: 'Available',
};

interface AvailabilityTimelineProps {
  availability: AvailabilityData;
}

function riskToScore(risk: PlayerAvailability['risk_level']): string {
  if (risk === 'unavailable') return 'high';
  if (risk === 'at_risk') return 'medium';
  return 'low';
}

export default function AvailabilityTimeline({ availability }: AvailabilityTimelineProps) {
  const { players, summary } = availability;

  if (players.length === 0) {
    return <UncertaintyNote message="No availability data for this fixture" />;
  }

  const grouped: Record<string, PlayerAvailability[]> = {
    unavailable: [],
    at_risk: [],
    available: [],
  };

  for (const player of players) {
    grouped[player.risk_level]?.push(player);
  }

  return (
    <div className={styles.timeline}>
      <div className={styles.summaryRow}>
        <span className={styles.summaryChip} data-variant="available">
          {summary.available_count} available
        </span>
        <span className={styles.summaryChip} data-variant="at_risk">
          {summary.high_risk_count} at risk
        </span>
        <span className={styles.summaryChip} data-variant="unavailable">
          {summary.unavailable_count} unavailable
        </span>
      </div>

      {RISK_GROUP_ORDER.map(group => {
        const groupPlayers = grouped[group];
        if (!groupPlayers || groupPlayers.length === 0) return null;
        return (
          <div key={group} className={styles.group}>
            <p className={`${styles.groupLabel} ${styles[`groupLabel_${group}`]}`}>
              {RISK_LABEL_MAP[group]}
            </p>
            {groupPlayers.map((player, playerIdx) => (
              <div key={player.name || `player-${playerIdx}`} className={styles.playerRow}>
                <span className={styles.playerName}>{player.name}</span>
                <AvailabilityBadge
                  riskLabel={riskToScore(player.risk_level)}
                  isLoading={false}
                />
                <span className={styles.probPct}>
                  {Math.round(player.availability_prob * 100)}%
                </span>
                {player.return_date_estimate && (
                  <span className={styles.returnDate}>
                    Est. return: {player.return_date_estimate}
                  </span>
                )}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}