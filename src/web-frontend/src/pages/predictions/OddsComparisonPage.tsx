import { Link } from "react-router-dom";
import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getOddsAccuracy,
  getOddsFixtures,
  getOddsTeams,
  predictMatch,
} from "../../services/api/predictionsApi";
import type { OddsAccuracyResponse } from "../../services/api/predictionsApi";
import { queryKeys } from "../../common/query/queryKeys";
import {
  STALE_TIME_STANDARD,
  STALE_TIME_SHORT,
} from "../../common/query/queryClient";
import type {
  OddsFixtureItem,
  PredictionResponse,
} from "../../types/prediction";
import { FreshnessBadge } from "../../common/components/FreshnessBadge";
import {
  formatSeasonDisplay,
  getCurrentFootballSeason,
  PREDICTION_LEAGUE_OPTIONS,
} from "../../utils/footballSeason";
import styles from "./css/OddsComparisonPage.module.css";
import { Sidebar } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import { PredictionsNavbar } from "../../components/Navigation/predictionsNavbar";

const LEAGUE_OPTIONS = PREDICTION_LEAGUE_OPTIONS;

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50];

const OUTCOME_LABEL: Record<string, string> = {
  H: "Home win",
  D: "Draw",
  A: "Away win",
};
const OUTCOME_TO_PROB: Record<string, "home" | "draw" | "away"> = {
  H: "home",
  D: "draw",
  A: "away",
};
const ODDS_REFRESH_MESSAGE =
  "Odds data not yet available — check back after 06:00 UTC";
const PREDICTION_PREFETCH_CONCURRENCY = 6;
const EMPTY_FIXTURES: OddsFixtureItem[] = [];

function fixturePredictionKey(
  fixture: OddsFixtureItem,
  league: string,
): string {
  return `${league}::${fixture.season}::${fixture.home_team}::${fixture.away_team}::${new Date(fixture.commence_time).toISOString().slice(0, 10)}`;
}

function fmt(n: number) {
  return (n * 100).toFixed(1) + "%";
}

function OddsCell({
  home,
  draw,
  away,
}: {
  home: number;
  draw: number;
  away: number;
}) {
  return (
    <span className={styles.oddsCell}>
      <span className={styles.oddsPill}>{home.toFixed(3)}</span>
      <span className={styles.oddsPill}>{draw.toFixed(3)}</span>
      <span className={styles.oddsPill}>{away.toFixed(3)}</span>
    </span>
  );
}

