import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { TeamSwitcher } from '../../common/components/TeamSwitcher';
import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import { SectionSkeleton } from '../../common/components/SectionSkeleton';
import NullStatePlaceholder from '../../components/widgets/NullStatePlaceholder';
import AvailabilityTimeline from '../../components/widgets/AvailabilityTimeline';
import PredictedXIBoard from '../../components/widgets/PredictedXIBoard';
import {
  fetchAvailabilityWidget,
  fetchLineupWidget,
} from '../../services/api/widgetApi';
import type {
  AvailabilityWidgetPayload,
  LineupWidgetPayload,
} from '../../services/api/widgetApi';
import liveFootballApi from '../../services/api/livefootballApi';
import { parseSeasonStartYear } from '../../utils/footballSeason';
import styles from './css/SquadIntelligenceHub.module.css';
import { Sidebar } from '../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../components/Social/SocialUserButtons';
import { PredictionsNavbar } from '../../components/Navigation/predictionsNavbar';

const CONGESTION_THRESHOLD_DAYS = 4;
const NEXT_FIXTURES_COUNT = 5;
const ALL_COMPETITION_CODES = ['PL', 'PD', 'BL1', 'SA', 'FL1'] as const;

const NEXT_FIXTURES_PER_COMP = 60;
const COMP_CODE_TO_LEAGUE: Record<string, string> = {
  PL: 'EPL',
  PD: 'La_Liga',
  BL1: 'Bundesliga',
  SA: 'Serie_A',
  FL1: 'Ligue_1',
};

interface FixtureOption {
  opponent: string;
  date: string;
  league: string;
  season: string;
  isHome: boolean;
}

function daysBetween(a: string, b: string): number {
  const msPerDay = 86400000;
  return Math.abs(new Date(b).getTime() - new Date(a).getTime()) / msPerDay;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: 'short', day: 'numeric', month: 'short',
  });
}

// Strip common suffixes the live-football API appends that our data doesn't use.
const TEAM_SUFFIX_RE = /\s+(FC|CF|SC|AFC|United FC|City FC|F\.C\.)$/i;
function normaliseTeamName(name: string): string {
  return name.replace(TEAM_SUFFIX_RE, '').trim();
}

