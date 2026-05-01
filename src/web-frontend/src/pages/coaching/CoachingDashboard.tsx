import { PlayerCarousel } from "../../components/Dashboard/PlayerCarousel";
import { Sidebar } from "../../components/Navigation/SideBar";
import { useState } from "react";
import type {
  PlayerCardData,
  SquadStats,
  SeasonStats,
  SessionEvent,
  PlayerAnalyticsData,
  ActivityEvent,
} from "../../components/Dashboard/types/DashboardTypes";
import { StatsWidget } from "../../components/Dashboard/StatsWidget";
import { SessionWidget } from "../../components/Dashboard/SessionWidget";
import { PlayerAnalyticsWidget } from "../../components/Dashboard/PlayerAnalyticsWidget";
import { ActivityFeedWidget } from "../../components/Dashboard/ActivityFeedWidget";
import "./css/CoachingDashboard.css";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import { CoachingNavBar } from "../../components/Navigation/CoachingNavBar";

const MOCK_PLAYERS: PlayerCardData[] = [
  {
    id: 1,
    display_name: "Sean Murphy",
    username: "smurphy",
    position: "GK",
    jersey_number: 1,
    status: "AV",
  },
  {
    id: 2,
    display_name: "Ryan Collins",
    username: "rcollins",
    position: "RB",
    jersey_number: 2,
    status: "AV",
  },
  {
    id: 3,
    display_name: "Cian Doyle",
    username: "cdoyle",
    position: "CB",
    jersey_number: 5,
    status: "AV",
  },
  {
    id: 4,
    display_name: "Fionn Walsh",
    username: "fwalsh",
    position: "CB",
    jersey_number: 6,
    status: "DO",
  },
  {
    id: 5,
    display_name: "Darragh Byrne",
    username: "dbyrne",
    position: "LB",
    jersey_number: 3,
    status: "IN",
  },
  {
    id: 6,
    display_name: "Mark Gallagher",
    username: "mgallagher",
    position: "CM",
    jersey_number: 8,
    status: "AV",
  },
  {
    id: 7,
    display_name: "Pádraic Lawlor",
    username: "plawlor",
    position: "CDM",
    jersey_number: 4,
    status: "AV",
  },
  {
    id: 8,
    display_name: "Aoife O'Brien",
    username: "aobrien",
    position: "CAM",
    jersey_number: 10,
    status: "AV",
  },
  {
    id: 9,
    display_name: "James Burke",
    username: "jburke",
    position: "RW",
    jersey_number: 7,
    status: "AV",
  },
  {
    id: 10,
    display_name: "Killian Nolan",
    username: "knolan",
    position: "ST",
    jersey_number: 9,
    status: "SU",
  },
  {
    id: 11,
    display_name: "Liam Ryan",
    username: "lryan",
    position: "LW",
    jersey_number: 11,
    status: "AV",
  },
];

const MOCK_SQUAD_STATS: SquadStats = {
  avg_fitness: 84,
  available: 16,
  injured: 2,
  suspended: 0,
  in_doubt: 1,
  total: 18,
};

const MOCK_SEASON_STATS: SeasonStats = {
  wins: 9,
  draws: 3,
  losses: 4,
  goals_scored: 28,
  goals_conceded: 18,
};

const MOCK_SESSIONS: SessionEvent[] = [
  {
    id: 1,
    type: "training",
    title: "Pressing drills",
    date: "2026-03-16T10:00:00",
    duration_mins: 90,
    players_attended: null,
    total_players: 18,
  },
  {
    id: 2,
    type: "match",
    title: "vs Drogheda United",
    date: "2026-03-18T19:45:00",
    duration_mins: 105,
    players_attended: null,
    total_players: 18,
  },
  {
    id: 3,
    type: "training",
    title: "Set piece prep",
    date: "2026-03-20T10:00:00",
    duration_mins: 75,
    players_attended: null,
    total_players: 18,
  },
  {
    id: 4,
    type: "rest",
    title: "Recovery day",
    date: "2026-03-19T00:00:00",
    duration_mins: 0,
    players_attended: null,
    total_players: 18,
  },
  {
    id: 5,
    type: "friendly",
    title: "vs Shelbourne U21",
    date: "2026-03-31T16:00:00",
    duration_mins: 90,
    players_attended: null,
    total_players: 18,
  },
  {
    id: 6,
    type: "training",
    title: "Finishing & crossing",
    date: "2026-03-31T16:00:00",
    duration_mins: 60,
    players_attended: 15,
    total_players: 18,
  },
];

