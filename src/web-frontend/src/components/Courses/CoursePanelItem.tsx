import "./css/CoursePanel.css";
import type { CourseItem } from "./types/CourseTypes";

interface CoursePanelItemProps {
  item: CourseItem;
  isActive: boolean;
  isLocked: boolean;
  onNavigate: (id: string) => void;
  isDone: boolean;
  isLast: boolean;
}

export const CoursePanelItem = ({ item, isActive, isLocked, onNavigate, isDone, isLast }: CoursePanelItemProps) => {
  return (
    <button
      className={`cpi ${isActive ? "active" : ""} ${isLocked ? "locked" : ""}`}
      onClick={() => !isLocked && onNavigate(item.id)}
      disabled={isLocked}
      aria-current={isActive ? "true" : undefined}
    >
      <div className="cpi-indicator">
        <div className="cpi-status">{isDone ? '✓' : 'x'}</div>
        {!isLast && (<div className={`cpi-line ${isDone ? 'done' : ''}`}/>)}
      </div>
      <div className="cpi-info">
        <span className='cpi-title'>{item.title}</span>
        <span className="cp-item-dur">{item.mins} mins</span>
      </div>
    </button>
  );
};
