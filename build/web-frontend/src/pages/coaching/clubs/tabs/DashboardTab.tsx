import { useEffect, useState } from 'react';
import { clubsApi } from '../../../../services/api';
import { playerdataApi } from '../../../../services/api/playerdataApi';
import { PlayerCarousel } from '../../../../components/Dashboard/PlayerCarousel';
import { StatsWidget } from '../../../../components/Dashboard/StatsWidget';
import { SessionWidget } from '../../../../components/Dashboard/SessionWidget';
import { ActivityFeedWidget } from '../../../../components/Dashboard/ActivityFeedWidget';
import { PlayerXgWidget } from '../../../../components/Clubs/PlayerXgWidget';
import type { ClubContext } from '../IndividualClubBase';
import type {
  PlayerCardData,
  SquadStats,
  SeasonStats,
  SessionEvent,
  ActivityEvent,
} from '../../../../components/Dashboard/types/DashboardTypes';
import type { ClubPlayer } from '../../../../types/clubPlayers';
import type { PlayerDataMetric, PlayerSeasonSummary } from '../../../../types/playerdata';
import type {
  ClubSeasonResult,
  ClubCalendarFeedItem,
  ClubPlayerManualStats,
} from '../../../../types/club';
import styles from './css/DashboardTab.module.css';
import { SectionSkeleton } from '../../../../common/components/SectionSkeleton';
import { InlineRetry } from '../../../../common/components/InlineRetry';

interface Props {
  ctx: ClubContext;
}

type UnderstatRecordShape = {
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
};

const toInt = (value: unknown): number => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
};

const extractUnderstatRecord = (value: unknown): UnderstatRecordShape | null => {
  if (!value || typeof value !== 'object') return null;

  const data = value as Record<string, unknown>;
  const candidate =
    data.summary && typeof data.summary === 'object'
      ? (data.summary as Record<string, unknown>)
      : data;

  const wins = toInt(candidate.wins);
  const draws = toInt(candidate.draws);
  const losses = toInt(candidate.losses);
  const goals_for = toInt(candidate.goals_for);
  const goals_against = toInt(candidate.goals_against);

  const hasAnyCore =
    'wins' in candidate ||
    'draws' in candidate ||
    'losses' in candidate ||
    'goals_for' in candidate ||
    'goals_against' in candidate;

  if (!hasAnyCore) return null;

  return { wins, draws, losses, goals_for, goals_against };
};

const mapPlayerToCardData = (p: ClubPlayer): PlayerCardData => ({
  id: p.id,
  display_name: p.display_name || `${p.first_name} ${p.last_name}`.trim(),
  username: String(p.id),
  position: p.primary_position || '—',
  jersey_number: p.squad_number ?? null,
  status: (p.availability_status as PlayerCardData['status']) ?? 'AV',
});

const deriveSquadStats = (players: ClubPlayer[]): SquadStats => {
  const total = players.length;
  const injured = players.filter((p) => p.availability_status === 'IN').length;
  const suspended = players.filter((p) => p.availability_status === 'SU').length;
  const inDoubt = players.filter((p) => p.availability_status === 'DO').length;
  const available = total - injured - suspended - inDoubt;
  return {
    avg_fitness: total > 0 ? Math.round((available / total) * 100) : 0,
    available,
    injured,
    suspended,
    in_doubt: inDoubt,
    total,
  };
};

const deriveSeasonStats = (results: ClubSeasonResult[]): SeasonStats => {
  // If we have a single record with 0 id, it's likely Understat enrichment data
  if (results.length === 1 && results[0].id === 0) {
    const stat = results[0];
    return {
      wins: (stat as any).wins || 0,
      draws: (stat as any).draws || 0,
      losses: (stat as any).losses || 0,
      goals_scored: stat.goals_for || 0,
      goals_conceded: stat.goals_against || 0,
    };
  }

  // Otherwise aggregate match results
  return results.reduce<SeasonStats>(
    (acc, r) => {
      acc.goals_scored += r.goals_for;
      acc.goals_conceded += r.goals_against;
      if (r.outcome === 'W') acc.wins += 1;
      else if (r.outcome === 'D') acc.draws += 1;
      else acc.losses += 1;
      return acc;
    },
    { wins: 0, draws: 0, losses: 0, goals_scored: 0, goals_conceded: 0 }
  );
};

