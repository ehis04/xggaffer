import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import { SectionSkeleton } from '../../common/components/SectionSkeleton';
import { InlineRetry } from '../../common/components/InlineRetry';
import DegradedBanner from '../../components/widgets/DegradedBanner';
import NullStatePlaceholder from '../../components/widgets/NullStatePlaceholder';
import SimulatedLeagueTable from '../../components/widgets/SimulatedLeagueTable';
import PositionProbabilityMatrix from '../../components/widgets/PositionProbabilityMatrix';
import ProjectedPointsBandChart from '../../components/widgets/ProjectedPointsBandChart';
import WhatIfPanel from '../../components/widgets/WhatIfPanel';
import { fetchProjectedTableWidget } from '../../services/api/widgetApi';
import type {
  ProjectedTableWidgetPayload,
  TeamProjection,
  WhatIfAdjustment,
} from '../../services/api/widgetApi';
import liveFootballApi from '../../services/api/livefootballApi';
import { WHATIF_WIN_POINTS, WHATIF_DRAW_POINTS, WHATIF_LOSS_POINTS } from '../../components/widgets/WhatIfPanel';
import styles from './css/SeasonProjectionCentre.module.css';

const VALID_LEAGUE_CODES = ['PL', 'PD', 'BL1', 'SA', 'FL1'] as const;
type LeagueCode = typeof VALID_LEAGUE_CODES[number];

const LEAGUE_LABELS: Record<string, string> = {
  PL: 'Premier League',
  PD: 'La Liga',
  BL1: 'Bundesliga',
  SA: 'Serie A',
  FL1: 'Ligue 1',
};

const DEFAULT_VIEW = 'table' as const;
const VIEWS = ['table', 'matrix', 'chart'] as const;
type View = typeof VIEWS[number];

interface Fixture {
  home_team: string;
  away_team: string;
  fixture_id: string;
}

function applyAdjustments(
  original: TeamProjection[],
  adjustments: WhatIfAdjustment[],
): TeamProjection[] {
  const copy = original.map(t => ({ ...t }));
  for (const adj of adjustments) {
    if (!adj.selected_outcome) continue;
    const home = copy.find(t => t.team_name === adj.home_team);
    const away = copy.find(t => t.team_name === adj.away_team);
    if (!home || !away) continue;
    if (adj.selected_outcome === 'home') {
      home.projected_points_median += WHATIF_WIN_POINTS;
      away.projected_points_median += WHATIF_LOSS_POINTS;
    } else if (adj.selected_outcome === 'draw') {
      home.projected_points_median += WHATIF_DRAW_POINTS;
      away.projected_points_median += WHATIF_DRAW_POINTS;
    } else {
      away.projected_points_median += WHATIF_WIN_POINTS;
      home.projected_points_median += WHATIF_LOSS_POINTS;
    }
  }
  copy.sort((a, b) => b.projected_points_median - a.projected_points_median);
  copy.forEach((t, i) => { t.expected_position = i + 1; });
  return copy;
}

function adjustedTeamNames(adjustments: WhatIfAdjustment[]): Set<string> {
  const names = new Set<string>();
  for (const adj of adjustments) {
    if (adj.selected_outcome) {
      names.add(adj.home_team);
      names.add(adj.away_team);
    }
  }
  return names;
}

