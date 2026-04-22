import type { OddsComparisonEngineData } from '../../../types/prediction';
import ProbabilityBar from '../../../common/ProbabilityBar';
import OddsComparisonCard from './OddsComparisonCard';
import styles from './css/StructuredResponseBlock.module.css';

interface StructuredResponseBlockProps {
  queryType: string;
  engineData: Record<string, unknown>;
  partial: boolean;
  error: string | null;
  onExampleClick?: (query: string) => void;
}

interface TopFactor {
  feature: string;
  value: number;
  contribution: number;
  description: string;
}

interface Player {
  name: string;
  risk_score?: number;
  risk_label?: string;
}

interface PredictedPlayer {
  name: string;
  position: string;
  start_probability?: number;
}

interface Capability {
  description: string;
  example: string;
}

interface ProbabilitySet {
  home: number;
  draw: number;
  away: number;
}

function isOddsComparisonEngineData(data: unknown): data is OddsComparisonEngineData {
  if (typeof data !== 'object' || data === null) {
    return false;
  }

  const candidate = data as Record<string, unknown>;

  return (
    typeof candidate.home_team === 'string' &&
    typeof candidate.away_team === 'string' &&
    typeof candidate.league === 'string' &&
    typeof candidate.season === 'string' &&
    typeof candidate.market === 'object' &&
    candidate.market !== null &&
    typeof candidate.comparison === 'object' &&
    candidate.comparison !== null &&
    Array.isArray(candidate.bookmakers) &&
    typeof candidate.support === 'object' &&
    candidate.support !== null
  );
}

function getProbabilities(data: Record<string, unknown>): ProbabilitySet | null {
  const probabilities = data.probabilities as Partial<ProbabilitySet> | undefined;

  if (
    typeof probabilities?.home !== 'number' ||
    typeof probabilities.draw !== 'number' ||
    typeof probabilities.away !== 'number'
  ) {
    return null;
  }

  return {
    home: probabilities.home,
    draw: probabilities.draw,
    away: probabilities.away,
  };
}

function getRiskClass(label?: string, score?: number): string {
  const effective =
    label?.toLowerCase() ??
    (score !== undefined ? (score > 0.6 ? 'high' : score > 0.3 ? 'medium' : 'low') : 'low');

  if (effective === 'high') return styles.riskHigh;
  if (effective === 'medium') return styles.riskMedium;
  return styles.riskLow;
}