const MOCK_ANALYTICS: Record<number, PlayerAnalyticsData> = {
  1: {
    id: 1,
    display_name: "Sean Murphy",
    position: "GK",
    attributes: {
      pace: 54,
      passing: 61,
      stamina: 88,
      shooting: 22,
      defending: 78,
      dribbling: 45,
      physicality: 80,
      fitness: 92,
    },
  },
  2: {
    id: 2,
    display_name: "Ryan Collins",
    position: "RB",
    attributes: {
      pace: 80,
      passing: 74,
      stamina: 76,
      shooting: 55,
      defending: 79,
      dribbling: 70,
      physicality: 75,
      fitness: 78,
    },
  },
  3: {
    id: 3,
    display_name: "Cian Doyle",
    position: "CB",
    attributes: {
      pace: 66,
      passing: 70,
      stamina: 84,
      shooting: 40,
      defending: 87,
      dribbling: 52,
      physicality: 86,
      fitness: 85,
    },
  },
  4: {
    id: 4,
    display_name: "Fionn Walsh",
    position: "CB",
    attributes: {
      pace: 68,
      passing: 72,
      stamina: 87,
      shooting: 38,
      defending: 89,
      dribbling: 50,
      physicality: 88,
      fitness: 88,
    },
  },
  5: {
    id: 5,
    display_name: "Darragh Byrne",
    position: "LB",
    attributes: {
      pace: 78,
      passing: 68,
      stamina: 80,
      shooting: 50,
      defending: 75,
      dribbling: 68,
      physicality: 72,
      fitness: 20,
    },
  },
  6: {
    id: 6,
    display_name: "Mark Gallagher",
    position: "CM",
    attributes: {
      pace: 88,
      passing: 72,
      stamina: 80,
      shooting: 70,
      defending: 60,
      dribbling: 78,
      physicality: 74,
      fitness: 95,
    },
  },
  7: {
    id: 7,
    display_name: "Pádraic Lawlor",
    position: "CDM",
    attributes: {
      pace: 70,
      passing: 82,
      stamina: 85,
      shooting: 55,
      defending: 83,
      dribbling: 65,
      physicality: 82,
      fitness: 80,
    },
  },
  8: {
    id: 8,
    display_name: "Aoife O'Brien",
    position: "CAM",
    attributes: {
      pace: 83,
      passing: 88,
      stamina: 71,
      shooting: 75,
      defending: 48,
      dribbling: 85,
      physicality: 60,
      fitness: 72,
    },
  },
  9: {
    id: 9,
    display_name: "James Burke",
    position: "RW",
    attributes: {
      pace: 91,
      passing: 68,
      stamina: 88,
      shooting: 78,
      defending: 42,
      dribbling: 87,
      physicality: 65,
      fitness: 90,
    },
  },
  10: {
    id: 10,
    display_name: "Killian Nolan",
    position: "ST",
    attributes: {
      pace: 86,
      passing: 65,
      stamina: 82,
      shooting: 89,
      defending: 35,
      dribbling: 80,
      physicality: 78,
      fitness: 83,
    },
  },
  11: {
    id: 11,
    display_name: "Liam Ryan",
    position: "LW",
    attributes: {
      pace: 90,
      passing: 71,
      stamina: 86,
      shooting: 75,
      defending: 40,
      dribbling: 88,
      physicality: 63,
      fitness: 87,
    },
  },
};

const MOCK_ACTIVITY: ActivityEvent[] = [
  {
    id: 1,
    type: "session_logged",
    title: "Session logged",
    detail: "Pressing drills — 90 min, 15 players attended",
    timestamp: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
  },
  {
    id: 2,
    type: "player_injured",
    title: "Darragh Byrne injured",
    detail: "Hamstring strain — estimated 2 weeks out",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
  },
  {
    id: 3,
    type: "formation_updated",
    title: "Formation updated",
    detail: "4-3-3 → 4-2-3-1 saved for next match",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
  },
  {
    id: 4,
    type: "match_result",
    title: "Match result recorded",
    detail: "vs Drogheda United — Won 2-1",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 50).toISOString(),
  },
  {
    id: 5,
    type: "player_added",
    title: "Player added to squad",
    detail: "Ciarán Flood joined — position: LB",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
  },
  {
    id: 6,
    type: "player_recovered",
    title: "Fionn Walsh recovered",
    detail: "Cleared to train — available for selection",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 98).toISOString(),
  },
];

export const CoachingDashboard = () => {
  const [selectedPlayer, setSelectedPlayer] = useState<number | null>(null);
  function handlePlayerSelect(player: PlayerCardData) {
    setSelectedPlayer((prev) => (prev === player.id ? null : player.id));
  }
  const selectedAnalytics = selectedPlayer
    ? (MOCK_ANALYTICS[selectedPlayer] ?? null)
    : null;
  return (
    <div className="coaching-dashboard-container">
      <div className="sidebar-section">
        <Sidebar />
      </div>
      <div className="coaching-dashboard">
        <header className="coaching-dashboard-header">
          <div className="coaching-dashboard-left">Coaching Dashboard</div>
          <div className="coaching-dashboard-middle"><CoachingNavBar /></div>
          <div className="coaching-dashboard-right">
            <SocialUserButtons />
          </div>
        </header>

        <main className="coaching-dashboard-content">
          <section className="player-carousel-container">
            <div className="player-carousel-header">
              <span className="section-label">Team</span>
              <button className="section-link">See all</button>
            </div>
            <PlayerCarousel
              players={MOCK_PLAYERS}
              selectedId={selectedPlayer}
              onPlayerSelect={handlePlayerSelect}
            />
          </section>

          <section className="player-stats-container">
            <StatsWidget squad={MOCK_SQUAD_STATS} season={MOCK_SEASON_STATS} />
          </section>

          <div className="coaching-dashboard-grid">
            <div className="coaching-dashboard-grid-schedule">
              <SessionWidget sessions={MOCK_SESSIONS} />
            </div>
            <div className="coaching-dashboard-grid-analytics">
              <PlayerAnalyticsWidget player={selectedAnalytics} />
            </div>
            <div className="coaching-dashboard-grid-activity">
              <ActivityFeedWidget events={MOCK_ACTIVITY} />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
