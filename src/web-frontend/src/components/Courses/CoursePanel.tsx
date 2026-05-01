import { useState } from "react";
import type { CourseSection} from "./types/CourseTypes";
import "./css/CoursePanel.css";
import { CoursePanelSection } from "./CoursePanelSection";

export interface CoursePathProps {
  sections: CourseSection[];
  currentItemId: string;
  completedIds: Set<string>;
  onNavigate: (id: string) => void;
}

export const CoursePanel = ({
  sections,
  currentItemId,
  completedIds,
  onNavigate,
}: CoursePathProps) => {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const toggleSec = (id: string) => {
    setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const isOpen = (id: string) => collapsed[id] !== true;

  return (
    <div className="course-panel-container">
      {sections.map((section) => {
        const doneCount = section.items.filter((i) =>
          completedIds.has(i.id),
        ).length;
        const open = isOpen(section.id);

        return (
          <CoursePanelSection
            section={section}
            toggle={toggleSec}
            done={doneCount}
            open={open}
            completedIds={completedIds}
            currentItemId={currentItemId}
            onNavigate={onNavigate}
          />
        );
      })}
    </div>
  );
};
