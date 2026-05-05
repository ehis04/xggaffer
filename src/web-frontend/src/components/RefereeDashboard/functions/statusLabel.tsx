import type { CourseStatus } from "../types/RefereeDashboardTypes";

export const statusLabel : Record<CourseStatus, string> = {
  completed: "Complete",
  active: "In Progress",
  locked: "Locked",
}