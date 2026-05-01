import { CoursePanelItem } from "./CoursePanelItem";
import type { CourseItem, CourseSection } from "./types/CourseTypes";
import './css/CoursePanel.css';

interface CoursePanelSectionProps {
  section: CourseSection;
  toggle: (id: string) => void;
  done: number;
  open: boolean;
  completedIds: Set<string>;
  currentItemId: string;
  onNavigate: (id: string) => void;
}

export const CoursePanelSection = ({
  section,
  toggle,
  done,
  open,
  completedIds,
  currentItemId,
  onNavigate,
}: CoursePanelSectionProps) => {
  return (
    <div key={section.id} className="cps-container">
      <button className="cps-header" onClick={() => toggle(section.id)} aria-expanded={open}>
        <div className="cps-header-left">
          <span className="cps-title">{section.title}</span>
        </div>
        <div className="cps-header-right">
          <span className="cps-tracker">
            {done}/{section.items.length}
          </span>
          <span className={`cps-icon ${open ? "open" : ""}`}></span>
        </div>
      </button>

      {open && (
        <div className="cps-items">
          {section.items.map((item: CourseItem, ii: number) => {
            const isActive = item.id === currentItemId;
            const isDone = completedIds.has(item.id);
            const isLocked = false;
            const isLast = ii === section.items.length - 1;

            return (
              <CoursePanelItem
                key={item.id}
                item={item}
                isActive={isActive}
                isLocked={isLocked}
                onNavigate={onNavigate}
                isDone={isDone}
                isLast={isLast}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};
