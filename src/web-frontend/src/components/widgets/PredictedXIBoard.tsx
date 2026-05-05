import NullStatePlaceholder from './NullStatePlaceholder';
import type { LineupData, PredictedPlayer } from '../../services/api/widgetApi';
import styles from './css/PredictedXIBoard.module.css';

const CONFIDENCE_GREEN_THRESHOLD = 0.8;
const CONFIDENCE_AMBER_THRESHOLD = 0.6;
const PITCH_MIN_WIDTH_PX = 320;

const POSITION_GROUP_ORDER = ['GK', 'DEF', 'MID', 'FWD'] as const;

interface PredictedXIBoardProps {
  lineup: LineupData;
  showConfidence?: boolean;
}

function confidenceClass(prob: number): string {
  if (prob >= CONFIDENCE_GREEN_THRESHOLD) return styles.playerGreen;
  if (prob >= CONFIDENCE_AMBER_THRESHOLD) return styles.playerAmber;
  return styles.playerRed;
}

function parseFormation(formation: string | null): number[] {
  if (!formation) return [];
  return formation.split('-').map(n => parseInt(n, 10)).filter(n => !isNaN(n));
}

function groupByPosition(players: PredictedPlayer[]): Record<string, PredictedPlayer[]> {
  const groups: Record<string, PredictedPlayer[]> = { GK: [], DEF: [], MID: [], FWD: [] };
  for (const player of players) {
    const pos = player.position.toUpperCase();
    if (pos === 'GK') groups.GK.push(player);
    else if (['CB', 'RB', 'LB', 'RWB', 'LWB', 'DEF', 'SW'].includes(pos)) groups.DEF.push(player);
    else if (['CM', 'CAM', 'CDM', 'DM', 'AM', 'MID', 'RM', 'LM'].includes(pos)) groups.MID.push(player);
    else groups.FWD.push(player);
  }
  return groups;
}

function PlayerMarker({ player, showConfidence }: { player: PredictedPlayer; showConfidence: boolean }) {
  return (
    <div className={`${styles.playerMarker} ${confidenceClass(player.start_prob)}`}>
      {player.position && (
        <span className={styles.playerMarkerPos}>{player.position.toUpperCase()}</span>
      )}
      <span className={styles.playerMarkerName}>{player.name}</span>
      {showConfidence && (
        <span className={styles.playerMarkerProb}>
          {Math.round(player.start_prob * 100)}%
        </span>
      )}
    </div>
  );
}

function PitchLayout({ players, formation, showConfidence }: {
  players: PredictedPlayer[];
  formation: string | null;
  showConfidence: boolean;
}) {
  const rows = parseFormation(formation);

  if (rows.length === 0) {
    return (
      <div className={styles.flatList}>
        {players.map((p, i) => (
          <PlayerMarker key={p.name || `player-${i}`} player={p} showConfidence={showConfidence} />
        ))}
      </div>
    );
  }

  const gk = players.slice(0, 1);
  const outfield = players.slice(1);

  const assigned: PredictedPlayer[][] = [];
  let cursor = 0;
  for (const count of rows) {
    assigned.push(outfield.slice(cursor, cursor + count));
    cursor += count;
  }

  const rowsReversed = [...assigned].reverse();

  return (
    <div className={styles.pitch} style={{ minWidth: PITCH_MIN_WIDTH_PX }}>
      {formation && <span className={styles.formationBadge}>{formation}</span>}
      {rowsReversed.map((row, i) => (
        <div key={i} className={styles.pitchRow}>
          {row.map((p, pi) => (
            <PlayerMarker key={p.name || `row-${i}-player-${pi}`} player={p} showConfidence={showConfidence} />
          ))}
        </div>
      ))}
      <div className={styles.pitchRow}>
        {gk.map((p, gi) => (
          <PlayerMarker key={p.name || `gk-${gi}`} player={p} showConfidence={showConfidence} />
        ))}
      </div>
    </div>
  );
}

function MobileList({ players }: { players: PredictedPlayer[] }) {
  const groups = groupByPosition(players);
  return (
    <div className={styles.mobileList}>
      {POSITION_GROUP_ORDER.map(group => {
        const groupPlayers = groups[group];
        if (!groupPlayers || groupPlayers.length === 0) return null;
        return (
          <div key={group} className={styles.mobileGroup}>
            <span className={styles.mobileGroupLabel}>{group}</span>
            <div className={styles.mobileGroupPlayers}>
              {groupPlayers.map((p, pi) => (
                <span key={p.name || `${group}-player-${pi}`} className={styles.mobilePlayerName}>{p.name}</span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function PredictedXIBoard({ lineup, showConfidence = true }: PredictedXIBoardProps) {
  if (!lineup.predicted_xi || lineup.predicted_xi.length === 0) {
    return (
      <NullStatePlaceholder
        icon="shield"
        message="Predicted XI not available for this team"
      />
    );
  }

  return (
    <div className={styles.board}>
      <div className={styles.desktopView}>
        <PitchLayout
          players={lineup.predicted_xi}
          formation={lineup.formation}
          showConfidence={showConfidence}
        />
      </div>
      <div className={styles.mobileView}>
        <MobileList players={lineup.predicted_xi} />
      </div>
    </div>
  );
}