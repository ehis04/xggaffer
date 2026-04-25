import type { ClubPlayer } from '../../types/clubPlayers';
import type { ClubPlayerManualStats } from '../../types/club';
import type { PlayerSeasonSummary } from '../../types/playerdata';
import styles from './css/PlayerXgWidget.module.css';

interface Props {
  player: ClubPlayer | null;
  manualStats: ClubPlayerManualStats | null;
  externalSummary?: PlayerSeasonSummary | null;
}

type PositionGroup = 'gk' | 'defender' | 'midfielder' | 'attacker';

type StatKey =
  | 'xg' | 'npxg' | 'xa' | 'shots' | 'key_passes' | 'dribbles_completed'
  | 'tackles' | 'interceptions' | 'aerials_won' | 'clearances'
  | 'saves' | 'save_percentage' | 'clean_sheets' | 'goals_conceded';

interface StatDef {
  key: StatKey;
  label: string;
  decimals: number;
  suffix?: string;
}

const POSITION_GROUP_MAP: Record<string, PositionGroup> = {
  GK: 'gk',
  RB: 'defender', RWB: 'defender', CB: 'defender', RCB: 'defender',
  CCB: 'defender', LCB: 'defender', LB: 'defender', LWB: 'defender',
  RDM: 'midfielder', CDM: 'midfielder', LDM: 'midfielder',
  CM: 'midfielder', RM: 'midfielder', LM: 'midfielder',
  RAM: 'attacker', CAM: 'attacker', LAM: 'attacker',
  RW: 'attacker', LW: 'attacker', CF: 'attacker', ST: 'attacker',
};

const STATS_BY_GROUP: Record<PositionGroup, StatDef[]> = {
  gk: [
    { key: 'saves',           label: 'Saves',          decimals: 0 },
    { key: 'save_percentage', label: 'Save %',         decimals: 1, suffix: '%' },
    { key: 'clean_sheets',    label: 'Clean sheets',   decimals: 0 },
    { key: 'goals_conceded',  label: 'Goals conceded', decimals: 0 },
  ],
  defender: [
    { key: 'aerials_won',    label: 'Aerials won',    decimals: 0 },
    { key: 'tackles',        label: 'Tackles',        decimals: 0 },
    { key: 'interceptions',  label: 'Interceptions',  decimals: 0 },
    { key: 'clearances',     label: 'Clearances',     decimals: 0 },
    { key: 'xa',             label: 'xA',             decimals: 2 },
  ],
  midfielder: [
    { key: 'xa',                  label: 'xA',              decimals: 2 },
    { key: 'xg',                  label: 'xG',              decimals: 2 },
    { key: 'key_passes',          label: 'Key passes',      decimals: 0 },
    { key: 'tackles',             label: 'Tackles',         decimals: 0 },
    { key: 'interceptions',       label: 'Interceptions',   decimals: 0 },
    { key: 'dribbles_completed',  label: 'Dribbles',        decimals: 0 },
  ],
  attacker: [
    { key: 'xg',                 label: 'xG',          decimals: 2 },
    { key: 'npxg',               label: 'npxG',        decimals: 2 },
    { key: 'xa',                 label: 'xA',          decimals: 2 },
    { key: 'shots',              label: 'Shots',       decimals: 0 },
    { key: 'key_passes',         label: 'Key passes',  decimals: 0 },
    { key: 'dribbles_completed', label: 'Dribbles',    decimals: 0 },
  ],
};

const LEAGUE_AVERAGES: Record<PositionGroup, Partial<Record<StatKey, number>>> = {
  gk: {
    saves: 3.2,
    save_percentage: 72,
    clean_sheets: 4,
    goals_conceded: 18,
  },
  defender: {
    aerials_won: 2.1,
    tackles: 1.8,
    interceptions: 1.4,
    clearances: 3.2,
    xa: 0.03,
  },
  midfielder: {
    xa: 0.06,
    xg: 0.05,
    key_passes: 1.4,
    tackles: 1.5,
    interceptions: 1.1,
    dribbles_completed: 0.9,
  },
  attacker: {
    xg: 0.25,
    npxg: 0.22,
    xa: 0.08,
    shots: 2.4,
    key_passes: 1.1,
    dribbles_completed: 1.3,
  },
};

type Grade = 'A+' | 'A' | 'A-' | 'B+' | 'B' | 'B-' | 'C+' | 'C' | 'C-' | 'D+' | 'D' | 'D-';

interface GradeResult {
  grade: Grade;
  colour: string;
  bg: string;
}

const GRADE_SCALE: Grade[] = [
  'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-',
];

