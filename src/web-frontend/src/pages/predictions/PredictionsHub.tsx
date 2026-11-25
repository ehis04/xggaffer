import { useEffect, useMemo, useState, type ReactElement } from "react";
import { useNavigate } from "react-router-dom";
import { getOddsFixtures } from "../../services/api/predictionsApi";
import type { OddsFixtureItem } from "../../types/prediction";
import {
  getCurrentFootballSeason,
  predictionLeagueToLiveCompetitionCode,
  PREDICTION_LEAGUE_OPTIONS,
} from "../../utils/footballSeason";
import styles from "./css/PredictionsHub.module.css";
import { Sidebar } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import { playerIcon, predictionsIcon, searchIcon } from "../coaching/CoachingBase";
import { PredictionsNavbar } from "../../components/Navigation/predictionsNavbar";

export const oddsIcon = (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    fill="currentColor"
    className="bi bi-bar-chart-fill"
    viewBox="0 0 16 16"
  >
    <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z" />
  </svg>
);

export const projectionIcon = (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    fill="currentColor"
    className="bi bi-graph-up-arrow"
    viewBox="0 0 16 16"
  >
    <path
      fillRule="evenodd"
      d="M0 0h1v15h15v1H0zm10 3.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-1 0V4.9l-3.613 4.417a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61L13.445 4H10.5a.5.5 0 0 1-.5-.5"
    />
  </svg>
);

export const tacticalIcon = (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    fill="currentColor"
    className="bi bi-bullseye"
    viewBox="0 0 16 16"
  >
    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16" />
    <path d="M8 13A5 5 0 1 1 8 3a5 5 0 0 1 0 10m0 1A6 6 0 1 0 8 2a6 6 0 0 0 0 12" />
    <path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6m0 1a4 4 0 1 0 0-8 4 4 0 0 0 0 8" />
    <path d="M9.5 8a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0" />
  </svg>
);

export const trustIcon = (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    fill="currentColor"
    className="bi bi-house-lock-fill"
    viewBox="0 0 16 16"
  >
    <path d="M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L8 2.207l6.646 6.647a.5.5 0 0 0 .708-.708L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293z" />
    <path d="m8 3.293 4.72 4.72a3 3 0 0 0-2.709 3.248A2 2 0 0 0 9 13v2H3.5A1.5 1.5 0 0 1 2 13.5V9.293z" />
    <path d="M13 9a2 2 0 0 0-2 2v1a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1v-1a2 2 0 0 0-2-2m0 1a1 1 0 0 1 1 1v1h-2v-1a1 1 0 0 1 1-1" />
  </svg>
);

export interface HubContext {
  fixture: FixtureExample | null;
  teamExamples: string[];
  trustLeague: string;
}

export interface Section {
  icon: ReactElement;
  title: string;
  description: string;
  label: string;
  path?: string;
  getPath?: (context: HubContext) => string;
}

const FALLBACK_TEAM_EXAMPLES = [
  "Arsenal",
  "Real Madrid",
  "Barcelona",
  "Liverpool",
  "Atlético Madrid",
] as const;

interface FixtureExample {
  home: string;
  away: string;
  league: string;
  date: string;
  season: string;
}

function randomFrom<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

const fixtureToExample = (fixture: OddsFixtureItem): FixtureExample => ({
  home: fixture.home_team,
  away: fixture.away_team,
  league: fixture.league,
  date: new Date(fixture.commence_time).toISOString().slice(0, 10),
  season: fixture.season || getCurrentFootballSeason(),
});