const mapCalendarToSessions = (feed: ClubCalendarFeedItem[]): SessionEvent[] => {
  const eventSessions: SessionEvent[] = feed
    .filter((item) => item.item_type === 'event' && item.event)
    .map((item) => {
      const ev = item.event!;
      const type: SessionEvent['type'] =
        ev.event_type === 'training' ? 'training' : 'friendly';
      return {
        id: ev.id,
        type,
        title: ev.title,
        date: ev.start_datetime,
        duration_mins: 0,
        players_attended: null,
        total_players: 0,
      };
    });

  const fixtureSessions: SessionEvent[] = feed
    .filter((item) => item.item_type === 'fixture' && item.fixture)
    .map((item) => {
      const fx = item.fixture!;
      return {
        id: fx.id + 100_000,
        type: 'match' as SessionEvent['type'],
        title: fx.calendar_label,
        date: fx.match_datetime,
        duration_mins: 90,
        players_attended: null,
        total_players: 0,
      };
    });

  return [...eventSessions, ...fixtureSessions];
};

const buildActivityFeed = (
  players: ClubPlayer[],
  results: ClubSeasonResult[],
  feed: ClubCalendarFeedItem[]
): ActivityEvent[] => {
  const events: ActivityEvent[] = [];
  let id = 1;

  players
    .filter((p) => p.current_injury?.is_current)
    .forEach((p) => {
      const inj = p.current_injury!;
      events.push({
        id: id++,
        type: 'player_injured',
        title: `${p.display_name || p.first_name} injured`,
        detail: `${inj.injury_type_display} — ${inj.severity_display}${inj.estimated_return ? ` · est. return ${inj.estimated_return}` : ''}`,
        timestamp: inj.created_at,
      });
    });

  [...players]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 3)
    .forEach((p) => {
      events.push({
        id: id++,
        type: 'player_added',
        title: 'Player added to squad',
        detail: `${p.display_name || `${p.first_name} ${p.last_name}`.trim()} joined${p.primary_position ? ` — position: ${p.primary_position}` : ''}`,
        timestamp: p.created_at,
      });
    });

  results.slice(0, 3).forEach((r) => {
    events.push({
      id: id++,
      type: 'match_result',
      title: 'Match result recorded',
      detail: `vs ${r.opponent_name} — ${r.outcome === 'W' ? 'Won' : r.outcome === 'D' ? 'Drew' : 'Lost'} ${r.goals_for}-${r.goals_against}`,
      timestamp: r.created_at,
    });
  });

  feed
    .filter((item) => item.item_type === 'event' && item.event)
    .slice(0, 2)
    .forEach((item) => {
      const ev = item.event!;
      events.push({
        id: id++,
        type: 'session_logged',
        title: 'Session logged',
        detail: ev.title,
        timestamp: ev.created_at,
      });
    });

  return events
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 8);
};

const UNDERSTAT_PREFERRED_KEYS = new Set(['xg', 'npxg', 'xa']);

const mergePlayerSummaries = (
  understat: PlayerSeasonSummary | null,
  sofascore: PlayerSeasonSummary | null,
): PlayerSeasonSummary | null => {
  if (!understat && !sofascore) return null;
  const metricsMap = new Map<string, PlayerDataMetric>();
  (sofascore?.metrics ?? []).forEach((m) => metricsMap.set(m.key, m));
  (understat?.metrics ?? []).forEach((m) => {
    if (UNDERSTAT_PREFERRED_KEYS.has(m.key) || !metricsMap.has(m.key)) {
      metricsMap.set(m.key, m);
    }
  });
  return { ...(understat ?? sofascore!), metrics: Array.from(metricsMap.values()) };
};