export default function StructuredResponseBlock({
  queryType,
  engineData,
  partial,
  error,
  onExampleClick,
}: StructuredResponseBlockProps) {
  if (partial && Object.keys(engineData).length === 0) {
    return (
      <div className={styles.partialNote}>
        Detailed analytics data is unavailable for this query.
      </div>
    );
  }

  switch (queryType) {
    case 'MATCH_PREDICTION': {
      const topFactors = engineData.top_factors as TopFactor[] | undefined;
      const metrics = engineData.metrics as { accuracy: number } | undefined;
      const probabilities = getProbabilities(engineData);

      return (
        <div className={styles.panel}>
          {probabilities && <ProbabilityBar probabilities={probabilities} />}
          {topFactors && topFactors.length > 0 && (
            <div className={styles.factorsList}>
              <p className={styles.sectionLabel}>Top factors</p>
              {topFactors.slice(0, 5).map((f, i) => (
                <div key={i} className={styles.factorRow}>
                  <span className={styles.factorDesc}>{f.description}</span>
                  <span className={f.contribution >= 0 ? styles.contribPos : styles.contribNeg}>
                    {f.contribution >= 0 ? '+' : ''}
                    {f.contribution.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
          {metrics?.accuracy !== undefined && (
            <span className={styles.accuracyBadge}>
              Model accuracy: {Math.round(metrics.accuracy * 100)}%
            </span>
          )}
        </div>
      );
    }

    case 'ODDS_COMPARISON':
      if (!isOddsComparisonEngineData(engineData)) {
        return (
          <div className={styles.partialNote}>
            Detailed analytics data is unavailable for this query.
          </div>
        );
      }

      return (
        <OddsComparisonCard
          engineData={engineData}
          partial={partial}
          error={error}
        />
      );

    case 'GLOSSARY': {
      const definition = engineData.definition as string | undefined;
      const term = engineData.term as string | undefined;
      const allTerms = engineData.all_terms as string[] | undefined;

      if (allTerms) {
        return (
          <div className={styles.panel}>
            <p className={styles.sectionLabel}>Available terms</p>
            <ul className={styles.termList}>
              {allTerms.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        );
      }

      return (
        <div className={styles.panel}>
          {term && <h3 className={styles.glossaryTerm}>{term.toUpperCase()}</h3>}
          {definition && <p className={styles.glossaryDef}>{definition}</p>}
        </div>
      );
    }

    case 'ELO_QUERY': {
      const team = engineData.team as string | undefined;
      const eloRating = engineData.elo_rating as number | undefined;
      const awayTeam = engineData.away_team as string | undefined;
      const awayElo = engineData.away_elo_rating as number | undefined;

      return (
        <div className={styles.panel}>
          <div className={styles.eloRow}>
            {team && eloRating !== undefined && (
              <div className={styles.eloCard}>
                <span className={styles.eloTeam}>{team}</span>
                <span className={styles.eloRating}>{Math.round(eloRating)}</span>
              </div>
            )}
            {awayTeam && awayElo !== undefined && (
              <div className={styles.eloCard}>
                <span className={styles.eloTeam}>{awayTeam}</span>
                <span className={styles.eloRating}>{Math.round(awayElo)}</span>
              </div>
            )}
          </div>
        </div>
      );
    }

    case 'SEASON_SIMULATION': {
      const titleProbs = engineData.title_probabilities as Record<string, number> | undefined;
      const relegationProbs = engineData.relegation_probabilities as
        | Record<string, number>
        | undefined;

      if (!titleProbs) return null;

      const sorted = Object.entries(titleProbs)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5);

      return (
        <div className={styles.panel}>
          <p className={styles.sectionLabel}>Title probabilities</p>
          {sorted.map(([team, prob]) => {
            const pct = Math.round(prob * 100);
            return (
              <div key={team} className={styles.simRow}>
                <span className={styles.simTeam}>{team}</span>
                <div className={styles.simBarWrap}>
                  <div className={styles.simBar} style={{ width: `${pct}%` }} />
                </div>
                <span className={styles.simPct}>{pct}%</span>
              </div>
            );
          })}
          {relegationProbs && (
            <>
              <p className={`${styles.sectionLabel} ${styles.relegationLabel}`}>Relegation risk</p>
              {Object.entries(relegationProbs)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 3)
                .map(([team, prob]) => (
                  <div key={team} className={styles.simRow}>
                    <span className={styles.simTeam}>{team}</span>
                    <span className={styles.simPct}>{Math.round(prob * 100)}%</span>
                  </div>
                ))}
            </>
          )}
        </div>
      );
    }

    case 'LINEUP_PREDICTION': {
      const predictedXi = engineData.predicted_xi as PredictedPlayer[] | undefined;

      if (!predictedXi || predictedXi.length === 0) {
        return (
          <div className={styles.panel}>
            <p className={styles.muted}>Lineup data unavailable.</p>
          </div>
        );
      }

      return (
        <div className={styles.panel}>
          <p className={styles.sectionLabel}>Predicted XI</p>
          {predictedXi.map((p, i) => (
            <div key={i} className={styles.lineupRow}>
              <span className={styles.lineupPos}>{p.position}</span>
              <span className={styles.lineupName}>{p.name}</span>
              {p.start_probability !== undefined && (
                <span className={styles.lineupProb}>
                  {Math.round(p.start_probability * 100)}%
                </span>
              )}
            </div>
          ))}
        </div>
      );
    }

    case 'TACTICAL_QUERY': {
      const clusterLabel = engineData.cluster_label as string | undefined;
      const dominantZones = engineData.dominant_zones as number[] | undefined;
      const querySubType = engineData.query_type as string | undefined;
      const homeTeam = engineData.home_team as string | undefined;
      const awayTeam = engineData.away_team as string | undefined;

      return (
        <div className={styles.panel}>
          {querySubType === 'comparison' && homeTeam && awayTeam ? (
            <div className={styles.tacticalCompare}>
              <span className={styles.tacticalTeam}>{homeTeam}</span>
              <span className={styles.vs}>vs</span>
              <span className={styles.tacticalTeam}>{awayTeam}</span>
            </div>
          ) : null}
          {clusterLabel && <span className={styles.clusterBadge}>{clusterLabel}</span>}
          {dominantZones && dominantZones.length > 0 && (
            <div className={styles.zonesWrap}>
              <p className={styles.sectionLabel}>Dominant zones</p>
              <ol className={styles.zoneList}>
                {dominantZones.map((z) => (
                  <li key={z}>Zone {z}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      );
    }

    case 'AVAILABILITY_QUERY': {
      const players = engineData.players as Player[] | undefined;

      if (!players || players.length === 0) {
        return (
          <div className={styles.panel}>
            <p className={styles.muted}>No player data available.</p>
          </div>
        );
      }

      return (
        <div className={styles.panel}>
          <p className={styles.sectionLabel}>Availability risk</p>
          {players.map((p, i) => (
            <div key={i} className={styles.playerRow}>
              <span className={styles.playerName}>{p.name}</span>
              <span className={`${styles.riskBadge} ${getRiskClass(p.risk_label, p.risk_score)}`}>
                {p.risk_label ??
                  (p.risk_score !== undefined ? `${Math.round(p.risk_score * 100)}%` : 'Unknown')}
              </span>
            </div>
          ))}
        </div>
      );
    }

    case 'COMPOSITE_MATCH': {
      const match = engineData.match as Record<string, unknown> | undefined;
      const elo = engineData.elo as Record<string, unknown> | undefined;
      const availability = engineData.availability as Record<string, unknown> | undefined;
      const lineup = engineData.lineup as Record<string, unknown> | undefined;
      const matchProbabilities = match ? getProbabilities(match) : null;

      return (
        <div className={styles.panel}>
          <div className={styles.compositeGrid}>
            <div className={styles.compositeSection}>
              <p className={styles.sectionLabel}>Match prediction</p>
              {matchProbabilities ? (
                <ProbabilityBar probabilities={matchProbabilities} />
              ) : (
                <p className={styles.muted}>Unavailable</p>
              )}
            </div>
            <div className={styles.compositeSection}>
              <p className={styles.sectionLabel}>Elo ratings</p>
              {elo && Object.keys(elo).length > 0 ? (
                <StructuredResponseBlock
                  queryType="ELO_QUERY"
                  engineData={elo}
                  partial={false}
                  error={null}
                />
              ) : (
                <p className={styles.muted}>Unavailable</p>
              )}
            </div>
          </div>
          <div className={styles.compositeSummary}>
            <p className={styles.sectionLabel}>Availability</p>
            <p className={styles.muted}>
              {availability && Object.keys(availability).length > 0
                ? `${(availability.players as unknown[])?.length ?? 0} players assessed`
                : (engineData.availability_error as string) ?? 'Unavailable'}
            </p>
            <p className={styles.sectionLabel}>Lineup</p>
            <p className={styles.muted}>
              {lineup && Object.keys(lineup).length > 0
                ? `${(lineup.predicted_xi as unknown[])?.length ?? 0} players predicted`
                : (engineData.lineup_error as string) ?? 'Unavailable'}
            </p>
          </div>
        </div>
      );
    }

    case 'STAT_COMPARISON': {
      const homeTeam = engineData.home_team as string | undefined;
      const awayTeam = engineData.away_team as string | undefined;
      const stats = engineData.stats as Record<string, Record<string, number>> | undefined;

      if (!stats) return null;

      return (
        <div className={styles.panel}>
          <div className={styles.statHeader}>
            <span />
            <span className={styles.statTeamLabel}>{homeTeam}</span>
            <span className={styles.statTeamLabel}>{awayTeam}</span>
          </div>
          {Object.entries(stats).map(([statName, values]) => {
            const homeVal = homeTeam ? values[homeTeam] : undefined;
            const awayVal = awayTeam ? values[awayTeam] : undefined;
            const homeWins = homeVal !== undefined && awayVal !== undefined && homeVal > awayVal;
            const awayWins = awayVal !== undefined && homeVal !== undefined && awayVal > homeVal;

            return (
              <div key={statName} className={styles.statRow}>
                <span className={styles.statName}>{statName}</span>
                <span className={homeWins ? styles.statValueBold : styles.statValue}>
                  {homeVal?.toFixed(2) ?? '—'}
                </span>
                <span className={awayWins ? styles.statValueBold : styles.statValue}>
                  {awayVal?.toFixed(2) ?? '—'}
                </span>
              </div>
            );
          })}
        </div>
      );
    }

    case 'UNKNOWN': {
      const capabilities = engineData.capabilities as Record<string, Capability> | undefined;

      if (!capabilities) return null;

      return (
        <div className={styles.capabilitiesGrid}>
          {Object.entries(capabilities).map(([key, cap]) => (
            <button
              key={key}
              className={styles.capabilityCard}
              onClick={() => onExampleClick?.(cap.example)}
            >
              <span className={styles.capabilityDesc}>{cap.description}</span>
              <span className={styles.capabilityExample}>{cap.example}</span>
            </button>
          ))}
        </div>
      );
    }

    default:
      return null;
  }
}