function AccuracyChart({ stats }: { stats: OddsAccuracyResponse }) {
  const { model_wins, market_wins, ties, total_evaluated, season } = stats;
  if (total_evaluated === 0) return null;

  const modelRate = model_wins / total_evaluated;
  const marketRate = market_wins / total_evaluated;
  const tiesRate = ties / total_evaluated;

  return (
    <div className={styles.chartSection}>
      <div className={styles.chartHeader}>
        <span className={styles.chartTitle}>
          Season accuracy breakdown — {formatSeasonDisplay(season)}
        </span>
        <span className={styles.chartSubtitle}>
          {total_evaluated} games evaluated
        </span>
      </div>
      <div className={styles.chartBars}>
        <div className={styles.chartRow}>
          <span className={styles.chartLabel}>Model</span>
          <div className={styles.barTrack}>
            <div
              className={`${styles.barFill} ${styles.barModel}`}
              style={{ width: `${modelRate * 100}%` }}
            />
          </div>
          <span className={styles.chartStat}>
            {(modelRate * 100).toFixed(1)}%
            <span className={styles.chartCount}>{model_wins} wins</span>
          </span>
        </div>
        <div className={styles.chartRow}>
          <span className={styles.chartLabel}>Market</span>
          <div className={styles.barTrack}>
            <div
              className={`${styles.barFill} ${styles.barMarket}`}
              style={{ width: `${marketRate * 100}%` }}
            />
          </div>
          <span className={styles.chartStat}>
            {(marketRate * 100).toFixed(1)}%
            <span className={styles.chartCount}>{market_wins} wins</span>
          </span>
        </div>
        {ties > 0 && (
          <div className={styles.chartRow}>
            <span className={styles.chartLabel}>Tied</span>
            <div className={styles.barTrack}>
              <div
                className={`${styles.barFill} ${styles.barTie}`}
                style={{ width: `${tiesRate * 100}%` }}
              />
            </div>
            <span className={styles.chartStat}>
              {(tiesRate * 100).toFixed(1)}%
              <span className={styles.chartCount}>{ties}</span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function FixtureRow({
  fixture,
  league,
  seasonFallback,
  showResultColumn,
  prefetchedPrediction,
}: {
  fixture: OddsFixtureItem;
  league: string;
  seasonFallback: string;
  showResultColumn: boolean;
  prefetchedPrediction: PredictionResponse | null;
}) {
  const [pred, setPred] = useState<PredictionResponse | null>(
    prefetchedPrediction,
  );
  const [predLoading, setPredLoading] = useState(false);
  const [predErr, setPredErr] = useState(false);

  useEffect(() => {
    if (prefetchedPrediction) {
      setPred(prefetchedPrediction);
      setPredErr(false);
    } else {
      setPred(null);
      setPredErr(false);
      setPredLoading(false);
    }
  }, [
    prefetchedPrediction,
    fixture.home_team,
    fixture.away_team,
    fixture.commence_time,
    league,
  ]);

  const load = useCallback(async () => {
    if (pred || predLoading) return;
    setPredLoading(true);
    setPredErr(false);
    try {
      const res = await predictMatch({
        home_team: fixture.home_team,
        away_team: fixture.away_team,
        league,
        season: fixture.season || seasonFallback,
      });
      setPred(res);
    } catch {
      setPredErr(true);
    } finally {
      setPredLoading(false);
    }
  }, [
    fixture.home_team,
    fixture.away_team,
    fixture.season,
    league,
    pred,
    predLoading,
    seasonFallback,
  ]);

  const dateStr = new Date(fixture.commence_time).toLocaleDateString(
    undefined,
    {
      day: "numeric",
      month: "short",
      year: "numeric",
    },
  );
  const outcome = fixture.result?.outcome;

  const outcomeKey = outcome ? OUTCOME_TO_PROB[outcome] : null;
  const modelProb = pred && outcomeKey ? pred.probabilities[outcomeKey] : null;
  const marketProb =
    fixture.consensus && outcomeKey
      ? fixture.consensus[
          `devig_${outcomeKey}` as "devig_home" | "devig_draw" | "devig_away"
        ]
      : null;

  let modelCorrect: boolean | null = null;
  let marketCorrect: boolean | null = null;
  if (modelProb !== null && marketProb !== null) {
    if (modelProb > marketProb) {
      modelCorrect = true;
      marketCorrect = false;
    } else if (marketProb > modelProb) {
      marketCorrect = true;
      modelCorrect = false;
    } else {
      modelCorrect = true;
      marketCorrect = true;
    }
  }

  return (
    <tr className={styles.row}>
      <td className={styles.td}>
        <span className={styles.fixture}>
          <span className={styles.team}>{fixture.home_team}</span>
          <span className={styles.vs}>vs</span>
          <span className={styles.team}>{fixture.away_team}</span>
        </span>
      </td>

      <td className={`${styles.td} ${styles.dateCell}`}>{dateStr}</td>

      <td className={styles.td}>
        {fixture.consensus ? (
          <OddsCell
            home={fixture.consensus.devig_home}
            draw={fixture.consensus.devig_draw}
            away={fixture.consensus.devig_away}
          />
        ) : (
          <span className={styles.noResult}>No odds data</span>
        )}
      </td>

      {showResultColumn && (
        <td className={styles.td}>
          {fixture.result ? (
            <span className={styles.result}>
              <span className={styles.score}>{fixture.result.score}</span>
              <span className={styles.outcomeLabel}>
                {outcome ? OUTCOME_LABEL[outcome] : ""}
              </span>
            </span>
          ) : (
            <span className={styles.noResult}>—</span>
          )}
        </td>
      )}

      <td className={styles.td}>
        {pred ? (
          <span className={styles.predResult}>
            <strong>{pred.prediction}</strong>
            <span className={styles.predProbs}>
              {fmt(pred.probabilities.home)} / {fmt(pred.probabilities.draw)} /{" "}
              {fmt(pred.probabilities.away)}
            </span>
          </span>
        ) : predLoading ? (
          <span className={styles.predLoading}>…</span>
        ) : predErr ? (
          <span className={styles.predError}>Failed</span>
        ) : (
          <button className={styles.predButton} onClick={load}>
            Get prediction
          </button>
        )}
      </td>

      <td className={styles.td}>
        <Link
          className={styles.analysisLink}
          to={`/match/lookup?home=${encodeURIComponent(fixture.home_team)}&away=${encodeURIComponent(fixture.away_team)}&league=${encodeURIComponent(league)}&season=${encodeURIComponent(fixture.season || seasonFallback)}&date=${encodeURIComponent(new Date(fixture.commence_time).toISOString().slice(0, 10))}`}
        >
          View analysis →
        </Link>
      </td>

      {showResultColumn && (
        <td className={styles.td}>
          {!fixture.result ? (
            <span className={styles.noResult}>—</span>
          ) : predLoading ? (
            <span className={styles.predLoading}>…</span>
          ) : (
            <span className={styles.accuracyCell}>
              <span
                className={
                  modelCorrect === true
                    ? styles.accuracyCorrect
                    : modelCorrect === false
                      ? styles.accuracyWrong
                      : styles.accuracyPending
                }
              >
                Model{" "}
                {modelCorrect === true
                  ? "✓"
                  : modelCorrect === false
                    ? "✗"
                    : "—"}
              </span>
              <span
                className={
                  marketCorrect === true
                    ? styles.accuracyCorrect
                    : marketCorrect === false
                      ? styles.accuracyWrong
                      : styles.accuracyPending
                }
              >
                Market{" "}
                {marketCorrect === true
                  ? "✓"
                  : marketCorrect === false
                    ? "✗"
                    : "—"}
              </span>
            </span>
          )}
        </td>
      )}
    </tr>
  );
}

export default function OddsComparisonPage() {
  const currentSeason = getCurrentFootballSeason();
  const [league, setLeague] = useState(LEAGUE_OPTIONS[0].value);
  const [view, setView] = useState<"past" | "future">("future");
  const [teamA, setTeamA] = useState("");
  const [teamB, setTeamB] = useState("");
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState(1);
  const [prefetchedPredictions, setPrefetchedPredictions] = useState<
    Record<string, PredictionResponse>
  >({});

  useEffect(() => {
    setPage(1);
  }, [league, view, teamA, teamB, pageSize]);

  const { data: teamsEnvelope } = useQuery({
    queryKey: queryKeys.predictions.odds.teams(league),
    queryFn: () => getOddsTeams(league),
    staleTime: STALE_TIME_STANDARD,
    enabled: Boolean(league),
  });
  const teams = teamsEnvelope?.data?.teams ?? [];

  const {
    data: fixturesEnvelope,
    isPending: fixturesLoading,
    isError: fixturesErrored,
  } = useQuery({
    queryKey: queryKeys.predictions.odds.fixtures(league, view, teamA, teamB),
    queryFn: () =>
      getOddsFixtures(league, view, teamA || undefined, teamB || undefined),
    staleTime: STALE_TIME_SHORT,
    enabled: Boolean(league),
  });

  const { data: accuracyEnvelope } = useQuery({
    queryKey: queryKeys.predictions.odds.accuracy(league, currentSeason),
    queryFn: () => getOddsAccuracy(league, currentSeason),
    staleTime: STALE_TIME_STANDARD,
    enabled: Boolean(league),
  });
  const accuracyStats = accuracyEnvelope?.data ?? null;

  const freshness = fixturesEnvelope?.freshness ?? null;
  const fixturesData = fixturesEnvelope?.data ?? null;
  const fixtures = fixturesData?.fixtures ?? EMPTY_FIXTURES;
  const fixturesSeason = fixturesData?.season || currentSeason;
  const seasonLabel = formatSeasonDisplay(fixturesSeason);
  const dataNull =
    !fixturesLoading &&
    !fixturesErrored &&
    fixturesEnvelope !== undefined &&
    fixturesEnvelope.data === null;

  const showResultColumn = view === "past";

  useEffect(() => {
    setPrefetchedPredictions({});

    if (view !== "past" || fixtures.length === 0) {
      return;
    }

    let cancelled = false;

    const toFetch = fixtures.filter((fixture) => fixture.result);
    const total = toFetch.length;
    if (total === 0) {
      return;
    }

    const run = async () => {
      let cursor = 0;
      const workerCount = Math.min(PREDICTION_PREFETCH_CONCURRENCY, total);

      const workers = Array.from({ length: workerCount }, async () => {
        while (true) {
          if (cancelled) return;
          const idx = cursor;
          cursor += 1;
          if (idx >= total) return;

          const fixture = toFetch[idx];
          try {
            const prediction = await predictMatch({
              home_team: fixture.home_team,
              away_team: fixture.away_team,
              league,
              season: fixture.season || fixturesSeason,
            });

            if (cancelled) return;
            const key = fixturePredictionKey(fixture, league);
            setPrefetchedPredictions((prev) => ({
              ...prev,
              [key]: prediction,
            }));
          } catch {
            // Keep preloading the remainder even when one fixture fails.
          }
        }
      });

      await Promise.all(workers);
    };

    run().catch(() => {
      if (cancelled) return;
    });

    return () => {
      cancelled = true;
    };
  }, [fixtures, fixturesSeason, league, view]);

  const totalPages = Math.max(1, Math.ceil(fixtures.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const paginatedFixtures = fixtures.slice(
    (safePage - 1) * pageSize,
    safePage * pageSize,
  );

  return (
    <div className={styles.page}>
      <div className={styles.Sidebar}>
        <Sidebar />
      </div>

      <div className={styles.base}>
        <header className={styles.Header}>
          <div className={styles.Left}>Odds Comparisson</div>
          <div className={styles.Middle}><PredictionsNavbar/></div>
          <div className={styles.Right}>
            <SocialUserButtons />
          </div>
        </header>
        
        <section className={styles.hero}>
          <h1 className={styles.title}>
            Odds &amp; Market Comparison — {seasonLabel}
          </h1>
          <p className={styles.subtitle}>
            Browse bookmaker odds and model predictions for{" "}
            {view === "past" ? "completed" : "upcoming"} fixtures.
          </p>
          <FreshnessBadge freshness={fixturesEnvelope?.freshness} />
        </section>

        <div className={styles.controls}>
          <label className={styles.controlField}>
            <span className={styles.controlLabel}>League</span>
            <select
              className={styles.select}
              value={league}
              onChange={(e) => {
                setLeague(e.target.value);
                setTeamA("");
                setTeamB("");
              }}
            >
              {LEAGUE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.controlField}>
            <span className={styles.controlLabel}>View</span>
            <select
              className={styles.select}
              value={view}
              onChange={(e) => setView(e.target.value as "past" | "future")}
            >
              <option value="future">Upcoming fixtures</option>
              <option value="past">Past fixtures</option>
            </select>
          </label>

          <label className={styles.controlField}>
            <span className={styles.controlLabel}>Team A</span>
            <select
              className={styles.select}
              value={teamA}
              onChange={(e) => setTeamA(e.target.value)}
            >
              <option value="">Any</option>
              {teams
                .filter((t) => t !== teamB)
                .map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
            </select>
          </label>

          <label className={styles.controlField}>
            <span className={styles.controlLabel}>Team B</span>
            <select
              className={styles.select}
              value={teamB}
              onChange={(e) => setTeamB(e.target.value)}
            >
              <option value="">Any</option>
              {teams
                .filter((t) => t !== teamA)
                .map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
            </select>
          </label>

          <label className={styles.controlField}>
            <span className={styles.controlLabel}>Per page</span>
            <select
              className={styles.select}
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        </div>

        {accuracyStats && (
          <div className={styles.accuracyBox}>
            <span className={styles.accuracyBoxLabel}>
              {formatSeasonDisplay(accuracyStats.season || fixturesSeason)}{" "}
              accuracy
            </span>
            <span className={styles.accuracyBoxStat}>
              <span className={styles.accuracyBoxValue}>
                {accuracyStats.model_wins}
              </span>
              <span className={styles.accuracyBoxName}>Model wins</span>
            </span>
            <span className={styles.accuracyBoxDivider}>vs</span>
            <span className={styles.accuracyBoxStat}>
              <span className={styles.accuracyBoxValue}>
                {accuracyStats.market_wins}
              </span>
              <span className={styles.accuracyBoxName}>Market wins</span>
            </span>
            {accuracyStats.ties > 0 && (
              <span className={styles.accuracyBoxStat}>
                <span className={styles.accuracyBoxValue}>
                  {accuracyStats.ties}
                </span>
                <span className={styles.accuracyBoxName}>Ties</span>
              </span>
            )}
            <span className={styles.accuracyBoxTotal}>
              of {accuracyStats.total_evaluated} games
            </span>
          </div>
        )}

        {fixturesLoading && (
          <div className={styles.stateCard}>
            <p className={styles.stateText}>Loading fixtures…</p>
          </div>
        )}

        {!fixturesLoading && fixturesErrored && (
          <div className={`${styles.stateCard} ${styles.errorState}`}>
            <p className={styles.stateText}>Failed to load fixtures.</p>
          </div>
        )}

        {!fixturesLoading && !fixturesErrored && dataNull && (
          <div className={styles.stateCard}>
            <p className={styles.stateText}>{ODDS_REFRESH_MESSAGE}</p>
          </div>
        )}

        {!fixturesLoading &&
          !fixturesErrored &&
          !dataNull &&
          fixtures.length === 0 && (
            <div className={styles.stateCard}>
              <p className={styles.stateText}>
                No fixtures with odds data found for this selection.
              </p>
            </div>
          )}

        {!fixturesLoading &&
          !fixturesErrored &&
          !dataNull &&
          fixtures.length > 0 && (
            <>
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.th}>
                        Fixture
                        {freshness && <FreshnessBadge freshness={freshness} />}
                      </th>
                      <th className={styles.th}>Date</th>
                      <th className={`${styles.th} ${styles.oddsHeader}`}>
                        Consensus odds (H / D / A)
                      </th>
                      {showResultColumn && (
                        <th className={styles.th}>Result</th>
                      )}
                      <th className={styles.th}>Model prediction</th>
                      <th className={styles.th}>Analysis</th>
                      {showResultColumn && (
                        <th className={styles.th}>Accuracy</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedFixtures.map((f) => (
                      <FixtureRow
                        key={fixturePredictionKey(f, league)}
                        fixture={f}
                        league={league}
                        seasonFallback={fixturesSeason}
                        showResultColumn={showResultColumn}
                        prefetchedPrediction={
                          prefetchedPredictions[
                            fixturePredictionKey(f, league)
                          ] ?? null
                        }
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              {accuracyStats && view === "past" && (
                <AccuracyChart stats={accuracyStats} />
              )}

              <div className={styles.pagination}>
                <button
                  className={styles.pageBtn}
                  disabled={safePage === 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  ← Prev
                </button>
                <span className={styles.pageInfo}>
                  Page {safePage} of {totalPages}
                  <span className={styles.pageCount}>
                    {" "}
                    — {fixtures.length} fixtures
                  </span>
                </span>
                <button
                  className={styles.pageBtn}
                  disabled={safePage === totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next →
                </button>
              </div>
            </>
          )}
      </div>
    </div>
  );
}
