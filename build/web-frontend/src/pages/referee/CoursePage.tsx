import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { CoursePanel } from "../../components/Courses/CoursePanel";
import { CourseContent } from "../../components/Courses/CourseContent";
import { CourseResults } from "../../components/Courses/CourseResults";
import { CoursePanelTabs } from "../../components/Courses/CoursePanelTabs";
import type { CoursePanelTab } from "../../components/Courses/CoursePanelTabs";
import { Sidebar } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import type {
  CourseSection,
  DrillAnswers,
} from "../../components/Courses/types/CourseTypes";
import apiClient from "../../services/api/client";
import { REFEREE } from "../../services/api/endpoints";
import "./css/CoursePage.css";
import type { CourseResponse } from "./types/RefereeTypes";

export const CoursePage = () => {
  const { lawNumber } = useParams<{ lawNumber: string }>();

  const [sections, setSections] = useState<CourseSection[]>([]);
  const [lawTitle, setLawTitle] = useState("");
  const [lawNum, setLawNum] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log("lawNumber from params:", lawNumber);
    if (!lawNumber) return;

    const fetchCourse = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await apiClient.get<CourseResponse>(
          REFEREE.COURSE_BY_NUMBER(Number(lawNumber)),
        );
        console.log("Course api response: ", data);
        setSections(data.sections);
        setLawTitle(data.law_title);
        setLawNum(data.law_number);
      } catch (err) {
        console.error("CoursePage fetch error:", err);
        setError(err instanceof Error ? err.message : "Failed to load course.");
      } finally {
        setLoading(false);
      }
    };

    fetchCourse();
  }, [lawNumber]);


  const flatItems = useMemo(() => sections.flatMap((s) => s.items), [sections]);

  const [completedIds, setCompletedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (flatItems.length > 0) {
      setCompletedIds(
        new Set(
          flatItems.filter((i) => i.status === "completed").map((i) => i.id),
        ),
      );
    }
  }, [flatItems]);
  const [currentItemId, setCurrentItemId] = useState("");

  useEffect(() => {
    if (flatItems.length > 0 && !currentItemId) {
      setCurrentItemId(
        flatItems.find((i) => i.status === "active")?.id ??
          flatItems[0]?.id ??
          "",
      );
    }
  }, [flatItems]);

  const currentIndex = flatItems.findIndex((i) => i.id === currentItemId);
  const currentItem = flatItems[currentIndex];

  const navigate = (id: string) => {
    const item = flatItems.find((i) => i.id === id);
    if (!item) return;
    setCurrentItemId(id);
  };

  const navPrev = () => {
    const prev = flatItems[currentIndex - 1];
    if (prev) navigate(prev.id);
  };

  const navNext = () => {
    const next = flatItems[currentIndex + 1];
    if (next) navigate(next.id);
  };

  useEffect(() => {
    if (!currentItem || currentItem.type !== "clause") return;
    if (completedIds.has(currentItemId)) return;

    setCompletedIds((prev) => new Set([...prev, currentItemId]));

    apiClient
      .post(REFEREE.PROGRESS_COMPLETE, { item_id: Number(currentItemId) })
      .catch((err) => console.error("Failed to mark clause complete:", err));
  }, [currentItemId]);

  const [scenarioSelections, setScenarioSelections] = useState<
    Record<string, string>
  >({});
  const [scenarioRevealed, setScenarioRevealed] = useState<Set<string>>(
    new Set(),
  );

  const handleScenarioSelect = (itemId: string, optId: string) => {
    if (scenarioRevealed.has(itemId)) return;
    setScenarioSelections((prev) => ({ ...prev, [itemId]: optId }));
  };

  const handleScenarioCheck = async (itemId: string) => {
    setScenarioRevealed((prev) => new Set([...prev, itemId]));
    const item = flatItems.find((i) => i.id === itemId);
    if (!item?.scenario) return;

    const selectedId = scenarioSelections[itemId];

    if (selectedId === item.scenario.cor) {
      setCompletedIds((prev) => new Set([...prev, itemId]));
    }

    try {
      await apiClient.post(REFEREE.PROGRESS_SCENARIO, {
        item_id: Number(itemId),
        selected_id: selectedId,
      });
    } catch (err) {
      console.error("Failed to submit scenario:", err);
    }
  };

  const [drillAnswers, setDrillAnswers] = useState<
    Record<string, DrillAnswers>
  >({});
  const [drillSubmitted, setDrillSubmitted] = useState<Set<string>>(new Set());

  const handleDrillAnswer = (
    itemId: string,
    index: number,
    value: "true" | "false",
  ) => {
    setDrillAnswers((prev) => ({
      ...prev,
      [itemId]: { ...(prev[itemId] ?? {}), [index]: value },
    }));
  };

  const handleDrillSubmit = async (itemId: string) => {
    setDrillSubmitted((prev) => new Set([...prev, itemId]));
    const item = flatItems.find((i) => i.id === itemId);
    if (!item?.drill) return;

    const answers = drillAnswers[itemId] ?? {};

    const correct = Object.entries(answers).filter(
      ([i, a]) => a === item.drill!.items[Number(i)].a,
    ).length;
    if (correct >= Math.ceil(item.drill.items.length * 0.6)) {
      setCompletedIds((prev) => new Set([...prev, itemId]));
    }

    try {
      await apiClient.post(REFEREE.PROGRESS_DRILL, {
        item_id: Number(itemId),
        answers: Object.fromEntries(
          Object.entries(answers).map(([k, v]) => [k, v]),
        ),
      });
    } catch (err) {
      console.error("Failed to submit drill:", err);
    }
  };

  const [activeTab, setActiveTab] = useState<CoursePanelTab>("path");

  const progress =
    flatItems.length > 0
      ? Math.round((completedIds.size / flatItems.length) * 100)
      : 0;

  if (loading) {
    return (
      <div className="course-page-container">
        <Sidebar />
        <div className="course-page">
          <div className="course-loading">Loading course...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="course-page-container">
        <Sidebar />
        <div className="course-page">
          <div className="course-error">{error}</div>
        </div>
      </div>
    );
  }


  return (
    <div className="course-page-container">
      <Sidebar />

      <div className="course-page">
        <header className="course-header">
          <div className="course-header-left">
            <span className="course-law-badge">Law {lawNum}</span>
            <h1 className="course-header-title">{lawTitle}</h1>
          </div>
          <div className="course-header-right">
            <div className="course-progress-wrap">
              <span className="course-progress-pct">{progress}%</span>
              <div className="course-progress-bar">
                <div
                  className="course-progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
            <SocialUserButtons />
          </div>
        </header>

        <main className="course-body">
          <section className="course-content-pane">
            <div className="course-content-scroll">
              {currentItem && (
                <CourseContent
                  item={currentItem}
                  completedIds={completedIds}
                  scenarioSelections={scenarioSelections}
                  scenarioRevealed={scenarioRevealed}
                  onScenarioSelect={handleScenarioSelect}
                  onScenarioCheck={handleScenarioCheck}
                  drillAnswers={drillAnswers}
                  drillSubmitted={drillSubmitted}
                  onDrillAnswer={handleDrillAnswer}
                  onDrillSubmit={handleDrillSubmit}
                  // onScenarioReset={}
                  // onDrillReset={}
                />
              )}
            </div>

            <footer className="course-nav-footer">
              <button
                className="course-nav-btn course-nav-prev"
                onClick={navPrev}
                disabled={currentIndex === 0}
              >
                ← Previous
              </button>

              <div className="course-nav-info">
                <span>
                  {currentIndex + 1} / {flatItems.length}
                </span>
                {currentItem && <span>~{currentItem.mins} min</span>}
              </div>

              <button
                className="course-nav-btn course-nav-next"
                onClick={navNext}
                disabled={currentIndex === flatItems.length - 1}
              >
                Next →
              </button>
            </footer>
          </section>

          <aside className="course-right-panel">
            <CoursePanelTabs activeTab={activeTab} onChange={setActiveTab} />

            <div className="course-panel-body">
              {activeTab === "path" ? (
                <CoursePanel
                  sections={sections}
                  currentItemId={currentItemId}
                  completedIds={completedIds}
                  onNavigate={navigate}
                />
              ) : (
                <CourseResults
                  sections={sections}
                  completedIds={completedIds}
                  onNavigate={(id) => {
                    navigate(id);
                    setActiveTab("results");
                  }}
                />
              )}
            </div>
          </aside>
        </main>
      </div>
    </div>
  );
};
