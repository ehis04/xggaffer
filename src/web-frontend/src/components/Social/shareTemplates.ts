import type { Club } from "../../types/club";
import type { LawCourse } from "../RefereeDashboard/types/RefereeDashboardTypes";

const clean = (value: string) => value.trim().replace(/\s+/g, " ");

export const buildCourseCompletedPost = (courseName: string) =>
  `I just completed the ${clean(courseName)} course.`;

export const buildLawCourseCompletedPost = (course: LawCourse) =>
  buildCourseCompletedPost(`Law ${course.law_number}: ${course.title}`);

export const buildClubInvitePost = (clubName: string, joinCode?: string | null) => {
  const base = `Join my club, ${clean(clubName)}!`;
  return joinCode ? `${base} Use join code ${clean(joinCode)}.` : base;
};

export const buildClubJoinUrl = (clubId: number) => {
  if (typeof window === "undefined") {
    return `/clubs/${clubId}/`;
  }

  return `${window.location.origin}/clubs/${clubId}/`;
};

export const buildClubSharePost = (club: Club) =>
  [
    buildClubInvitePost(
      club.name,
      club.directory_visibility === "hidden_code_only" ? club.join_code : null,
    ),
    `Request to join here: ${buildClubJoinUrl(club.id)}`,
  ].join(" ");
