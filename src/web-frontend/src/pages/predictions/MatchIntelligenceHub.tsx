import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { PREDICTION_LEAGUE_OPTIONS } from '../../utils/footballSeason';
import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import { SectionSkeleton } from '../../common/components/SectionSkeleton';
import { InlineRetry } from '../../common/components/InlineRetry';
import ProbabilityBar from '../../common/ProbabilityBar';
import ConfidenceBadge from '../../components/widgets/ConfidenceBadge';
import DegradedBanner from '../../components/widgets/DegradedBanner';
import NullStatePlaceholder from '../../components/widgets/NullStatePlaceholder';
import StrengthComparisonStrip from '../../components/widgets/StrengthComparisonStrip';
import { ScorelineGrid, TopScoresCard } from '../../components/widgets/ScorelineGrid';
import AvailabilityTimeline from '../../components/widgets/AvailabilityTimeline';
import PredictedXIBoard from '../../components/widgets/PredictedXIBoard';
import PredictionVsMarketCard from '../../components/widgets/PredictionVsMarketCard';
import {
  fetchMatchPredictionWidget,
  fetchScorelineWidget,
  fetchAvailabilityWidget,
  fetchLineupWidget,
} from '../../services/api/widgetApi';
import { getMatchLookupFixtures, getOddsFixtures, type MatchLookupFixture } from '../../services/api/predictionsApi';
import type {
  MatchPredictionWidgetPayload,
  ScorelineWidgetPayload,
  AvailabilityWidgetPayload,
  LineupWidgetPayload,
  WidgetFreshness,
} from '../../services/api/widgetApi';
import type { OddsConsensus } from '../../types/prediction';
import {
  getCurrentFootballSeason,
  getFootballSeasonForDate,
  liveCompetitionCodeToPredictionLeague,
  formatSeasonDisplay,
} from '../../utils/footballSeason';
import styles from './css/MatchIntelligenceHub.module.css';
import ZoneHeatmap from '../../components/widgets/ZoneHeatmap';
import StyleProfileCard from '../../components/widgets/StyleProfileCard';
import { fetchTacticalWidget } from '../../services/api/widgetApi';
import type { TacticalWidgetPayload } from '../../services/api/widgetApi';
import { Sidebar } from '../../components/Navigation/SideBar';
import { PredictionsNavbar } from '../../components/Navigation/predictionsNavbar';
import { SocialUserButtons } from '../../components/Social/SocialUserButtons';

const DEFAULT_LEAGUE = 'EPL';
const COVERAGE_NOTICE = 'Tactical analysis powered by StatsBomb Open Data. Coverage includes Premier League and La Liga teams.' as const;
const TACTICAL_LEAGUE_CODES = new Set(['LL', 'PD', 'LA_LIGA', 'LALIGA', 'ES', 'SPA', 'EPL', 'PL', 'PREMIER_LEAGUE', 'PREMIER LEAGUE']);

