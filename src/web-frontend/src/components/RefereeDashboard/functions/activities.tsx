import type { PerformanceData } from "../types/RefereeDashboardTypes";

export const activities: {
  key: keyof Omit<PerformanceData, "overall_score">;
  label: string;
  colour: string;
}[] = [
  { key: "quizzes", label: "Quizzes", colour: "var(--quiz-colour)" },
  { key: "scenarios", label: "Scenarios", colour: "var(--scenario-colour)" },
  { key: "drills", label: "Drills", colour: "var(--drill-colour)" },
  { key: "clauses", label: "Clauses", colour: "var(--clause-colour)"},
];
