import { CourseMap } from "../../components/RefereeDashboard/CourseMap";
import { DashboardCard } from "../../components/RefereeDashboard/DashboardCard";
import { PerformanceWidget } from "../../components/RefereeDashboard/PerformanceWidget";
import { YourCourses } from "../../components/RefereeDashboard/YourCourses";
import "./css/RefereeHome.css";
import { Sidebar } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import type { DashboardData } from "./types/RefereeTypes";
import { useEffect, useState } from "react";
import apiClient from "../../services/api/client";
import { REFEREE } from "../../services/api/endpoints";

export const RefereeHome = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const json = await apiClient.get<DashboardData>(REFEREE.DASHBOARD);
        setData(json);
      } catch (error) {
        console.error("Error with Referee Dashboard data: ", error);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="rh-container">
        <div className="sidebar-section">
          <Sidebar />
        </div>
        <div className="referee-home">
          <div className="rh-loading">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="rh-container">
      <div className="sidebar-section">
        <Sidebar />
      </div>
      <div className="referee-home">
        <header className="referee-home-header">
          <div className="referee-home-left">Courses Dashboard</div>
          <div className="referee-home-mid"></div>
          <div className="referee-home-right">
            <SocialUserButtons />
          </div>
        </header>

        <main className="referee-home-content">
          <DashboardCard
            activeCourse={data?.active_course}
            streak={data?.streak}
          />
          <YourCourses courses={data?.courses} />
          <PerformanceWidget data={data?.performance} />
          <CourseMap courses={data?.courses} />
        </main>
      </div>
    </div>
  );
};
