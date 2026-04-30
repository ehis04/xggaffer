import "./css/DashboardCard.css";
import { dayLabels } from "../Dashboard/functions/dayLabels";
import type { RefereeDashboardCardProps } from "./types/RefereeDashboardTypes";
import { StreakDay } from "./StreakDay";
import { getUserProfile } from "../Navigation/functions/getUserProfile";
import { useEffect, useState } from "react";
import type { UserData } from "../Navigation/SideBar";
import { getWeekDates, isSameDay } from "../Dashboard/functions/calenderFuncs";
import { ProfileButton } from "../Buttons/ProfileButton";
import { ActiveCourseProgress } from "./ActiveCourseProgress";

export const DashboardCard = ({
  activeCourse,
  streak,
}: RefereeDashboardCardProps) => {
  const [userData, setUserData] = useState<UserData | null>(null);
  const weekDates = getWeekDates();
  const today = new Date();
  const studiedDates = streak?.studied_dates.map((d) => new Date(d));

  useEffect(() => {
    getUserProfile(setUserData);
  }, []);

  const handleProfileClick = (username: string) => {
    globalThis.location.href = `/profile/${username}`;
  };

  return (
    <div className="ref-dashboard-card">
      <div className="rdc-profile">
        {userData && (
          <ProfileButton
            username={userData.username}
            profileImage={userData.profile_image ?? undefined}
            size="extra-large"
            onClick={handleProfileClick}
          />
        )}{" "}
      </div>
      <h2 className="rdc-name"> Welcome, {userData?.display_name}!</h2>
      <p className="rdc-username">@{userData?.username}</p>

      {activeCourse ? (
        <div className="rdc-course">
          <span className="rdc-current-course">
            Currently Studying - Law {activeCourse.law_number}
          </span>
          <h3 className="rdc-course-title"> {activeCourse.title}</h3>
          <div className="rdc-progress-header">
            <span className="rdc-course-progress">Course Progress</span>
            <span className="rdc-progress-perc">
              {activeCourse.progress_percentage}%
            </span>
          </div>
          <div className="rdc-current-pb">
            <ActiveCourseProgress
              percentage={activeCourse.progress_percentage}
            />
          </div>
        </div>
      ) : (
        <div className="rdc-current-course-empty">
          <span className="rdc-current-course-empty-txt">
            Select a Course and Begin Your Referee Journey!{" "}
          </span>
        </div>
      )}

      <div className="rdc-streak">
        <div className="rdc-icon-container">
          <span className="rdc-streak-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              fill="var(--bright-orange)"
              className="bi bi-clock"
              viewBox="0 0 16 16"
            >
              <path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71z" />
              <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0" />
            </svg>
          </span>
        </div>
        <div className="rdc-streak-txt">
          <h3 className="rdc-streak-label"> Learning Streak </h3>
          <span className="rdc-streak-count"> {streak?.current_streak}</span>
          <span className="rdc-streak-ft">days in a row</span>
        </div>
      </div>

      <div className="rdc-week" role="list">
        {weekDates.map((date, i) => {
          const isToday = isSameDay(date, today);
          const studied = (studiedDates ?? []).some((d) => isSameDay(d, date));
          return (
            <StreakDay
              key={i}
              label={dayLabels[i]}
              studied={studied}
              isToday={isToday}
            />
          );
        })}
      </div>

      <button className="rdc-continue" disabled={!activeCourse}>
        Continue Studying
      </button>
    </div>
  );
};
