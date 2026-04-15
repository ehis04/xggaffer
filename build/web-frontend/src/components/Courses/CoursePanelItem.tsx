import "./css/CoursePanel.css";

export const CoursePanelItem = ({ item, isActive, isLocked, onNavigate, isDone, isLast }) => {
  return (
    <button
      key={item.id}
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