const GRADE_COLOURS: Record<Grade, { colour: string; bg: string }> = {
  'A+': { colour: '#1adb6e', bg: 'rgba(26,219,110,0.13)' },
  'A':  { colour: '#3dd68c', bg: 'rgba(61,214,140,0.13)' },
  'A-': { colour: '#5dd4a0', bg: 'rgba(93,212,160,0.13)' },
  'B+': { colour: '#8ecf3d', bg: 'rgba(142,207,61,0.13)' },
  'B':  { colour: '#b8d43d', bg: 'rgba(184,212,61,0.13)' },
  'B-': { colour: '#d4c83d', bg: 'rgba(212,200,61,0.13)' },
  'C+': { colour: '#d4a83d', bg: 'rgba(212,168,61,0.13)' },
  'C':  { colour: '#d4883d', bg: 'rgba(212,136,61,0.13)' },
  'C-': { colour: '#d4683d', bg: 'rgba(212,104,61,0.13)' },
  'D+': { colour: '#d4563d', bg: 'rgba(212,86,61,0.13)'  },
  'D':  { colour: '#d44e3d', bg: 'rgba(212,78,61,0.13)'  },
  'D-': { colour: '#a01a1a', bg: 'rgba(160,26,26,0.13)'  },
};

const gradeRatio = (ratio: number): GradeResult => {
  const idx = Math.min(
    GRADE_SCALE.length - 1,
    Math.max(0, Math.floor((1 - Math.min(ratio, 3) / 3) * GRADE_SCALE.length))
  );
  const grade = GRADE_SCALE[idx];
  return { grade, ...GRADE_COLOURS[grade] };
};

const gradeStatValue = (
  key: StatKey,
  value: number,
  group: PositionGroup
): GradeResult => {
  const avg = LEAGUE_AVERAGES[group][key];
  if (!avg || avg === 0) return { grade: 'C', ...GRADE_COLOURS['C'] };

  const isInverted = key === 'goals_conceded';
  const ratio = isInverted ? avg / Math.max(value, 0.01) : value / avg;
  return gradeRatio(ratio);
};

const overallGrade = (
  stats: ClubPlayerManualStats,
  group: PositionGroup
): GradeResult => {
  const defs = STATS_BY_GROUP[group];
  const graded = defs
    .map((d) => {
      const raw = stats[d.key as keyof ClubPlayerManualStats];
      if (raw === null || raw === undefined) return null;
      return gradeStatValue(d.key, Number(raw), group);
    })
    .filter((g): g is GradeResult => g !== null);

  if (graded.length === 0) return { grade: 'C', ...GRADE_COLOURS['C'] };

  const avgIdx = Math.round(
    graded.reduce((sum, g) => sum + GRADE_SCALE.indexOf(g.grade), 0) / graded.length
  );
  const grade = GRADE_SCALE[Math.min(avgIdx, GRADE_SCALE.length - 1)];
  return { grade, ...GRADE_COLOURS[grade] };
};

const formatValue = (
  stats: ClubPlayerManualStats,
  def: StatDef
): string => {
  const raw = stats[def.key as keyof ClubPlayerManualStats];
  if (raw === null || raw === undefined) return '—';
  const num = Number(raw);
  return `${num.toFixed(def.decimals)}${def.suffix ?? ''}`;
};

const getExternalValue = (
  metrics: PlayerSeasonSummary['metrics'],
  key: string
): number | null => {
  if (!metrics) return null;
  const m = metrics.find((metric) => metric.key === key);
  return m?.value ?? null;
};

const overallGradeFromExternal = (
  metrics: PlayerSeasonSummary['metrics'],
  group: PositionGroup
): GradeResult => {
  const defs = STATS_BY_GROUP[group];
  const graded = defs
    .map((d) => {
      const v = getExternalValue(metrics, d.key);
      if (v === null) return null;
      return gradeStatValue(d.key, v, group);
    })
    .filter((g): g is GradeResult => g !== null);

  if (graded.length === 0) return { grade: 'C', ...GRADE_COLOURS['C'] };
  const avgIdx = Math.round(
    graded.reduce((sum, g) => sum + GRADE_SCALE.indexOf(g.grade), 0) / graded.length
  );
  const grade = GRADE_SCALE[Math.min(avgIdx, GRADE_SCALE.length - 1)];
  return { grade, ...GRADE_COLOURS[grade] };
};