function normalizeTeamName(name: string): string {
  return name.normalize('NFD').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function isPastFixtureDate(dateStr: string): boolean {
  if (!dateStr) return false;
  const fixtureEndUtc = Date.parse(`${dateStr}T23:59:59Z`);
  if (Number.isNaN(fixtureEndUtc)) return false;
  return fixtureEndUtc < Date.now();
}

function hasTacticalCoverage(code: string): boolean {
  return TACTICAL_LEAGUE_CODES.has(code.toUpperCase().replace(/[^A-Z0-9]/g, '_'));
}

interface BlockState<T> {
  data: T | null;
  loading: boolean;
  error: boolean;
  retrying: boolean;
}

function initBlock<T>(): BlockState<T> {
  return { data: null, loading: true, error: false, retrying: false };
}

interface TopFactor {
  feature: string;
  contribution: number;
  description: string;
}

function ModelReasoningPanel({ factors }: { factors: TopFactor[] }) {
  const [open, setOpen] = useState(false);
  if (!factors || factors.length === 0) return null;
  return (
    <div className={styles.reasoningPanel}>
      <button className={styles.reasoningToggle} onClick={() => setOpen(v => !v)}>
        {open ? 'Hide reasoning' : 'Show reasoning'}
      </button>
      {open && (
        <div className={styles.reasoningList}>
          {factors.map((f, i) => (
            <div key={`${f.feature}-${i}`} className={styles.reasoningRow}>
              <span className={styles.reasoningDesc}>{f.description}</span>
              <span className={f.contribution >= 0 ? styles.contribPos : styles.contribNeg}>
                {f.contribution >= 0 ? '+' : ''}{f.contribution.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function BlockShell({
  title,
  children,
  loading,
  error,
  onRetry,
  retrying,
}: {
  title: string;
  children: React.ReactNode;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  retrying: boolean;
}) {
  return (
    <section className={styles.block}>
      <h2 className={styles.blockTitle}>{title}</h2>
      {loading && <SectionSkeleton rows={3} />}
      {!loading && error && (
        <InlineRetry message="Failed to load data." onRetry={onRetry} retrying={retrying} />
      )}
      {!loading && !error && children}
    </section>
  );
}

function TacticalBlock({ homeTeam, awayTeam }: { homeTeam: string; awayTeam: string }) {
  const [homePayload, setHomePayload] = useState<TacticalWidgetPayload | null>(null);
  const [awayPayload, setAwayPayload] = useState<TacticalWidgetPayload | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.allSettled([
      fetchTacticalWidget(homeTeam),
      fetchTacticalWidget(awayTeam),
    ]).then(([homeRes, awayRes]) => {
      if (cancelled) return;
      setHomePayload(homeRes.status === 'fulfilled' ? homeRes.value.data : null);
      setAwayPayload(awayRes.status === 'fulfilled' ? awayRes.value.data : null);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [homeTeam, awayTeam]);

  if (loading) return <SectionSkeleton rows={3} />;

  return (
    <div className={styles.squadColumns}>
      <div className={styles.squadColumn}>
        <StyleProfileCard styleCluster={homePayload?.data?.style_cluster ?? null} />
        <ZoneHeatmap zoneProfiles={homePayload?.data?.zone_profiles ?? null} team={homeTeam} />
      </div>
      <div className={styles.squadColumn}>
        <StyleProfileCard styleCluster={awayPayload?.data?.style_cluster ?? null} />
        <ZoneHeatmap zoneProfiles={awayPayload?.data?.zone_profiles ?? null} team={awayTeam} />
      </div>
    </div>
  );
}

export default function MatchIntelligenceHub() {
  const [searchParams] = useSearchParams();
  return <MatchIntelligenceContent key={searchParams.toString()} />;
}

function MatchIntelligenceContent() {
  const [searchParams, setSearchParams] = useSearchParams();
  const homeTeam = searchParams.get('home') ?? '';
  const awayTeam = searchParams.get('away') ?? '';
  const leagueCode = searchParams.get('league') ?? DEFAULT_LEAGUE;
  const fixtureDate = searchParams.get('date') ?? '';
  const season = searchParams.get('season') ?? getFootballSeasonForDate(fixtureDate, getCurrentFootballSeason());

  const [switcherLeague, setSwitcherLeague] = useState(liveCompetitionCodeToPredictionLeague(leagueCode) ?? leagueCode);
  const [switcherSeason, setSwitcherSeason] = useState(searchParams.get('season') ?? (fixtureDate ? season : '2025'));
  const [teamSearch, setTeamSearch] = useState('');
  const [switchFixtures, setSwitchFixtures] = useState<MatchLookupFixture[]>([]);
  const [switchLoading, setSwitchLoading] = useState(true);
  const [switchError, setSwitchError] = useState(false);
  const [switchAttempt, setSwitchAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setSwitchLoading(true);
    setSwitchError(false);
    setSwitchFixtures([]);
    getMatchLookupFixtures(switcherLeague, switcherSeason)
      .then(fixtures => { if (!cancelled) setSwitchFixtures(fixtures); })
      .catch(() => { if (!cancelled) setSwitchError(true); })
      .finally(() => { if (!cancelled) setSwitchLoading(false); });
    return () => { cancelled = true; };
  }, [switcherLeague, switcherSeason, switchAttempt]);

  function handleFixtureSwitch(fixture: MatchLookupFixture) {
    setSearchParams({
      home: fixture.home_team,
      away: fixture.away_team,
      league: fixture.league,
      season: fixture.season,
      date: fixture.date,
      source: 'lookup',
    });
  }

  const fixtureResolved = Boolean(homeTeam && awayTeam);
  const searchTerms = teamSearch.split(/\s+/).map(normalizeTeamName).filter(Boolean);
  const matchingFixtures = switchFixtures.filter(fixture => {
    const teams = normalizeTeamName(`${fixture.home_team} vs ${fixture.away_team}`);
    return searchTerms.every(term => teams.includes(term));
  });
  const latestSeason = Number(getCurrentFootballSeason());
  const seasons = Array.from({ length: latestSeason - 2014 + 1 }, (_, index) => String(latestSeason - index));
  const fixturePicker = (
    <section className={styles.fixtureSwitcher} aria-label="Match lookup controls">
      <label>
        League
        <select className={styles.switcherSelect} value={switcherLeague} onChange={event => setSwitcherLeague(event.target.value)}>
          {PREDICTION_LEAGUE_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <label>
        Season
        <select className={styles.switcherSelect} value={switcherSeason} onChange={event => setSwitcherSeason(event.target.value)}>
          {seasons.map(option => <option key={option} value={option}>{formatSeasonDisplay(option)}</option>)}
        </select>
      </label>
      <label>
        Search by team
        <input type="search" className={styles.switcherSelect} value={teamSearch} onChange={event => setTeamSearch(event.target.value)} />
      </label>
      <label>
        Fixture
        <select
          className={styles.switcherSelect}
          value=""
          disabled={switchLoading || matchingFixtures.length === 0}
          onChange={event => {
            if (!event.target.value) return;
            const fixture = matchingFixtures[Number(event.target.value)];
            if (fixture) handleFixtureSwitch(fixture);
          }}
        >
          <option value="">{switchLoading ? 'Loading fixtures…' : 'Select a fixture'}</option>
          {matchingFixtures.map((fixture, index) => (
            <option key={`${fixture.home_team}/${fixture.away_team}/${fixture.date}`} value={index}>
              {fixture.home_team} vs {fixture.away_team} — {fixture.date}
            </option>
          ))}
        </select>
      </label>
      {switchError && <InlineRetry message="Could not load fixtures." onRetry={() => setSwitchAttempt(attempt => attempt + 1)} />}
      {!switchLoading && !switchError && matchingFixtures.length === 0 && (
        <p role="status">{searchTerms.length ? 'No matches for that team search.' : 'No fixtures are available for this league and season.'}</p>
      )}
    </section>
  );

  const [matchPred, setMatchPred] = useState<BlockState<MatchPredictionWidgetPayload>>(initBlock());
  const [scoreline, setScoreline] = useState<BlockState<ScorelineWidgetPayload>>(initBlock());
  const [homeAvail, setHomeAvail] = useState<BlockState<AvailabilityWidgetPayload>>(initBlock());
  const [awayAvail, setAwayAvail] = useState<BlockState<AvailabilityWidgetPayload>>(initBlock());
  const [homeLineup, setHomeLineup] = useState<BlockState<LineupWidgetPayload>>(initBlock());
  const [awayLineup, setAwayLineup] = useState<BlockState<LineupWidgetPayload>>(initBlock());
  const [marketConsensus, setMarketConsensus] = useState<OddsConsensus | null>(null);
  const [marketFreshness, setMarketFreshness] = useState<WidgetFreshness | null>(null);
  const [marketLoading, setMarketLoading] = useState(true);
  const [marketError, setMarketError] = useState(false);
  const [marketRetrying, setMarketRetrying] = useState(false);

  const [showHomeXI, setShowHomeXI] = useState(false);
  const [showAwayXI, setShowAwayXI] = useState(false);
  const [scorelineExpanded, setScorelineExpanded] = useState(false);

  const loadMatchPred = useCallback(async function loadMatchPred(isRetry = false) {
    setMatchPred(prev => ({ ...prev, loading: !isRetry, retrying: isRetry, error: false }));
    try {
      const env = await fetchMatchPredictionWidget(homeTeam, awayTeam, leagueCode, season);
      setMatchPred({ data: env.data, loading: false, error: false, retrying: false });
    } catch {
      setMatchPred({ data: null, loading: false, error: true, retrying: false });
    }
  }, [homeTeam, awayTeam, leagueCode, season]);

  const loadScoreline = useCallback(async function loadScoreline(isRetry = false) {
    setScoreline(prev => ({ ...prev, loading: !isRetry, retrying: isRetry, error: false }));
    try {
      const env = await fetchScorelineWidget(homeTeam, awayTeam, leagueCode, season);
      setScoreline({ data: env.data, loading: false, error: false, retrying: false });
    } catch {
      setScoreline({ data: null, loading: false, error: true, retrying: false });
    }
  }, [homeTeam, awayTeam, leagueCode, season]);

  const loadMarket = useCallback(async function loadMarket(isRetry = false) {
    if (isRetry) setMarketRetrying(true);
    else setMarketLoading(true);
    setMarketError(false);
    try {
      const primaryView = isPastFixtureDate(fixtureDate) ? 'past' : 'future';
      const secondaryView = primaryView === 'past' ? 'future' : 'past';

      let envelope = await getOddsFixtures(leagueCode, primaryView, homeTeam, awayTeam);
      let fixtures = envelope.data?.fixtures ?? [];
      if (fixtures.length === 0) {
        envelope = await getOddsFixtures(leagueCode, secondaryView, homeTeam, awayTeam);
        fixtures = envelope.data?.fixtures ?? [];
      }

      const targetHome = normalizeTeamName(homeTeam);
      const targetAway = normalizeTeamName(awayTeam);
      const match = fixtures.find(f => {
        const fixtureHome = normalizeTeamName(f.home_team);
        const fixtureAway = normalizeTeamName(f.away_team);
        return fixtureHome === targetHome && fixtureAway === targetAway
          && (!fixtureDate || f.commence_time?.slice(0, 10) === fixtureDate);
      });
      setMarketConsensus(match?.consensus ?? null);
      if (envelope.freshness) {
        setMarketFreshness({
          ...(envelope.freshness as WidgetFreshness),
          cascade_degraded: false,
          cascade_reason: null,
        });
      }
    } catch {
      setMarketError(true);
    } finally {
      setMarketLoading(false);
      setMarketRetrying(false);
    }
  }, [homeTeam, awayTeam, leagueCode, fixtureDate]);

  const loadSquadBlock = useCallback(async function loadSquadBlock(isRetry = false) {
    if (!fixtureDate) {
      setHomeAvail({ data: null, loading: false, error: false, retrying: false });
      setAwayAvail({ data: null, loading: false, error: false, retrying: false });
      setHomeLineup({ data: null, loading: false, error: false, retrying: false });
      setAwayLineup({ data: null, loading: false, error: false, retrying: false });
      return;
    }
    const resetState = { loading: !isRetry, retrying: isRetry, error: false, data: null };
    setHomeAvail(prev => ({ ...prev, ...resetState }));
    setAwayAvail(prev => ({ ...prev, ...resetState }));
    setHomeLineup(prev => ({ ...prev, ...resetState }));
    setAwayLineup(prev => ({ ...prev, ...resetState }));

    const results = await Promise.allSettled([
      fetchAvailabilityWidget(homeTeam, fixtureDate, leagueCode, season),
      fetchAvailabilityWidget(awayTeam, fixtureDate, leagueCode, season),
      fetchLineupWidget(homeTeam, fixtureDate, leagueCode, season),
      fetchLineupWidget(awayTeam, fixtureDate, leagueCode, season),
    ]);

    const [ha, aa, hl, al] = results;
    setHomeAvail({
      data: ha.status === 'fulfilled' ? ha.value.data : null,
      loading: false,
      error: ha.status === 'rejected',
      retrying: false,
    });
    setAwayAvail({
      data: aa.status === 'fulfilled' ? aa.value.data : null,
      loading: false,
      error: aa.status === 'rejected',
      retrying: false,
    });
    setHomeLineup({
      data: hl.status === 'fulfilled' ? hl.value.data : null,
      loading: false,
      error: hl.status === 'rejected',
      retrying: false,
    });
    setAwayLineup({
      data: al.status === 'fulfilled' ? al.value.data : null,
      loading: false,
      error: al.status === 'rejected',
      retrying: false,
    });
  }, [homeTeam, awayTeam, leagueCode, season, fixtureDate]);

  useEffect(() => {
    if (!fixtureResolved) return;
    loadMatchPred();
    loadScoreline();
    loadMarket();
    loadSquadBlock();
  }, [fixtureResolved, loadMatchPred, loadScoreline, loadMarket, loadSquadBlock]);

  if (!fixtureResolved) {
    return (
      <div className={styles.page}>
        <div className={styles.Sidebar}>
          <Sidebar />
        </div>

        <div className={styles.base}>
          <header className={styles.Header}>
            <div className={styles.Left}>Match Lookup</div>
            <div className={styles.Middle}><PredictionsNavbar /></div>
            <div className={styles.Right}>
              <SocialUserButtons />
            </div>
          </header>

          <header className={styles.header}>
            <h1 className={styles.title}>Look up a match</h1>
            <p>Choose a league, season, and fixture to see the available analysis.</p>
            <Link to="/predictions/hub" className={styles.backLink}>Predictions home</Link>
          </header>
          {fixturePicker}
        </div>
      </div>
    );
  }

  const matchData = matchPred.data;
  const matchFreshness = matchData?.freshness ?? null;
  const modelProbs = matchData?.data
    ? { home: matchData.data.home_prob, draw: matchData.data.draw_prob, away: matchData.data.away_prob }
    : null;
  const topFactors = (matchData?.explanation?.top_factors ?? matchData?.data?.top_drivers ?? []) as TopFactor[];
  const scorelineData = scoreline.data?.data ?? null;
  const homeAvailability = homeAvail.data?.data ?? null;
  const awayAvailability = awayAvail.data?.data ?? null;
  const homePredictedLineup = homeLineup.data?.data ?? null;
  const awayPredictedLineup = awayLineup.data?.data ?? null;
  const tacticalAvailable = hasTacticalCoverage(leagueCode);

  return (
    <div className={styles.page}>
      <div className={styles.Sidebar}>
        <Sidebar />
      </div>

      <div className={styles.base}>
        <header className={styles.Header}>
          <div className={styles.Left}>Match Lookup</div>
          <div className={styles.Middle}><PredictionsNavbar /></div>
          <div className={styles.Right}>
            <SocialUserButtons />
          </div>
        </header>

      {fixturePicker}

      <header className={styles.header}>
        <h1 className={styles.title}>
          {homeTeam} vs {awayTeam}
        </h1>
        <span className={styles.leaguePill}>{leagueCode} · {formatSeasonDisplay(season)}{fixtureDate && ` · ${fixtureDate}`}</span>
        {isPastFixtureDate(fixtureDate) && (
          <p>Model estimates use available season data and may include matches played after this fixture.</p>
        )}
      </header>

      <div className={styles.blocks}>

        <BlockShell
          title="Strength Context"
          loading={matchPred.loading}
          error={matchPred.error}
          onRetry={() => loadMatchPred(true)}
          retrying={matchPred.retrying}
        >
          {matchFreshness?.cascade_degraded && matchFreshness.cascade_reason && (
            <DegradedBanner reason={matchFreshness.cascade_reason} cascade />
          )}
          <StrengthComparisonStrip
            homeTeam={homeTeam}
            awayTeam={awayTeam}
            homeElo={matchData?.data?.elo_home ?? null}
            awayElo={matchData?.data?.elo_away ?? null}
            freshness={matchFreshness ?? { source_fetched_at: null, snapshot_published_at: null, is_stale: false, is_degraded: false, stale_reason: null, sla_seconds: 0, cascade_degraded: false, cascade_reason: null }}
          />
        </BlockShell>

        <BlockShell
          title="Match Prediction"
          loading={matchPred.loading}
          error={matchPred.error}
          onRetry={() => loadMatchPred(true)}
          retrying={matchPred.retrying}
        >
          {modelProbs && (
            <>
              <ProbabilityBar
                probabilities={modelProbs}
                homeLabel={homeTeam}
                awayLabel={awayTeam}
              />
              <div className={styles.badgeRow}>
                <ConfidenceBadge
                  band={matchData!.confidence.band}
                  score={matchData!.confidence.score}
                />
                {matchFreshness && <FreshnessBadge freshness={matchFreshness} />}
              </div>
              <ModelReasoningPanel factors={topFactors} />
            </>
          )}
          {!modelProbs && !matchPred.loading && (
            <NullStatePlaceholder icon="chart" message="Prediction not available" />
          )}
        </BlockShell>

        <BlockShell
          title="Scoreline Outlook"
          loading={scoreline.loading}
          error={scoreline.error}
          onRetry={() => loadScoreline(true)}
          retrying={scoreline.retrying}
        >
          {scorelineData ? (
            <>
              {!scorelineExpanded && (
                <TopScoresCard topScorelines={scorelineData.top_3_scorelines} />
              )}
              {scorelineExpanded && (
                <ScorelineGrid
                  matrix={scorelineData.matrix}
                  homeTeam={homeTeam}
                  awayTeam={awayTeam}
                />
              )}
              <button
                className={styles.toggleBtn}
                onClick={() => setScorelineExpanded(v => !v)}
              >
                {scorelineExpanded ? 'Show top scorelines' : 'Show full grid'}
              </button>
              <p className={styles.goalsRow}>
                Over 2.5: {(scorelineData.over_under_probs.over_2_5 * 100).toFixed(1)}%
                {' · '}
                BTTS: {(scorelineData.btts_prob * 100).toFixed(1)}%
              </p>
            </>
          ) : (
            !scoreline.loading && !scoreline.error && (
              <NullStatePlaceholder icon="chart" message="Scoreline data not available" />
            )
          )}
        </BlockShell>

        <BlockShell
          title="Market vs Model"
          loading={marketLoading}
          error={marketError}
          onRetry={() => loadMarket(true)}
          retrying={marketRetrying}
        >
          {modelProbs ? (
            <PredictionVsMarketCard
              modelProbs={modelProbs}
              homeTeam={homeTeam}
              awayTeam={awayTeam}
              marketData={marketConsensus}
              freshness={marketFreshness ?? { source_fetched_at: null, snapshot_published_at: null, is_stale: false, is_degraded: false, stale_reason: null, sla_seconds: 0, cascade_degraded: false, cascade_reason: null }}
            />
          ) : (
            <NullStatePlaceholder icon="chart" message="Market comparison not available" />
          )}
        </BlockShell>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Squad Readiness</h2>
          <div className={styles.squadColumns}>
            <div className={styles.squadColumn}>
              <h3 className={styles.squadTeamTitle}>{homeTeam}</h3>
              {homeAvail.loading && <SectionSkeleton rows={4} />}
              {!homeAvail.loading && homeAvail.error && (
                <InlineRetry message="Failed to load." onRetry={() => loadSquadBlock(true)} retrying={homeAvail.retrying} />
              )}
              {!homeAvail.loading && !homeAvail.error && homeAvailability && (
                <AvailabilityTimeline availability={homeAvailability} />
              )}
              {!homeAvail.loading && !homeAvail.error && !homeAvailability && (
                <NullStatePlaceholder icon="shield" message="No availability data" />
              )}
              <button className={styles.toggleBtn} onClick={() => setShowHomeXI(v => !v)}>
                {showHomeXI ? 'Hide predicted XI' : 'Show predicted XI'}
              </button>
              {showHomeXI && homeLineup.loading && <SectionSkeleton rows={4} />}
              {showHomeXI && !homeLineup.loading && homePredictedLineup && (
                <PredictedXIBoard lineup={homePredictedLineup} />
              )}
              {showHomeXI && !homeLineup.loading && !homePredictedLineup && (
                <NullStatePlaceholder icon="shield" message="Lineup not available" />
              )}
            </div>
            <div className={styles.squadColumn}>
              <h3 className={styles.squadTeamTitle}>{awayTeam}</h3>
              {awayAvail.loading && <SectionSkeleton rows={4} />}
              {!awayAvail.loading && awayAvail.error && (
                <InlineRetry message="Failed to load." onRetry={() => loadSquadBlock(true)} retrying={awayAvail.retrying} />
              )}
              {!awayAvail.loading && !awayAvail.error && awayAvailability && (
                <AvailabilityTimeline availability={awayAvailability} />
              )}
              {!awayAvail.loading && !awayAvail.error && !awayAvailability && (
                <NullStatePlaceholder icon="shield" message="No availability data" />
              )}
              <button className={styles.toggleBtn} onClick={() => setShowAwayXI(v => !v)}>
                {showAwayXI ? 'Hide predicted XI' : 'Show predicted XI'}
              </button>
              {showAwayXI && awayLineup.loading && <SectionSkeleton rows={4} />}
              {showAwayXI && !awayLineup.loading && awayPredictedLineup && (
                <PredictedXIBoard lineup={awayPredictedLineup} />
              )}
              {showAwayXI && !awayLineup.loading && !awayPredictedLineup && (
                <NullStatePlaceholder icon="shield" message="Lineup not available" />
              )}
            </div>
          </div>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Tactical Context</h2>
          <p className={styles.coverageNotice}>{COVERAGE_NOTICE}</p>
          {tacticalAvailable ? (
            <TacticalBlock homeTeam={homeTeam} awayTeam={awayTeam} />
          ) : (
            <NullStatePlaceholder icon="chart" message="Tactical data not available for this league" />
          )}
        </section>

      </div>
      </div>
    </div>
  );
}
