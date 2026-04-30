import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ProbabilityBar from '../../common/ProbabilityBar';
import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import { fetchMatchPredictionWidget } from '../../services/api/widgetApi';
import type { MatchPredictionWidgetPayload } from '../../services/api/widgetApi';
import {
  getFootballSeasonForDate,
  liveCompetitionCodeToPredictionLeague,
} from '../../utils/footballSeason';
import ConfidenceBadge from './ConfidenceBadge';
import DegradedBanner from './DegradedBanner';
import UncertaintyNote from './UncertaintyNote';
import styles from './css/MatchPredictionCard.module.css';

const UPSET_THRESHOLD = 0.35;

interface MatchPredictionCardProps {
  homeTeam: string;
  awayTeam: string;
  kickoff: string;
  leagueCode: string;
  fixtureId: number | string;
}

function isUnderdog(payload: MatchPredictionWidgetPayload): boolean {
  if (!payload.data) return false;
  const { home_prob, away_prob } = payload.data;
  const max = Math.max(home_prob, away_prob);
  const min = Math.min(home_prob, away_prob);
  return max > UPSET_THRESHOLD && min > UPSET_THRESHOLD && min / max > 0.5;
}

export default function MatchPredictionCard({
  homeTeam,
  awayTeam,
  kickoff,
  leagueCode,
  fixtureId,
}: MatchPredictionCardProps) {
  const [payload, setPayload] = useState<MatchPredictionWidgetPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const predictionLeague = liveCompetitionCodeToPredictionLeague(leagueCode) ?? leagueCode;
    const season = getFootballSeasonForDate(kickoff);
    setLoading(true);
    setError(false);
    setPayload(null);
    fetchMatchPredictionWidget(homeTeam, awayTeam, predictionLeague, season)
      .then(envelope => {
        if (!cancelled && envelope.data) setPayload(envelope.data);
      })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [homeTeam, awayTeam, kickoff, leagueCode]);

  const kickoffStr = new Date(kickoff).toLocaleDateString(undefined, {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
  const predictionLeague = liveCompetitionCodeToPredictionLeague(leagueCode) ?? leagueCode;
  const season = getFootballSeasonForDate(kickoff);
  const kickoffDate = new Date(kickoff);
  const analysisParams = new URLSearchParams({
    home: homeTeam,
    away: awayTeam,
    league: predictionLeague,
    season,
    fixture_id: String(fixtureId),
  });
  if (!Number.isNaN(kickoffDate.getTime())) {
    analysisParams.set('date', kickoffDate.toISOString().slice(0, 10));
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.fixture}>
          <span className={styles.team}>{homeTeam}</span>
          <span className={styles.vs}>vs</span>
          <span className={styles.team}>{awayTeam}</span>
        </span>
        <span className={styles.kickoff}>{kickoffStr}</span>
      </div>

      {loading && <div className={styles.skeleton} />}

      {!loading && error && <UncertaintyNote message="Prediction unavailable" />}

      {!loading && !error && payload && (
        <>
          {payload.freshness.cascade_degraded && payload.freshness.cascade_reason && (
            <DegradedBanner reason={payload.freshness.cascade_reason} cascade />
          )}
          {payload.data && (
            <ProbabilityBar
              probabilities={{
                home: payload.data.home_prob,
                draw: payload.data.draw_prob,
                away: payload.data.away_prob,
              }}
              homeLabel={homeTeam}
              awayLabel={awayTeam}
            />
          )}
          <div className={styles.meta}>
            <ConfidenceBadge band={payload.confidence.band} score={payload.confidence.score} />
            <FreshnessBadge freshness={payload.freshness} />
            {isUnderdog(payload) && (
              <span className={styles.upsetBadge}>Upset watch</span>
            )}
          </div>
          <Link className={styles.analysisLink} to={`/match/lookup?${analysisParams.toString()}`}>
            View full analysis →
          </Link>
        </>
      )}
    </div>
  );
}