export const PlayerXgWidget = ({ player, manualStats, externalSummary }: Props) => {
  if (!player) {
    return (
      <div className={styles.empty}>
        <span className={styles.emptyText}>Select a player.</span>
      </div>
    );
  }

  const group: PositionGroup =
    POSITION_GROUP_MAP[player.primary_position ?? ''] ?? 'attacker';
  const statDefs = STATS_BY_GROUP[group];

  if (!manualStats) {
    const extMetrics = externalSummary?.metrics;
    const hasExternal = extMetrics && extMetrics.length > 0;

    if (!hasExternal) {
      return (
        <div className={styles.widget}>
          <div className={styles.header}>
            <div className={styles.playerInfo}>
              <span className={styles.playerName}>
                {player.display_name || `${player.first_name} ${player.last_name}`.trim()}
              </span>
              <span className={styles.playerPos}>{player.primary_position || '—'}</span>
            </div>
            <div className={styles.overallBadge} style={{ color: '#888', background: 'rgba(255,255,255,0.05)' }}>
              <span className={styles.overallGrade}>—</span>
              <span className={styles.overallLbl}>Not updated</span>
            </div>
          </div>
          <div className={styles.divider} />
          <p className={styles.noStats}>
            No stats recorded yet. Add them in the Players tab.
          </p>
        </div>
      );
    }

    const overall = overallGradeFromExternal(extMetrics, group);
    const ctx = externalSummary?.context;

    return (
      <div className={styles.widget}>
        <div className={styles.header}>
          <div className={styles.playerInfo}>
            <span className={styles.playerName}>
              {player.display_name || `${player.first_name} ${player.last_name}`.trim()}
            </span>
            <span className={styles.playerPos}>{player.primary_position || '—'}</span>
          </div>
          <div
            className={styles.overallBadge}
            style={{ color: overall.colour, background: overall.bg }}
            title="Overall grade"
          >
            <span className={styles.overallGrade}>{overall.grade}</span>
            <span className={styles.overallLbl}>Overall</span>
          </div>
        </div>

        <div className={styles.divider} />

        <div className={styles.statList}>
          {statDefs.map((def) => {
            const value = getExternalValue(extMetrics, def.key);
            const hasValue = value !== null;
            const gradeResult = hasValue ? gradeStatValue(def.key, value, group) : null;
            const displayValue = hasValue ? `${value.toFixed(def.decimals)}${def.suffix ?? ''}` : '—';
            const avg = LEAGUE_AVERAGES[group][def.key];

            return (
              <div key={def.key} className={styles.statRow}>
                <span className={styles.statLabel}>{def.label}</span>
                <div className={styles.statBar}>
                  <div
                    className={styles.statBarFill}
                    style={{
                      width: hasValue && avg
                        ? `${Math.min((value / (avg * 2)) * 100, 100)}%`
                        : '0%',
                      background: gradeResult?.colour ?? 'rgba(255,255,255,0.1)',
                    }}
                  />
                </div>
                <span className={styles.statValue}>{displayValue}</span>
                {gradeResult ? (
                  <span
                    className={styles.statGrade}
                    style={{ color: gradeResult.colour, background: gradeResult.bg }}
                  >
                    {gradeResult.grade}
                  </span>
                ) : (
                  <span className={styles.statGradeEmpty}>—</span>
                )}
              </div>
            );
          })}
        </div>

        <div className={styles.divider} />
        <p className={styles.season}>
          {ctx?.season ?? '—'} · understat + sofascore
        </p>
      </div>
    );
  }

  const overall = overallGrade(manualStats, group);

  return (
    <div className={styles.widget}>
      <div className={styles.header}>
        <div className={styles.playerInfo}>
          <span className={styles.playerName}>
            {player.display_name || `${player.first_name} ${player.last_name}`.trim()}
          </span>
          <span className={styles.playerPos}>{player.primary_position || '—'}</span>
        </div>
        <div
          className={styles.overallBadge}
          style={{ color: overall.colour, background: overall.bg }}
          title="Overall grade"
        >
          <span className={styles.overallGrade}>{overall.grade}</span>
          <span className={styles.overallLbl}>Overall</span>
        </div>
      </div>

      <div className={styles.divider} />

      <div className={styles.statList}>
        {statDefs.map((def) => {
          const raw = manualStats[def.key as keyof ClubPlayerManualStats];
          const hasValue = raw !== null && raw !== undefined;
          const gradeResult = hasValue
            ? gradeStatValue(def.key, Number(raw), group)
            : null;
          const displayValue = formatValue(manualStats, def);
          const avg = LEAGUE_AVERAGES[group][def.key];

          return (
            <div key={def.key} className={styles.statRow}>
              <span className={styles.statLabel}>{def.label}</span>
              <div className={styles.statBar}>
                <div
                  className={styles.statBarFill}
                  style={{
                    width: hasValue && avg
                      ? `${Math.min((Number(raw) / (avg * 2)) * 100, 100)}%`
                      : '0%',
                    background: gradeResult?.colour ?? 'rgba(255,255,255,0.1)',
                  }}
                />
              </div>
              <span className={styles.statValue}>{displayValue}</span>
              {gradeResult ? (
                <span
                  className={styles.statGrade}
                  style={{ color: gradeResult.colour, background: gradeResult.bg }}
                >
                  {gradeResult.grade}
                </span>
              ) : (
                <span className={styles.statGradeEmpty}>—</span>
              )}
            </div>
          );
        })}
      </div>

      <div className={styles.divider} />
      <p className={styles.season}>
        {manualStats.season} · {manualStats.appearances ?? '?'} apps · {manualStats.minutes_played ?? '?'} mins
      </p>
    </div>
  );
};