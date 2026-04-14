import type { ActiveCourse, PerformanceData, StreakData } from "../../../components/RefereeDashboard/types/RefereeDashboardTypes";
import type { LawCourse } from "../../../components/RefereeDashboard/types/RefereeDashboardTypes";

export const MOCK_ACTIVE_COURSE: ActiveCourse = {
  law_number: 12,
  title: "Fouls & Misconduct",
  progress_percentage: 68,
  clauses_read: 17,
  total_clauses: 25,
};

export const MOCK_STREAK: StreakData = {
  current_streak: 9,
  // ISO strings for each day the user studied this week
  // isSameDay() from calendarFuncs handles the comparison
  studied_dates: [
    "2025-03-10", // Mon
    "2025-03-11", // Tue
    "2025-03-12", // Wed
    "2025-03-13", // Thu
    "2025-03-14", // Fri
    "2025-03-15", // Sat (today in this example)
    "2026-03-19",
  ],
};

export const MOCK_COURSES: LawCourse[] = [
  {
    law_number: 1,
    title: "The Field of Play",
    description: "Dimensions, markings, goals, and surface requirements.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 12,
    total_clauses: 12,
  },
  {
    law_number: 2,
    title: "The Ball",
    description: "Specifications for size, weight, material, and pressure.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 6,
    total_clauses: 6,
  },
  {
    law_number: 3,
    title: "The Players",
    description: "Team size, substitutions, and player requirements.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 10,
    total_clauses: 10,
  },
  {
    law_number: 4,
    title: "The Players' Equipment",
    description: "Mandatory kit, prohibited items, and colours.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 8,
    total_clauses: 8,
  },
  {
    law_number: 5,
    title: "The Referee",
    description: "Powers, duties, and decisions of the referee.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 14,
    total_clauses: 14,
  },
  {
    law_number: 6,
    title: "The Other Match Officials",
    description: "Assistant referees, fourth officials, and VAR roles.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 9,
    total_clauses: 9,
  },
  {
    law_number: 7,
    title: "The Duration of the Match",
    description: "Periods of play, half-time, and added time.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 7,
    total_clauses: 7,
  },
  {
    law_number: 8,
    title: "The Start and Restart of Play",
    description: "Kick-off, dropped ball, and restart procedures.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 8,
    total_clauses: 8,
  },
  {
    law_number: 9,
    title: "The Ball In and Out of Play",
    description: "When the ball is in play and when it is out.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 5,
    total_clauses: 5,
  },
  {
    law_number: 10,
    title: "Determining the Outcome",
    description: "Scoring a goal, extra time, and penalty shoot-outs.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 8,
    total_clauses: 8,
  },
  {
    law_number: 11,
    title: "Offside",
    description: "Offside position, offside offence, and no-offside situations.",
    status: "completed",
    progress_percentage: 100,
    clauses_read: 11,
    total_clauses: 11,
  },
  {
    law_number: 12,
    title: "Fouls & Misconduct",
    description: "Direct & indirect free kicks, yellow & red card offences.",
    status: "active",
    progress_percentage: 68,
    clauses_read: 17,
    total_clauses: 25,
  },
  {
    law_number: 13,
    title: "Free Kicks",
    description: "Direct and indirect free kicks, wall distance, and execution.",
    status: "locked",
    progress_percentage: 0,
    clauses_read: 0,
    total_clauses: 10,
  },
  {
    law_number: 14,
    title: "The Penalty Kick",
    description: "Procedure, encroachment, and retaking of penalty kicks.",
    status: "locked",
    progress_percentage: 0,
    clauses_read: 0,
    total_clauses: 9,
  },
  {
    law_number: 15,
    title: "The Throw-in",
    description: "Correct technique and infringements at the throw-in.",
    status: "locked",
    progress_percentage: 0,
    clauses_read: 0,
    total_clauses: 7,
  },
  {
    law_number: 16,
    title: "The Goal Kick",
    description: "Procedure and restrictions during a goal kick.",
    status: "locked",
    progress_percentage: 0,
    clauses_read: 0,
    total_clauses: 6,
  },
  {
    law_number: 17,
    title: "The Corner Kick",
    description: "Procedure, positioning, and infringements at corner kicks.",
    status: "locked",
    progress_percentage: 0,
    clauses_read: 0,
    total_clauses: 6,
  },
];

export const MOCK_PERFORMANCE: PerformanceData = {
  overall_score: 72,
  quizzes: {
    score: 82,
  },
  scenarios: {
    score: 60,
  },
  drills: {
    score: 71,
  },
  clauses: {
    score: 88,
  },
};