export default function SeasonProjectionCentre() {
  const { leagueCode = 'PL' } = useParams<{ leagueCode: string }>();
  const navigate = useNavigate();

  const [view, setView] = useState<View>(DEFAULT_VIEW);
  const [payload, setPayload] = useState<ProjectedTableWidgetPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState(false);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [adjustedTeams, setAdjustedTeams] = useState<TeamProjection[] | null>(null);
  const [whatIfAdjustments, setWhatIfAdjustments] = useState<WhatIfAdjustment[]>([]);

  function resetWhatIf() {
    setAdjustedTeams(null);
    setWhatIfAdjustments([]);
  }

  async function fetchData(isRetry = false) {
    if (isRetry) setRetrying(true);
    else setLoading(true);
    setError(false);

    try {
      const envelope = await fetchProjectedTableWidget(leagueCode);
      setPayload(envelope.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
      setRetrying(false);
    }
  }

  useEffect(() => {
    resetWhatIf();
    setView(DEFAULT_VIEW);
    fetchData();
  }, [leagueCode]);

  useEffect(() => {
    let cancelled = false;
    liveFootballApi
      .getCompetitions()
      .then(competitions => {
        const comp = (competitions as Array<{ id: number; code: string }>)
          .find(c => c.code === leagueCode);
        if (!comp) return null;
        return liveFootballApi.getCompetitionFixtures(comp.id, { status: 'SCHEDULED', limit: 10 });
      })
      .then(res => {
        if (cancelled || !res) return;
        const resAny = res as unknown as { fixtures?: unknown; items?: unknown };
        const rawFixtures = Array.isArray(resAny.fixtures)
          ? resAny.fixtures
          : Array.isArray(resAny.items)
            ? resAny.items
            : [];

        const shaped: Fixture[] = rawFixtures.slice(0, 10).map((f: any) => ({
          home_team: f.home_team?.name ?? f.home_team_name ?? '',
          away_team: f.away_team?.name ?? f.away_team_name ?? '',
          fixture_id: String(f.id),
        }));
        if (!cancelled) setFixtures(shaped);
      })
      .catch(() => { if (!cancelled) setFixtures([]); });
    return () => { cancelled = true; };
  }, [leagueCode]);

  function handleAdjustment(adjustments: WhatIfAdjustment[]) {
    setWhatIfAdjustments(adjustments);
    const originalTeams = payload?.data?.teams;
    if (!originalTeams) return;
    const hasAny = adjustments.some(a => a.selected_outcome !== null);
    setAdjustedTeams(hasAny ? applyAdjustments(originalTeams, adjustments) : null);
  }

  const isValidLeague = VALID_LEAGUE_CODES.includes(leagueCode as LeagueCode);
  const teams = adjustedTeams ?? payload?.data?.teams ?? [];
  const originalTeams = payload?.data?.teams ?? [];
  const seasonLabel = (payload?.summary?.season_label as string) ?? '';
  const freshness = payload?.freshness;
  const adjustedNames = adjustedTeamNames(whatIfAdjustments);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Season Projection Centre</h1>
      </header>

      <div className={styles.leagueTabBar}>
        {VALID_LEAGUE_CODES.map(code => (
          <button
            key={code}
            className={`${styles.leagueTab} ${leagueCode === code ? styles.leagueTabActive : ''}`}
            onClick={() => navigate(`/season/${code}`)}
          >
            {LEAGUE_LABELS[code]}
          </button>
        ))}
      </div>

      {!isValidLeague && (
        <NullStatePlaceholder
          icon="chart"
          message="Invalid league code. Select a league above."
        />
      )}

      {isValidLeague && loading && <SectionSkeleton rows={6} />}

      {isValidLeague && !loading && error && (
        <InlineRetry
          message="Failed to load projection data."
          onRetry={() => fetchData(true)}
          retrying={retrying}
        />
      )}

      {isValidLeague && !loading && !error && !payload?.data && (
        <NullStatePlaceholder
          icon="chart"
          message="Season projection not yet available for this league"
        />
      )}

      {isValidLeague && !loading && !error && payload?.data && (
        <div className={styles.content}>
          <div className={styles.contentHeader}>
            <h2 className={styles.contentTitle}>
              {LEAGUE_LABELS[leagueCode]} — Season {seasonLabel} Projection
            </h2>
            {freshness && <FreshnessBadge freshness={freshness} />}
          </div>

          {freshness?.cascade_degraded && freshness.cascade_reason && (
            <DegradedBanner reason={freshness.cascade_reason} cascade />
          )}

          <div className={styles.viewToggleBar}>
            {VIEWS.map(v => (
              <button
                key={v}
                className={`${styles.viewToggleBtn} ${view === v ? styles.viewToggleBtnActive : ''}`}
                onClick={() => setView(v)}
              >
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>

          <div className={styles.viewContainer}>
            {view === 'table' && freshness && (
              <SimulatedLeagueTable
                teams={teams}
                leagueCode={leagueCode}
                freshness={freshness}
                adjustedTeamNames={adjustedNames}
              />
            )}
            {view === 'matrix' && (
              <PositionProbabilityMatrix teams={originalTeams} />
            )}
            {view === 'chart' && (
              <ProjectedPointsBandChart teams={teams} />
            )}
          </div>

          <WhatIfPanel
            teams={originalTeams}
            fixtures={fixtures}
            onAdjustment={handleAdjustment}
          />

          <p className={styles.seasonScopeNotice}>
            Projections based on season {seasonLabel} data only.
          </p>
        </div>
      )}
    </div>
  );
}