export const PRED_SECTIONS: Section[] = [
  {
    icon: predictionsIcon,
    title: "Match Predictions",
    description:
      "Run match outcome predictions powered by Elo ratings and historical data across top leagues.",
    label: "Open Predictions",
    path: "/predictions",
  },
  {
    icon: oddsIcon,
    title: "Odds Comparison",
    description:
      "Compare model probabilities with bookmaker odds to spot value and market discrepancies.",
    label: "Compare Odds",
    path: "/predictions/odds",
  },
  {
    icon: searchIcon,
    title: "Match Intelligence",
    description:
      "Look up pre-match intelligence for any fixture — form, availability, head-to-head, and xG context.",
    label: "Look Up Match",
    getPath: ({ fixture }) => {
      if (!fixture) return "/match/lookup";
      return `/match/lookup?home=${encodeURIComponent(fixture.home)}&away=${encodeURIComponent(fixture.away)}&league=${encodeURIComponent(fixture.league)}&season=${encodeURIComponent(fixture.season)}&date=${encodeURIComponent(fixture.date)}&source=odds`;
    },
  },
  {
    icon: projectionIcon,
    title: "Season Projection",
    description:
      "Explore projected league standings, title races, and relegation battles for the current season.",
    label: "View Projections",
    getPath: ({ fixture }) =>
      `/season/${predictionLeagueToLiveCompetitionCode(fixture?.league ?? "EPL")}`,
  },
  {
    icon: tacticalIcon,
    title: "Tactical Scouting",
    description:
      "Analyse a team's formation tendencies, pressing intensity, and in/out-of-possession shape.",
    label: "Scout a Team",
    getPath: ({ teamExamples }) => {
      const teams =
        teamExamples.length > 0 ? teamExamples : FALLBACK_TEAM_EXAMPLES;
      return `/tactics/${encodeURIComponent(randomFrom(teams))}?source=fixture`;
    },
  },
  {
    icon: playerIcon,
    title: "Squad Intelligence",
    description:
      "Deep-dive into squad composition, injury risk, and player availability for any team.",
    label: "View Squad",
    getPath: ({ teamExamples }) => {
      const teams =
        teamExamples.length > 0 ? teamExamples : FALLBACK_TEAM_EXAMPLES;
      return `/squad/${encodeURIComponent(randomFrom(teams))}?source=fixture`;
    },
  },
  {
    icon: trustIcon,
    title: "Model Trust Centre",
    description:
      "Review model accuracy, calibration bands, and biggest hits and misses over the season.",
    label: "Open Trust Centre",
    getPath: ({ trustLeague }) =>
      `/trust?league=${encodeURIComponent(trustLeague)}&source=odds`,
  },
];

// NOTE: Tactical Scouting (/tactics/:teamSlug) and Squad Intelligence (/squad/:teamSlug)
// require a team slug — access them via Match Intelligence where team context is established.

export default function PredictionsHub() {
  const navigate = useNavigate();
  const [fixtures, setFixtures] = useState<FixtureExample[]>([]);

  useEffect(() => {
    let cancelled = false;

    const loadFixtures = async () => {
      const results = await Promise.allSettled(
        PREDICTION_LEAGUE_OPTIONS.map((option) =>
          getOddsFixtures(option.value, "future"),
        ),
      );

      if (cancelled) return;

      const nextFixtures = results
        .flatMap((result) => {
          if (result.status !== "fulfilled") return [];
          return result.value.data?.fixtures ?? [];
        })
        .filter((fixture) => fixture.commence_time)
        .sort(
          (a, b) =>
            new Date(a.commence_time).getTime() -
            new Date(b.commence_time).getTime(),
        )
        .slice(0, 12)
        .map(fixtureToExample);

      if (nextFixtures.length > 0) {
        setFixtures(nextFixtures);
      }
    };

    void loadFixtures();
    return () => {
      cancelled = true;
    };
  }, []);

  const context = useMemo<HubContext>(() => {
    const fixture = fixtures.length > 0 ? randomFrom(fixtures) : null;
    const teamExamples = fixtures.flatMap((item) => [item.home, item.away]);
    return {
      fixture,
      teamExamples,
      trustLeague: fixture?.league ?? PREDICTION_LEAGUE_OPTIONS[0].value,
    };
  }, [fixtures]);

  const resolveSectionPath = (section: Section): string =>
    section.getPath
      ? section.getPath(context)
      : (section.path ?? "/predictions/hub");

  return (
    <div className={styles.container}>
      <div className={styles.Sidebar}>
        <Sidebar />
      </div>
      <div className={styles.base}>
        <header className={styles.Header}>
          <div className={styles.Left}>Predictions Home</div>
          <div className={styles.Middle}><PredictionsNavbar context={context} /></div>
          <div className={styles.Right}>
            <SocialUserButtons />
          </div>
        </header>

        <section className={styles.hero}>
          <div>
            <h1 className={styles.title}>Prediction & Intelligence</h1>
            <p className={styles.subtitle}>
              Model-powered match predictions, tactical scouting, squad
              analysis, and trust metrics — all in one place.
            </p>
          </div>
        </section>

        <svg className={styles.SvgDefs} aria-hidden="true" focusable="false">
          <defs>
            <linearGradient id="coachingBaseGradientColor">
              <stop offset="5%" stopColor="#49fcff" />
              <stop offset="95%" stopColor="#00b43f" />
            </linearGradient>
          </defs>
        </svg>

        <div className={styles.grid}>
          {PRED_SECTIONS.map((section) => (
            <button
              key={section.title}
              className={styles.card}
              type="button"
              onClick={() => navigate(resolveSectionPath(section))}
              aria-label={section.label}
            >
              <div className={styles.cardIcon}>{section.icon}</div>
              <h2 className={styles.cardTitle}>{section.title}</h2>
              <p className={styles.cardDescription}>{section.description}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
