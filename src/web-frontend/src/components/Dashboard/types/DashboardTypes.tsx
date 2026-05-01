export interface PlayerCardData {
  id: number;
  display_name: string;
  username: string;
  position: string;
  jersey_number: number | null;
  status: "AV" | "IN" | "SU" | "DO";
}

export interface PlayerCarouselProps {
  players: PlayerCardData[];
  selectedId?: number | null;
  onPlayerSelect?: (player: PlayerCardData) => void;
}

export interface SquadStats {
  avg_fitness: number;
  available: number;
  injured: number;
  suspended: number;
  in_doubt: number;
  total: number;
}

export interface SeasonStats {
  wins: number;
  draws: number;
  losses: number;
  goals_scored: number;
  goals_conceded: number;
}

export interface StatsWidgetProps {
  squad: SquadStats;
  season: SeasonStats;
}

export interface StatCardProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaPositive?: boolean;
}

export type SessionType = "training" | "match" | "rest" | "friendly";

export interface SessionEvent {
  id: number;
  type: SessionType;
  title: string;
  date: string;
  duration_mins: number;
  players_attended: number | null;
  total_players: number;
}

export interface SessionWidgetProps {
  sessions: SessionEvent[];
}

export interface PlayerAttributes {
  pace: number;
  passing: number;
  stamina: number;
  shooting: number;
  defending: number;
  dribbling: number;
  physicality: number;
  fitness: number;
}

export interface PlayerAnalyticsData {
  id: number;
  display_name: string;
  position: string;
  attributes: PlayerAttributes;
}

export type Grade =
  | "A+"
  | "A"
  | "A-"
  | "B+"
  | "B"
  | "B-"
  | "C+"
  | "C"
  | "C-"
  | "D"
  | "F";

export interface GradeResult {
  grade: Grade;
  colour: string;
  bg: string;
}

export interface PlayerAnalyticsWidgetProps {
  player: PlayerAnalyticsData | null;
}

export interface PlayerAttributeDetailsProps {
  attrKey: keyof PlayerAttributes;
  value: number;
  colour: string;
  bg: string;
  grade: Grade;
}

export type ActivityEventType =
  | "session_logged"
  | "player_injured"
  | "player_recovered"
  | "formation_updated"
  | "player_added"
  | "match_result";

export interface ActivityEvent {
  id: number;
  type: ActivityEventType;
  title: string;
  detail: string;
  timestamp: string;
}

export interface ActivityConfig {
  colour: string
  bg: string
}

export interface ActivityFeedWidgetProps {
  events: ActivityEvent[]
}

