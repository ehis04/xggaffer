import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import NullStatePlaceholder from './NullStatePlaceholder';
import UncertaintyNote from './UncertaintyNote';
import type { WidgetFreshness } from '../../services/api/widgetApi';
import styles from './css/StrengthComparisonStrip.module.css';

const ELO_STRENGTH_BAR_MAX_DELTA = 400;
const ELO_BAR_BASE_PCT = 50;

interface StrengthComparisonStripProps {
  homeTeam: string;
  awayTeam: string;
  homeElo: number | null;
  awayElo: number | null;
  freshness: WidgetFreshness;
}

function deltaLabel(home: number, away: number, homeTeam: string, awayTeam: string): string {
  const delta = Math.round(Math.abs(home - away));
  const stronger = home > away ? homeTeam : awayTeam;
  return `${stronger} rated ${delta} points higher`;
}

function homeBarPct(home: number, away: number): number {
  const delta = home - away;
  const capped = Math.max(-ELO_STRENGTH_BAR_MAX_DELTA, Math.min(ELO_STRENGTH_BAR_MAX_DELTA, delta));
  return ELO_BAR_BASE_PCT + (capped / ELO_STRENGTH_BAR_MAX_DELTA) * ELO_BAR_BASE_PCT;
}

export default function StrengthComparisonStrip({
  homeTeam,
  awayTeam,
  homeElo,
  awayElo,
  freshness,
}: StrengthComparisonStripProps) {
  if (homeElo === null && awayElo === null) {
    return (
      <NullStatePlaceholder
        icon="shield"
        message="Elo strength ratings not available"
      />
    );
  }

  const homePct = homeElo !== null && awayElo !== null
    ? homeBarPct(homeElo, awayElo)
    : ELO_BAR_BASE_PCT;

  const bothPresent = homeElo !== null && awayElo !== null;

  return (
    <div className={styles.strip}>
      <div className={styles.teamRow}>
        <div className={styles.teamBlock}>
          <span className={styles.teamName}>{homeTeam}</span>
          <span className={styles.eloValue}>{homeElo !== null ? Math.round(homeElo) : '–'}</span>
        </div>
        <div className={styles.teamBlock}>
          <span className={styles.eloValue}>{awayElo !== null ? Math.round(awayElo) : '–'}</span>
          <span className={styles.teamName}>{awayTeam}</span>
        </div>
      </div>

      <div className={styles.barTrack}>
        <div className={styles.barHome} style={{ width: `${homePct}%` }} />
        <div className={styles.barAway} style={{ width: `${100 - homePct}%` }} />
      </div>

      {bothPresent ? (
        <p className={styles.deltaText}>{deltaLabel(homeElo!, awayElo!, homeTeam, awayTeam)}</p>
      ) : (
        <UncertaintyNote message="One team's Elo not available — bar shown at 50/50" />
      )}

      <div className={styles.badgeRow}>
        <FreshnessBadge freshness={freshness} />
      </div>
    </div>
  );
}