export default function SquadIntelligenceHub() {
  const { teamSlug = '' } = useParams<{ teamSlug: string }>();
  const teamName = decodeURIComponent(teamSlug);
  const navigate = useNavigate();

  const [fixtures, setFixtures] = useState<FixtureOption[]>([]);
  const [fixturesLoading, setFixturesLoading] = useState(true);
  const [selectedIdx, setSelectedIdx] = useState(0);

  const [availability, setAvailability] = useState<AvailabilityWidgetPayload | null>(null);
  const [availLoading, setAvailLoading] = useState(false);

  const [lineup, setLineup] = useState<LineupWidgetPayload | null>(null);
  const [lineupLoading, setLineupLoading] = useState(false);

  const [opponentLineup, setOpponentLineup] = useState<LineupWidgetPayload | null>(null);
  const [opponentLineupLoading, setOpponentLineupLoading] = useState(false);

  const [showXI, setShowXI] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFixturesLoading(true);

    liveFootballApi
      .getCompetitions()
      .then(async (competitions: Array<{ id: number; code: string; current_season_label?: string | null }>) => {
        const relevant = competitions.filter(c =>
          (ALL_COMPETITION_CODES as readonly string[]).includes(c.code)
        );
        const allFixtures: FixtureOption[] = [];

        for (const comp of relevant) {
          try {
            const res = await liveFootballApi.getCompetitionPreviousNextFixtures(comp.id, {
              next_limit: NEXT_FIXTURES_PER_COMP,
            });
            const rawFixtures = res.next ?? [];
            const matchesTeam = (f: any, side: 'home' | 'away'): boolean => {
                const obj = side === 'home' ? f.home_team : f.away_team;
                const flatName: string = side === 'home'
                  ? (f.home_team_name ?? '')
                  : (f.away_team_name ?? '');
                const candidates = [
                  obj?.name ?? '',
                  obj?.short_name ?? '',
                  flatName,
                ].filter(Boolean);
                if (candidates.some(n => n === teamName)) return true;
                // Case-insensitive prefix match: handles "Paris Saint-Germain" vs
                // "Paris Saint-Germain FC", and "Bayern Munich" vs "Bayern".
                const lowerTarget = teamName.toLowerCase();
                return candidates.some(n => {
                  const lower = n.toLowerCase();
                  return (
                    lower === lowerTarget ||
                    (lower.length >= 5 && lowerTarget.startsWith(lower)) ||
                    (lowerTarget.length >= 5 && lower.startsWith(lowerTarget))
                  );
                });
              };

            const teamFixtures = rawFixtures
              .filter((f: any) => {
                const fixtureStatus: string = f.status ?? '';
                if (fixtureStatus === 'FINISHED' || fixtureStatus === 'CANCELLED' || fixtureStatus === 'POSTPONED') return false;
                return matchesTeam(f, 'home') || matchesTeam(f, 'away');
              })
              .map((f: any) => {
                const isHome = matchesTeam(f, 'home');
                const home = f.home_team?.name ?? f.home_team_name ?? '';
                const away = f.away_team?.name ?? f.away_team_name ?? '';
                return {
                  opponent: isHome ? away : home,
                  date: (f.utc_date ?? f.kickoff_at ?? '').slice(0, 10),
                  league: comp.code,
                  season: parseSeasonStartYear(f.season_label ?? comp.current_season_label),
                  isHome,
                };
              });
            allFixtures.push(...teamFixtures);
          } catch {
            // continue to next competition
          }
        }

        allFixtures.sort((a, b) => a.date.localeCompare(b.date));

        if (!cancelled) {
          setFixtures(allFixtures.slice(0, NEXT_FIXTURES_COUNT));
          setSelectedIdx(0);
        }
      })
      .catch(() => { if (!cancelled) setFixtures([]); })
      .finally(() => { if (!cancelled) setFixturesLoading(false); });

    return () => { cancelled = true; };
  }, [teamSlug, teamName]);

  const selectedFixture = fixtures[selectedIdx] ?? null;

  useEffect(() => {
    if (!selectedFixture) return;
    let cancelled = false;

    setAvailLoading(true);
    setLineupLoading(true);
    setOpponentLineupLoading(true);
    setAvailability(null);
    setLineup(null);
    setOpponentLineup(null);

    const league = COMP_CODE_TO_LEAGUE[selectedFixture.league];

    fetchAvailabilityWidget(teamName, selectedFixture.date, league, selectedFixture.season)
      .then(env => { if (!cancelled) setAvailability(env.data); })
      .catch(() => { if (!cancelled) setAvailability(null); })
      .finally(() => { if (!cancelled) setAvailLoading(false); });

    fetchLineupWidget(teamName, selectedFixture.date, league, selectedFixture.season)
      .then(env => { if (!cancelled) setLineup(env.data); })
      .catch(() => { if (!cancelled) setLineup(null); })
      .finally(() => { if (!cancelled) setLineupLoading(false); });

    fetchLineupWidget(normaliseTeamName(selectedFixture.opponent), selectedFixture.date, league, selectedFixture.season)
      .then(env => { if (!cancelled) setOpponentLineup(env.data); })
      .catch(() => { if (!cancelled) setOpponentLineup(null); })
      .finally(() => { if (!cancelled) setOpponentLineupLoading(false); });

    return () => { cancelled = true; };
  }, [teamName, selectedFixture]);

  const availData = availability?.data ?? null;
  const lineupData = lineup?.data ?? null;
  const opponentLineupData = opponentLineup?.data ?? null;

  return (
    <div className={styles.page}>
      <div className={styles.Sidebar}>
        <Sidebar />
      </div>

      <div className={styles.base}>
        <header className={styles.Header}>
          <div className={styles.Left}>Odds Comparisson</div>
          <div className={styles.Middle}><PredictionsNavbar /></div>
          <div className={styles.Right}>
            <SocialUserButtons />
          </div>
        </header>

      <header className={styles.header}>
        <h1 className={styles.title}>{teamName}</h1>
        <p className={styles.subtitle}>Squad Intelligence</p>
      </header>

      <div className={styles.content}>
        <TeamSwitcher
          currentTeam={teamName}
          onSelect={team => navigate(`/squad/${encodeURIComponent(team)}`)}
        />
      </div>

      {fixturesLoading && <SectionSkeleton rows={2} />}

      {!fixturesLoading && fixtures.length === 0 && (
        <div className={styles.content}>
          <NullStatePlaceholder
            icon="chart"
            message="No upcoming fixtures found for this team"
          />
        </div>
      )}

      {!fixturesLoading && fixtures.length > 0 && (
        <div className={styles.content}>
          <div className={styles.fixtureSelector}>
            <label className={styles.selectorLabel} htmlFor="fixture-select">
              Select fixture
            </label>
            <select
              id="fixture-select"
              className={styles.select}
              value={selectedIdx}
              onChange={e => setSelectedIdx(Number(e.target.value))}
            >
              {fixtures.map((f, i) => (
                <option key={i} value={i}>
                  {f.isHome ? 'vs' : '@'} {f.opponent} — {formatDate(f.date)}
                </option>
              ))}
            </select>
          </div>

          {selectedFixture && (
            <>
              <section className={styles.block}>
                <div className={styles.blockHeader}>
                  <h2 className={styles.blockTitle}>Availability</h2>
                  {availability?.freshness && (
                    <FreshnessBadge freshness={availability.freshness} />
                  )}
                </div>
                {availLoading && <SectionSkeleton rows={5} />}
                {!availLoading && availData && (
                  <AvailabilityTimeline availability={availData} />
                )}
                {!availLoading && !availData && (
                  <NullStatePlaceholder icon="shield" message="No availability data" />
                )}
              </section>

              <section className={styles.block}>
                <div className={styles.blockHeader}>
                  <h2 className={styles.blockTitle}>Predicted XI</h2>
                  {lineup?.freshness && (
                    <FreshnessBadge freshness={lineup.freshness} />
                  )}
                </div>
                <button
                  className={styles.toggleBtn}
                  onClick={() => setShowXI(v => !v)}
                >
                  {showXI ? 'Hide XI' : 'Show predicted XI'}
                </button>
                {showXI && (
                  <div className={styles.xiMatchup}>
                    <div className={styles.xiTeam}>
                      <p className={styles.xiTeamName}>{teamName}</p>
                      {lineupLoading && <SectionSkeleton rows={4} />}
                      {!lineupLoading && lineupData && <PredictedXIBoard lineup={lineupData} />}
                      {!lineupLoading && !lineupData && (
                        <NullStatePlaceholder icon="shield" message="Lineup not available" />
                      )}
                    </div>
                    <div className={styles.xiTeam}>
                      <p className={styles.xiTeamName}>{selectedFixture.opponent}</p>
                      {opponentLineupLoading && <SectionSkeleton rows={4} />}
                      {!opponentLineupLoading && opponentLineupData && (
                        <PredictedXIBoard lineup={opponentLineupData} />
                      )}
                      {!opponentLineupLoading && !opponentLineupData && (
                        <NullStatePlaceholder icon="shield" message="Lineup not available" />
                      )}
                    </div>
                  </div>
                )}
              </section>

              <section className={styles.block}>
                <h2 className={styles.blockTitle}>Upcoming Schedule</h2>
                <div className={styles.scheduleList}>
                  {fixtures.map((f, i) => {
                    const prev = fixtures[i - 1];
                    const gap = prev ? daysBetween(prev.date, f.date) : null;
                    const isCongested = gap !== null && gap < CONGESTION_THRESHOLD_DAYS;
                    return (
                      <div
                        key={i}
                        className={`${styles.scheduleRow} ${i === selectedIdx ? styles.scheduleRowActive : ''}`}
                      >
                        <span className={styles.scheduleDate}>{formatDate(f.date)}</span>
                        <span className={styles.scheduleOpponent}>
                          {f.isHome ? 'vs' : '@'} {f.opponent}
                        </span>
                        <span className={styles.scheduleLeague}>{f.league}</span>
                        {isCongested && (
                          <span className={styles.congestionBadge}>High congestion</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            </>
          )}
        </div>
      )}
      </div>
    </div>
  );
}
