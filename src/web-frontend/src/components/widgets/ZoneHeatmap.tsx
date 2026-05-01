import NullStatePlaceholder from './NullStatePlaceholder';
import type { ZoneProfile } from '../../services/api/widgetApi';
import styles from './css/ZoneHeatmap.module.css';

const ZONE_GRID_COLS = 3;
const ZONE_GRID_ROWS = 3;
const HEATMAP_MIN_HEIGHT_PX = 240;
const HEATMAP_MIN_WIDTH_PX = 320;

const ZONE_ORDER = [
  'ATK-L', 'ATK-C', 'ATK-R',
  'MID-L', 'MID-C', 'MID-R',
  'DEF-L', 'DEF-C', 'DEF-R',
] as const;

const ZONE_SHORT: Record<string, string> = {
  'ATK-L': 'ATK-L', 'ATK-C': 'ATK-C', 'ATK-R': 'ATK-R',
  'MID-L': 'MID-L', 'MID-C': 'MID-C', 'MID-R': 'MID-R',
  'DEF-L': 'DEF-L', 'DEF-C': 'DEF-C', 'DEF-R': 'DEF-R',
};

const ZONE_LONG: Record<string, string> = {
  'ATK-L': 'Attacking left',
  'ATK-C': 'Attacking centre',
  'ATK-R': 'Attacking right',
  'MID-L': 'Midfield left',
  'MID-C': 'Midfield centre',
  'MID-R': 'Midfield right',
  'DEF-L': 'Defensive left',
  'DEF-C': 'Defensive centre',
  'DEF-R': 'Defensive right',
};

interface ZoneHeatmapProps {
  zoneProfiles: ZoneProfile[] | null;
  team: string;
}

function strengthClass(flag: ZoneProfile['strength_flag']): string {
  if (flag === 'strength') return styles.cellStrength;
  if (flag === 'weakness') return styles.cellWeakness;
  return styles.cellNeutral;
}

export default function ZoneHeatmap({ zoneProfiles, team }: ZoneHeatmapProps) {
  if (!zoneProfiles || zoneProfiles.length === 0) {
    return (
      <NullStatePlaceholder
        icon="chart"
        message="Tactical profile not available for this team"
      />
    );
  }

  const byName = Object.fromEntries(
    zoneProfiles.map(z => [z.zone_name, z])
  );

  const ordered = ZONE_ORDER.map(name => byName[name] ?? null);
  const strongestZone = ordered
    .filter((zone): zone is ZoneProfile => zone !== null)
    .reduce<ZoneProfile | null>((best, zone) => {
      if (!best) return zone;
      return zone.pass_success_rate > best.pass_success_rate ? zone : best;
    }, null);

  return (
    <div className={styles.wrapper}>
      <div className={styles.pitchCard}>
        <div className={styles.pitchHeader}>
          <div>
            <p className={styles.teamLabel}>{team}</p>
            <h3 className={styles.pitchTitle}>Ball retention map</h3>
          </div>
          <p className={styles.pitchSummary}>
            Percentages show completed-pass success in each zone for this team profile.
          </p>
        </div>

        <div className={styles.pitchSurface}>
          <div className={styles.halfwayLine} aria-hidden="true" />
          <div className={styles.centreCircle} aria-hidden="true" />
          <div className={styles.penaltyBoxTop} aria-hidden="true" />
          <div className={styles.penaltyBoxBottom} aria-hidden="true" />
          <div
            className={styles.grid}
            style={{
              minHeight: HEATMAP_MIN_HEIGHT_PX,
              minWidth: HEATMAP_MIN_WIDTH_PX,
              gridTemplateColumns: `repeat(${ZONE_GRID_COLS}, 1fr)`,
              gridTemplateRows: `repeat(${ZONE_GRID_ROWS}, 1fr)`,
            }}
          >
            {ordered.map((zone, i) => {
              if (!zone) {
                return (
                  <div key={`zone-empty-${i}`} className={`${styles.cell} ${styles.cellNeutral}`}>
                    <span className={styles.cellLabel}>—</span>
                    <span className={styles.cellSubLabel}>No profile data</span>
                  </div>
                );
              }
              return (
                <div
                  key={zone.zone_name}
                  className={`${styles.cell} ${strengthClass(zone.strength_flag)}`}
                  tabIndex={0}
                >
                  <span className={styles.cellLabel}>{ZONE_SHORT[zone.zone_name] ?? zone.zone_name}</span>
                  <span className={styles.cellSubLabel}>{ZONE_LONG[zone.zone_name] ?? zone.zone_name}</span>
                  <span className={styles.cellRate}>
                    {(zone.pass_success_rate * 100).toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className={styles.legend}>
          <span className={`${styles.legendSwatch} ${styles.swatchStrength}`} />
          <span className={styles.legendLabel}>Strength: one of this team&apos;s cleaner passing zones in the profile</span>
          <span className={`${styles.legendSwatch} ${styles.swatchNeutral}`} />
          <span className={styles.legendLabel}>Neutral: close to the team&apos;s normal baseline</span>
          <span className={`${styles.legendSwatch} ${styles.swatchWeakness}`} />
          <span className={styles.legendLabel}>Weakness: a zone where their pass completion drops off</span>
        </div>

        <div className={styles.notes}>
          <p className={styles.noteTitle}>How to read this pitch</p>
          <p className={styles.noteText}>
            Zone tags use pitch thirds and lanes. For example, ATK-L means the attacking-left channel and MID-C means the central midfield lane.
          </p>
          <p className={styles.noteText}>
            A number like 93.2% means this team completed 93.2% of tracked passes played in that zone within the underlying tactical sample.
          </p>
          <p className={styles.noteText}>
            The colours are relative to this team&apos;s own zone profile, not a league-wide average. A neutral zone is not bad; it just sits near the team&apos;s usual level.
          </p>
          {strongestZone && (
            <p className={styles.noteHighlight}>
              Highest pass success in this snapshot: {ZONE_LONG[strongestZone.zone_name] ?? strongestZone.zone_name} at {(strongestZone.pass_success_rate * 100).toFixed(1)}%.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}