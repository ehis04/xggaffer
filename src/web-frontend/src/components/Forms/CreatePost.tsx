import apiClient from "../../services/api/client";
import { COMMUNITY, REFEREE } from "../../services/api/endpoints";
import { clubsApi } from "../../services/api";
import { useAuth } from "../../context/useAuth";
import {
  buildClubSharePost,
  buildLawCourseCompletedPost,
} from "../Social/shareTemplates";
import "./css/CreatePost.css";
import { useState } from "react";
import type { Club } from "../../types/club";
import type { DashboardData } from "../../pages/referee/types/RefereeTypes";
import type { LawCourse } from "../RefereeDashboard/types/RefereeDashboardTypes";

interface CreatePostProps {
  onPost?: (content: string) => void;
  placeholder?: string;
  maxLength?: number;
}

export const CreatePost = ({
  onPost,
  placeholder = "Start Typing...",
  maxLength = 400,
}: CreatePostProps) => {
  const { user } = useAuth();
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [visibility, setVisibility] = useState<"PB" | "F" | "PR">("PB");
  const [openMenu, setOpenMenu] = useState<"courses" | "clubs" | null>(null);
  const [completedCourses, setCompletedCourses] = useState<LawCourse[]>([]);
  const [ownedClubs, setOwnedClubs] = useState<Club[]>([]);
  const [courseLoading, setCourseLoading] = useState(false);
  const [clubLoading, setClubLoading] = useState(false);
  const [courseLoadAttempted, setCourseLoadAttempted] = useState(false);
  const [clubLoadAttempted, setClubLoadAttempted] = useState(false);

  const toggleVisibility = () => {
    setVisibility((prev) => {
      if (prev === "PB") return "F";
      if (prev === "F") return "PR";
      return "PB";
    });
  };

  const getVisibilityIcon = () => {
    if (visibility === "PB") {
      return (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="white"
          className="bi bi-globe2"
          viewBox="0 0 16 16"
        >
          <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8m7.5-6.923c-.67.204-1.335.82-1.887 1.855q-.215.403-.395.872c.705.157 1.472.257 2.282.287zM4.249 3.539q.214-.577.481-1.078a7 7 0 0 1 .597-.933A7 7 0 0 0 3.051 3.05q.544.277 1.198.49zM3.509 7.5c.036-1.07.188-2.087.436-3.008a9 9 0 0 1-1.565-.667A6.96 6.96 0 0 0 1.018 7.5zm1.4-2.741a12.3 12.3 0 0 0-.4 2.741H7.5V5.091c-.91-.03-1.783-.145-2.591-.332M8.5 5.09V7.5h2.99a12.3 12.3 0 0 0-.399-2.741c-.808.187-1.681.301-2.591.332zM4.51 8.5c.035.987.176 1.914.399 2.741A13.6 13.6 0 0 1 7.5 10.91V8.5zm3.99 0v2.409c.91.03 1.783.145 2.591.332.223-.827.364-1.754.4-2.741zm-3.282 3.696q.18.469.395.872c.552 1.035 1.218 1.65 1.887 1.855V11.91c-.81.03-1.577.13-2.282.287zm.11 2.276a7 7 0 0 1-.598-.933 9 9 0 0 1-.481-1.079 8.4 8.4 0 0 0-1.198.49 7 7 0 0 0 2.276 1.522zm-1.383-2.964A13.4 13.4 0 0 1 3.508 8.5h-2.49a6.96 6.96 0 0 0 1.362 3.675c.47-.258.995-.482 1.565-.667m6.728 2.964a7 7 0 0 0 2.275-1.521 8.4 8.4 0 0 0-1.197-.49 9 9 0 0 1-.481 1.078 7 7 0 0 1-.597.933M8.5 11.909v3.014c.67-.204 1.335-.82 1.887-1.855q.216-.403.395-.872A12.6 12.6 0 0 0 8.5 11.91zm3.555-.401c.57.185 1.095.409 1.565.667A6.96 6.96 0 0 0 14.982 8.5h-2.49a13.4 13.4 0 0 1-.437 3.008M14.982 7.5a6.96 6.96 0 0 0-1.362-3.675c-.47.258-.995.482-1.565.667.248.92.4 1.938.437 3.008zM11.27 2.461q.266.502.482 1.078a8.4 8.4 0 0 0 1.196-.49 7 7 0 0 0-2.275-1.52c.218.283.418.597.597.932m-.488 1.343a8 8 0 0 0-.395-.872C9.835 1.897 9.17 1.282 8.5 1.077V4.09c.81-.03 1.577-.13 2.282-.287z" />
        </svg>
      );
    } else if (visibility === "F") {
      return (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="white"
          className="bi bi-people"
          viewBox="0 0 16 16"
        >
          <path d="M15 14s1 0 1-1-1-4-5-4-5 3-5 4 1 1 1 1zm-7.978-1L7 12.996c.001-.264.167-1.03.76-1.72C8.312 10.629 9.282 10 11 10c1.717 0 2.687.63 3.24 1.276.593.69.758 1.457.76 1.72l-.008.002-.014.002zM11 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4m3-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0M6.936 9.28a6 6 0 0 0-1.23-.247A7 7 0 0 0 5 9c-4 0-5 3-5 4q0 1 1 1h4.216A2.24 2.24 0 0 1 5 13c0-1.01.377-2.042 1.09-2.904.243-.294.526-.569.846-.816M4.92 10A5.5 5.5 0 0 0 4 13H1c0-.26.164-1.03.76-1.724.545-.636 1.492-1.256 3.16-1.275ZM1.5 5.5a3 3 0 1 1 6 0 3 3 0 0 1-6 0m3-2a2 2 0 1 0 0 4 2 2 0 0 0 0-4" />
        </svg>
      );
    } else {
      return (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="white"
          className="bi bi-lock"
          viewBox="0 0 16 16"
        >
          <path
            fillRule="evenodd"
            d="M8 0a4 4 0 0 1 4 4v2.05a2.5 2.5 0 0 1 2 2.45v5a2.5 2.5 0 0 1-2.5 2.5h-7A2.5 2.5 0 0 1 2 13.5v-5a2.5 2.5 0 0 1 2-2.45V4a4 4 0 0 1 4-4M4.5 7A1.5 1.5 0 0 0 3 8.5v5A1.5 1.5 0 0 0 4.5 15h7a1.5 1.5 0 0 0 1.5-1.5v-5A1.5 1.5 0 0 0 11.5 7zM8 1a3 3 0 0 0-3 3v2h6V4a3 3 0 0 0-3-3"
          />
        </svg>
      );
    }
  };

  const getVisibilityLabel = () => {
    if (visibility === "PB") return "Public";
    if (visibility === "F") return "Followers";
    return "Private";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) {
      return;
    }

    console.log("submitting:", content);

    setIsSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      const data = await apiClient.post<{ moderation_status?: "OK" | "UR" | "R" }>(COMMUNITY.CREATE_POST, {
          text_body: content,
          visibility: visibility,
      });
      console.log(data);
      if (data.moderation_status === "UR") {
        setNotice("Your post has been sent for review.");
      }
      if (onPost) {
        onPost(content);
      }

      setContent("");
    } catch (error) {
      setError(error instanceof Error ? error.message : "There was an error!");
      console.error("There was an error creating the post!: ", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTextAreaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    console.log("typing: ", e.target.value)
    if (e.target.value.length <= maxLength) {
      setContent(e.target.value);
    }
  };

  const applyTemplate = (template: string) => {
    if (template.length <= maxLength) {
      setContent(template);
      setNotice(null);
      setOpenMenu(null);
    } else {
      setNotice("That template is longer than the post limit.");
    }
  };

  const loadCompletedCourses = async () => {
    if (courseLoadAttempted || courseLoading) return;

    try {
      setCourseLoading(true);
      setCourseLoadAttempted(true);
      const dashboard = await apiClient.get<DashboardData>(REFEREE.DASHBOARD);
      setCompletedCourses(
        dashboard.courses.filter((course) => course.status === "completed"),
      );
    } catch (error) {
      console.error("Couldn't load completed courses:", error);
      setNotice("Couldn't load your completed courses.");
    } finally {
      setCourseLoading(false);
    }
  };

  const loadOwnedClubs = async () => {
    if (clubLoadAttempted || clubLoading) return;

    try {
      setClubLoading(true);
      setClubLoadAttempted(true);
      const clubs = await clubsApi.myClubs();
      setOwnedClubs(
        clubs.filter(
          (club) =>
            !club.is_trashed &&
            (club.creator === user?.id ||
              club.creator_username === user?.username),
        ),
      );
    } catch (error) {
      console.error("Couldn't load owned clubs:", error);
      setNotice("Couldn't load your clubs.");
    } finally {
      setClubLoading(false);
    }
  };

  const toggleMenu = (menu: "courses" | "clubs") => {
    const nextMenu = openMenu === menu ? null : menu;
    setOpenMenu(nextMenu);

    if (nextMenu === "courses") {
      void loadCompletedCourses();
    }

    if (nextMenu === "clubs") {
      void loadOwnedClubs();
    }
  };

  return (
    <div className="createPost-container">
      <div className="create-text-box">
        <div className="create-text-box-container">
          <form onSubmit={handleSubmit}>
            <textarea
              placeholder={placeholder}
              value={content}
              onChange={handleTextAreaChange}
              disabled={isSubmitting}
            ></textarea>
            {notice && <div className="create-post-notice">{notice}</div>}
            <div className="attachments">
              <div className="create-post-template-menu">
                <button
                  type="button"
                  onClick={() => toggleMenu("courses")}
                  title="Share a completed course"
                  aria-expanded={openMenu === "courses"}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    fill="white"
                    className="bi bi-mortarboard"
                    viewBox="0 0 16 16"
                  >
                    <path d="M8.211 2.047a.5.5 0 0 0-.422 0l-7.5 3.5a.5.5 0 0 0 .025.917l7.5 3a.5.5 0 0 0 .372 0L14 7.14V11.5a.5.5 0 0 0 1 0V6.739l.686-.275a.5.5 0 0 0 .025-.917z" />
                    <path d="M4.176 9.032a.5.5 0 0 0-.656.475v1.88a2 2 0 0 0 1.052 1.762l2.5 1.345a2 2 0 0 0 1.856 0l2.5-1.345a2 2 0 0 0 1.052-1.762v-1.88a.5.5 0 0 0-.656-.475l-3.638 1.455a.5.5 0 0 1-.372 0z" />
                  </svg>
                </button>
                {openMenu === "courses" && (
                  <div className="create-post-dropdown">
                    {courseLoading && (
                      <div className="create-post-dropdown-empty">
                        Loading courses...
                      </div>
                    )}
                    {!courseLoading && completedCourses.length === 0 && (
                      <div className="create-post-dropdown-empty">
                        No completed courses yet.
                      </div>
                    )}
                    {!courseLoading &&
                      completedCourses.map((course) => (
                        <button
                          key={course.law_number}
                          type="button"
                          onClick={() =>
                            applyTemplate(buildLawCourseCompletedPost(course))
                          }
                        >
                          Law {course.law_number}: {course.title}
                        </button>
                      ))}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={toggleVisibility}
                title={`Visibility: ${getVisibilityLabel()}`}
              >
                {getVisibilityIcon()}
              </button>
              <div className="create-post-template-menu">
                <button
                  type="button"
                  onClick={() => toggleMenu("clubs")}
                  title="Share one of your clubs"
                  aria-expanded={openMenu === "clubs"}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    fill="white"
                    className="bi bi-shield"
                    viewBox="0 0 16 16"
                  >
                    <path d="M5.338 1.59 8 0l2.662 1.59 3.023.337.336 3.022L16 7.612l-1.979 2.662-.336 3.022-3.023.337L8 15.223l-2.662-1.59-3.023-.337-.336-3.022L0 7.612 1.979 4.95l.336-3.022zM8 4.5a3.112 3.112 0 1 0 0 6.224A3.112 3.112 0 0 0 8 4.5" />
                  </svg>
                </button>
                {openMenu === "clubs" && (
                  <div className="create-post-dropdown">
                    {clubLoading && (
                      <div className="create-post-dropdown-empty">
                        Loading clubs...
                      </div>
                    )}
                    {!clubLoading && ownedClubs.length === 0 && (
                      <div className="create-post-dropdown-empty">
                        No owned clubs found.
                      </div>
                    )}
                    {!clubLoading &&
                      ownedClubs.map((club) => (
                        <button
                          key={club.id}
                          type="button"
                          onClick={() => applyTemplate(buildClubSharePost(club))}
                        >
                          {club.name}
                        </button>
                      ))}
                  </div>
                )}
              </div>
              <button
                type="submit"
                className="send-post"
                disabled={isSubmitting || !content.trim()}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  fill="white"
                  className="bi bi-arrow-up-circle-fill"
                  viewBox="0 0 16 16"
                >
                  <path d="M16 8A8 8 0 1 0 0 8a8 8 0 0 0 16 0m-7.5 3.5a.5.5 0 0 1-1 0V5.707L5.354 7.854a.5.5 0 1 1-.708-.708l3-3a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 5.707z" />
                </svg>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