const DashboardTab = ({ ctx }: Props) => {
  const { clubId } = ctx;

  const [players, setPlayers] = useState<ClubPlayer[]>([]);
  const [results, setResults] = useState<ClubSeasonResult[]>([]);
  const [calendarFeed, setCalendarFeed] = useState<ClubCalendarFeedItem[]>([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [selectedStats, setSelectedStats] = useState<ClubPlayerManualStats | null>(null);
  const [selectedExternalSummary, setSelectedExternalSummary] = useState<PlayerSeasonSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const load = async () => {
      setError(false);
      try {
        // Load all players (already unwrapped as array)
        const playersData = await clubsApi.listPlayers(clubId);
        setPlayers(playersData);

        // Try to get latest Understat data first, fallback to manual entries.
        let seasonData: ClubSeasonResult[] = [];
        try {
          const envelope = await clubsApi.getUnderstatSeasonSummary(clubId);
          const understatData =
            extractUnderstatRecord(envelope.data) ||
            extractUnderstatRecord(ctx.club.latest_understat_summary);

          if (understatData) {
            // Convert Understat enrichment to ClubSeasonResult format
            seasonData = [{
              id: 0,
              club_id: clubId,
              opponent_name: '',
              outcome: '',
              goals_for: understatData.goals_for,
              goals_against: understatData.goals_against,
              wins: understatData.wins,
              draws: understatData.draws,
              losses: understatData.losses,
              match_date: new Date().toISOString(),
              created_by: undefined,
              created_at: new Date().toISOString(),
            } as any];
          }
          if (seasonData.length === 0) {
            seasonData = await clubsApi.seasonResults.list(clubId);
          }
        } catch {
          // If the summary endpoint fails (permissions/shape/network), still
          // use club-level understat fallback before dropping to manual entries.
          const understatFallback = extractUnderstatRecord(ctx.club.latest_understat_summary);
          if (understatFallback) {
            seasonData = [{
              id: 0,
              club_id: clubId,
              opponent_name: '',
              outcome: '',
              goals_for: understatFallback.goals_for,
              goals_against: understatFallback.goals_against,
              wins: understatFallback.wins,
              draws: understatFallback.draws,
              losses: understatFallback.losses,
              match_date: new Date().toISOString(),
              created_by: undefined,
              created_at: new Date().toISOString(),
            } as any];
          } else {
            seasonData = await clubsApi.seasonResults.list(clubId);
          }
        }
        setResults(seasonData);

        // Load calendar feed
        const feedData = await clubsApi.listCalendarFeed(clubId, { limit: 50 });
        setCalendarFeed(feedData);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [clubId, retryKey, ctx.club.latest_understat_summary]);

  useEffect(() => {
    if (selectedPlayerId === null) {
      setSelectedStats(null);
      setSelectedExternalSummary(null);
      return;
    }
    let active = true;
    const load = async () => {
      try {
        const stats = await clubsApi.manualStats.list(clubId, selectedPlayerId);
        if (active) setSelectedStats(stats[0] ?? null);
      } catch {
        if (active) setSelectedStats(null);
      }

      const p = players.find((pl) => pl.id === selectedPlayerId) ?? null;
      const rawId = p?.canonical_player_id ?? p?.player_id ?? null;
      const canonicalId = typeof rawId === 'number' && rawId > 0 ? rawId : null;
      if (!canonicalId) {
        if (active) setSelectedExternalSummary(null);
        return;
      }
      const [uResult, ssResult] = await Promise.allSettled([
        playerdataApi.getPlayerSeasonSummary(canonicalId, { season: '2025', provider: 'understat' }),
        playerdataApi.getPlayerSeasonSummary(canonicalId, { season: '2025', provider: 'sofascore' }),
      ]);
      const merged = mergePlayerSummaries(
        uResult.status === 'fulfilled' ? uResult.value : null,
        ssResult.status === 'fulfilled' ? ssResult.value : null,
      );
      if (active) setSelectedExternalSummary(merged);
    };
    void load();
    return () => { active = false; };
  }, [selectedPlayerId, clubId, players]);

  const cardPlayers = players.map(mapPlayerToCardData);
  const squadStats = deriveSquadStats(players);
  const seasonStats: SeasonStats = deriveSeasonStats(results);

  const sessions = mapCalendarToSessions(calendarFeed);
  const activity = buildActivityFeed(players, results, calendarFeed);
  const selectedPlayer = players.find((p) => p.id === selectedPlayerId) ?? null;

  const handlePlayerSelect = (card: PlayerCardData) => {
    setSelectedPlayerId((prev) => (prev === card.id ? null : card.id));
  };

  if (loading) {
    return <SectionSkeleton rows={4} height="120px" gap="16px" />;
  }

  if (error) {
    return (
      <InlineRetry
        message="Failed to load dashboard"
        onRetry={() => setRetryKey((k) => k + 1)}
      />
    );
  }

  return (
    <div className={styles.dashboardContent}>
      <section className={styles.carouselContainer}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionLabel}>Team</span>
          <span className={styles.sectionMeta}>
            {squadStats.available}/{squadStats.total} available
          </span>
        </div>
        <PlayerCarousel
          players={cardPlayers}
          selectedId={selectedPlayerId}
          onPlayerSelect={handlePlayerSelect}
        />
      </section>

      <section className={styles.statsContainer}>
        <StatsWidget squad={squadStats} season={seasonStats} />
      </section>

      <div className={styles.grid}>
        <div className={styles.gridSchedule}>
          <SessionWidget sessions={sessions} />
        </div>
        <div className={styles.gridAnalytics}>
          <PlayerXgWidget player={selectedPlayer} manualStats={selectedStats} externalSummary={selectedExternalSummary} />
        </div>
        <div className={styles.gridActivity}>
          <ActivityFeedWidget events={activity} />
        </div>
      </div>
    </div>
  );
};

export default DashboardTab;