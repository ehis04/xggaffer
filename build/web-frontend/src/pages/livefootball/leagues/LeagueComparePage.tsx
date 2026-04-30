import React, { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../common/query/queryKeys";
import { STALE_TIME_STANDARD } from "../../../common/query/queryClient";
import { buildLeagueProjectionParams } from "../../../services/api/livefootballApi";
import { Link, useSearchParams } from "react-router-dom";
import CommentaryPanel from "../../../components/livefootball/leagues/CommentaryPanel";
import ComparisonMetrics from "../../../components/livefootball/leagues/ComparisonMetrics";
import ComparisonTable from "../../../components/livefootball/leagues/ComparisonTable";
import LeagueSelector from "../../../components/livefootball/leagues/LeagueSelector";
import MatchweekSelector from "../../../components/livefootball/leagues/MatchweekSelector";
import SeasonSelector from "../../../components/livefootball/leagues/SeasonSelector";
import liveFootballApi from "../../../services/api/livefootballApi";
import type { LeagueMetaItem } from "../../../types/livefootball";
import styles from "../../../components/livefootball/leagues/css/LeagueComparePage.module.css";
import { Sidebar } from "../../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../../components/Social/SocialUserButtons";

type ProjectionMode = "current_expected" | "pre_season" | "as_of_matchweek";
type ProjectionWindow = "full_season" | "to_date";

const MODE_LABELS: Record<ProjectionMode, string> = {
  current_expected: "Current expected",
  pre_season: "Pre-season",
  as_of_matchweek: "As-of matchweek",
};

const MODE_ORDER: ProjectionMode[] = [
  "current_expected",
  "pre_season",
  "as_of_matchweek",
];
// Keep matchweek mode implemented but temporarily hidden from the UI until product sign-off.
const ENABLE_MATCHWEEK_UI = false;
type UnavailableMode = LeagueMetaItem["unavailable_modes"][number];

const LeagueComparePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const {
    data: metaEnvelope,
    isPending: metaLoading,
    isError: metaErrored,
  } = useQuery({
    queryKey: queryKeys.livefootball.leaguesMeta(),
    queryFn: () => liveFootballApi.getLeaguesMeta(),
    staleTime: STALE_TIME_STANDARD,
  });
  const meta = metaEnvelope?.data ?? null;

  const leagues = meta?.leagues ?? [];

  const selectedLeague = useMemo<LeagueMetaItem | null>(() => {
    if (leagues.length === 0) {
      return null;
    }

    const competitionParam = Number(searchParams.get("competition"));
    if (Number.isFinite(competitionParam)) {
      const match = leagues.find(
        (league: LeagueMetaItem) => league.id === competitionParam,
      );
      if (match) {
        return match;
      }
    }

    return leagues[0];
  }, [leagues, searchParams]);

  const selectedSeason = useMemo<string | null>(() => {
    if (!selectedLeague) {
      return null;
    }

    const seasonParam = searchParams.get("season");
    if (seasonParam && selectedLeague.available_seasons.includes(seasonParam)) {
      return seasonParam;
    }

    return selectedLeague.available_seasons[0] ?? null;
  }, [selectedLeague, searchParams]);

  const selectedProjectionWindow = useMemo<ProjectionWindow>(() => {
    const raw = searchParams.get("projection_window");
    return raw === "to_date" ? "to_date" : "full_season";
  }, [searchParams]);

  const isCurrentSeasonSelected = useMemo<boolean>(() => {
    if (!selectedLeague || !selectedSeason) {
      return false;
    }

    return selectedSeason === selectedLeague.current_season_label;
  }, [selectedLeague, selectedSeason]);

  const selectedMode = useMemo<ProjectionMode | null>(() => {
    if (!selectedLeague || !selectedSeason) {
      return null;
    }

    const unavailableMap = new Map(
      selectedLeague.unavailable_modes.map((item: UnavailableMode) => [
        item.mode,
        item.reason,
      ]),
    );

    const supported = MODE_ORDER.filter((mode) => {
      if (!ENABLE_MATCHWEEK_UI && mode === "as_of_matchweek") {
        return false;
      }

      if (!selectedLeague.supported_modes.includes(mode)) {
        return false;
      }

      if (unavailableMap.has(mode)) {
        return false;
      }

      return true;
    });

    if (supported.length === 0) {
      return null;
    }

    const modeParam = searchParams.get("mode") as ProjectionMode | null;
    if (modeParam && supported.includes(modeParam)) {
      return modeParam;
    }

    if (supported.includes("current_expected")) {
      return "current_expected";
    }

    return supported[0];
  }, [selectedLeague, selectedSeason, searchParams]);

  const selectedMatchweek = useMemo<number | null>(() => {
    if (!ENABLE_MATCHWEEK_UI || selectedMode !== "as_of_matchweek") {
      return null;
    }

    const raw = searchParams.get("matchweek");
    if (!raw) {
      return null;
    }

    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }, [searchParams, selectedMode]);

  useEffect(() => {
    if (!selectedLeague || !selectedSeason || !selectedMode) {
      return;
    }

    const currentCompetition = searchParams.get("competition");
    const currentSeason = searchParams.get("season");
    const currentMode = searchParams.get("mode");
    const expectedMatchweek =
      ENABLE_MATCHWEEK_UI && selectedMode === "as_of_matchweek"
        ? selectedMatchweek
          ? String(selectedMatchweek)
          : null
        : null;
    const expectedProjectionWindow =
      selectedMode === "pre_season" && isCurrentSeasonSelected
        ? selectedProjectionWindow
        : null;

    if (
      currentCompetition === String(selectedLeague.id) &&
      currentSeason === selectedSeason &&
      currentMode === selectedMode &&
      searchParams.get("matchweek") === expectedMatchweek &&
      searchParams.get("projection_window") === expectedProjectionWindow
    ) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("competition", String(selectedLeague.id));
    nextParams.set("season", selectedSeason);
    nextParams.set("mode", selectedMode);

    if (ENABLE_MATCHWEEK_UI && selectedMode === "as_of_matchweek") {
      if (selectedMatchweek) {
        nextParams.set("matchweek", String(selectedMatchweek));
      } else {
        nextParams.delete("matchweek");
      }
    } else {
      nextParams.delete("matchweek");
    }

    if (selectedMode === "pre_season" && isCurrentSeasonSelected) {
      nextParams.set("projection_window", selectedProjectionWindow);
    } else {
      nextParams.delete("projection_window");
    }

    setSearchParams(nextParams, { replace: true });
  }, [
    searchParams,
    selectedLeague,
    selectedSeason,
    selectedMode,
    selectedMatchweek,
    selectedProjectionWindow,
    isCurrentSeasonSelected,
    setSearchParams,
  ]);

  const handleLeagueChange = (competitionId: number): void => {
    const nextLeague = leagues.find(
      (league: LeagueMetaItem) => league.id === competitionId,
    );
    const nextSeason = nextLeague?.available_seasons[0] ?? "";
    const supportedModes = MODE_ORDER.filter((mode) => {
      if (!ENABLE_MATCHWEEK_UI && mode === "as_of_matchweek") {
        return false;
      }

      if (!(nextLeague?.supported_modes ?? []).includes(mode)) {
        return false;
      }

      return true;
    });

    const nextMode = supportedModes.includes("current_expected")
      ? "current_expected"
      : (supportedModes[0] ?? "");

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("competition", String(competitionId));

    if (nextSeason) {
      nextParams.set("season", nextSeason);
    } else {
      nextParams.delete("season");
    }

    if (nextMode) {
      nextParams.set("mode", nextMode);
    } else {
      nextParams.delete("mode");
    }

    nextParams.delete("matchweek");

    if (
      nextMode === "pre_season" &&
      nextSeason === nextLeague?.current_season_label
    ) {
      nextParams.set("projection_window", "full_season");
    } else {
      nextParams.delete("projection_window");
    }

    setSearchParams(nextParams);
  };

  const handleMatchweekChange = (matchweek: number): void => {
    if (!ENABLE_MATCHWEEK_UI) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    if (selectedMode === "as_of_matchweek") {
      nextParams.set("matchweek", String(matchweek));
      setSearchParams(nextParams);
    }
  };

  const handleSeasonChange = (season: string): void => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("season", season);
    setSearchParams(nextParams);
  };

  const handleModeChange = (mode: ProjectionMode): void => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("mode", mode);

    nextParams.delete("matchweek");

    if (mode === "pre_season" && isCurrentSeasonSelected) {
      if (!nextParams.get("projection_window")) {
        nextParams.set("projection_window", "full_season");
      }
    } else {
      nextParams.delete("projection_window");
    }

    setSearchParams(nextParams);
  };

  const handleProjectionWindowChange = (
    projectionWindow: ProjectionWindow,
  ): void => {
    const nextParams = new URLSearchParams(searchParams);
    if (selectedMode === "pre_season" && isCurrentSeasonSelected) {
      nextParams.set("projection_window", projectionWindow);
      setSearchParams(nextParams);
    }
  };

  const unavailableModeReasons = useMemo(() => {
    return new Map(
      (selectedLeague?.unavailable_modes ?? []).map((item: UnavailableMode) => [
        item.mode,
        item.reason,
      ]),
    );
  }, [selectedLeague]);

  const filtersReady = Boolean(
    selectedLeague && selectedSeason && selectedMode,
  );

  const comparisonParams = useMemo(
    () => ({
      season: selectedSeason ?? undefined,
      mode: selectedMode ?? undefined,
      matchweek:
        ENABLE_MATCHWEEK_UI && selectedMode === "as_of_matchweek"
          ? (selectedMatchweek ?? undefined)
          : undefined,
      projection_window:
        selectedMode === "pre_season" && isCurrentSeasonSelected
          ? selectedProjectionWindow
          : undefined,
    }),
    [
      selectedSeason,
      selectedMode,
      selectedMatchweek,
      selectedProjectionWindow,
      isCurrentSeasonSelected,
    ],
  );

  const builtParams = buildLeagueProjectionParams(comparisonParams);

  const {
    data: comparisonEnvelope,
    isPending: comparisonLoading,
    isError: comparisonErrored,
  } = useQuery({
    queryKey: queryKeys.livefootball.compare(
      selectedLeague?.id ?? 0,
      builtParams ?? {},
    ),
    queryFn: () =>
      liveFootballApi.getLeagueComparison(selectedLeague!.id, comparisonParams),
    enabled: Boolean(selectedLeague && selectedSeason && selectedMode),
    staleTime: STALE_TIME_STANDARD,
  });
  const comparison = comparisonEnvelope?.data ?? null;

  return (
    <div className={styles.page}>
      <div className={styles.Sidebar}>
        <Sidebar />
      </div>

      <div className={styles.main}>
        <header className={styles.Header}>
          <div className={styles.Left}>Leagues</div>
          <div className={styles.Middle} />
          <div className={styles.Right}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles.Body}>
          <div className={styles.header}>
            <div className={styles.titleBlock}>
              <h1 className={styles.title}>League comparison</h1>
              <p className={styles.subtitle}>
                Compare actual standings against the model's expected table and
                inspect the key deltas.
              </p>
            </div>

            <div className={styles.actions}>
              <Link
                to={
                  selectedLeague && selectedSeason
                    ? `/livefootball/leagues?competition=${selectedLeague.id}&season=${selectedSeason}`
                    : "/livefootball/leagues"
                }
                className={styles.secondaryLink}
              >
                Back to leagues
              </Link>

              <Link
                to={
                  selectedLeague && selectedSeason
                    ? `/livefootball/leagues/custom?competition=${selectedLeague.id}&season=${selectedSeason}&mode=${selectedMode ?? "current_expected"}${
                        selectedMode === "pre_season" && isCurrentSeasonSelected
                          ? `&projection_window=${selectedProjectionWindow}`
                          : ""
                      }`
                    : "/livefootball/leagues/custom"
                }
                className={styles.secondaryLink}
              >
                Saved scenarios
              </Link>
            </div>
          </div>

          <section className={styles.filtersCard}>
            <div className={styles.filtersRow}>
              <LeagueSelector
                leagues={leagues}
                value={selectedLeague?.id ?? null}
                onChange={handleLeagueChange}
                disabled={metaLoading || leagues.length === 0}
              />

              <SeasonSelector
                seasons={selectedLeague?.available_seasons ?? []}
                value={selectedSeason}
                onChange={handleSeasonChange}
                disabled={metaLoading || !selectedLeague}
              />
            </div>

            <div className={styles.modeBlock}>
              <span className={styles.modeLabel}>Prediction mode</span>

              <div className={styles.modeButtons}>
                {MODE_ORDER.filter(
                  (mode) => ENABLE_MATCHWEEK_UI || mode !== "as_of_matchweek",
                ).map((mode) => {
                  const isSupported =
                    selectedLeague?.supported_modes.includes(mode) ?? false;
                  const reason = unavailableModeReasons.get(mode);
                  const disabled = !isSupported || Boolean(reason);

                  return (
                    <button
                      key={mode}
                      type="button"
                      className={`${styles.modeButton} ${selectedMode === mode ? styles.modeButtonActive : ""}`}
                      onClick={() => handleModeChange(mode)}
                      disabled={disabled}
                      title={
                        reason ||
                        (disabled
                          ? "This mode is unavailable for this league."
                          : "")
                      }
                    >
                      {MODE_LABELS[mode]}
                    </button>
                  );
                })}
              </div>

              {selectedMode === "pre_season" && isCurrentSeasonSelected ? (
                <div className={styles.projectionWindowRow}>
                  <button
                    type="button"
                    className={`${styles.modeButton} ${selectedProjectionWindow === "to_date" ? styles.modeButtonActive : ""}`}
                    onClick={() => handleProjectionWindowChange("to_date")}
                  >
                    Up to current date
                  </button>
                  <button
                    type="button"
                    className={`${styles.modeButton} ${selectedProjectionWindow === "full_season" ? styles.modeButtonActive : ""}`}
                    onClick={() => handleProjectionWindowChange("full_season")}
                  >
                    Full season
                  </button>
                </div>
              ) : null}

              {/* Temporarily disabled in UI: keep for quick restoration when the flow is fixed. */}
              {ENABLE_MATCHWEEK_UI && selectedMode === "as_of_matchweek" ? (
                <MatchweekSelector
                  value={selectedMatchweek ?? 1}
                  maxMatchweek={
                    comparison?.metadata.actual_matchday ??
                    comparison?.metadata.total_matchweeks ??
                    null
                  }
                  onChange={handleMatchweekChange}
                  disabled={comparisonLoading || !selectedLeague}
                />
              ) : null}
            </div>
          </section>

          {metaLoading ? (
            <section className={styles.stateCard}>
              <h2 className={styles.stateTitle}>Loading comparison</h2>
              <p className={styles.stateText}>
                Fetching leagues and available seasons.
              </p>
            </section>
          ) : null}

          {!metaLoading && metaErrored ? (
            <section className={styles.stateCard}>
              <h2 className={styles.stateTitle}>Comparison unavailable</h2>
              <p className={styles.stateText}>
                Failed to load league metadata.
              </p>
            </section>
          ) : null}

          {!metaLoading && !metaErrored && !filtersReady ? (
            <section className={styles.stateCard}>
              <h2 className={styles.stateTitle}>
                No comparison options available
              </h2>
              <p className={styles.stateText}>
                No supported league, season, and mode combination is currently
                available.
              </p>
            </section>
          ) : null}

          {!metaLoading && !metaErrored && filtersReady ? (
            <>
              {comparisonLoading ? (
                <section className={styles.stateCard}>
                  <h2 className={styles.stateTitle}>
                    Loading model comparison
                  </h2>
                  <p className={styles.stateText}>
                    Fetching actual and expected tables.
                  </p>
                </section>
              ) : null}

              {!comparisonLoading && comparisonErrored ? (
                <section className={styles.stateCard}>
                  <h2 className={styles.stateTitle}>
                    Could not load comparison
                  </h2>
                  <p className={styles.stateText}>
                    Could not load comparison data.
                  </p>
                </section>
              ) : null}

              {!comparisonLoading && !comparisonErrored && comparison ? (
                <>
                  <ComparisonTable
                    actualRows={comparison.actual_table}
                    expectedRows={comparison.expected_table}
                    mode={comparison.mode}
                    metadata={comparison.metadata}
                  />

                  <ComparisonMetrics
                    deltas={comparison.deltas}
                    comparisonMetrics={comparison.comparison_metrics}
                  />

                  <CommentaryPanel commentary={comparison.commentary} />
                </>
              ) : null}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default LeagueComparePage;
