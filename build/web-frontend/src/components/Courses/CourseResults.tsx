import "./css/CourseResults.css";
import type { CourseResultsProps } from "./types/CourseTypes";
import { courseType } from "./functions/courseType";
import { CourseResultsType } from "./CourseResultsType";
import { CourseResultsItem } from "./CourseResultsItem";

export const CourseResults = ({sections, completedIds, onNavigate}: CourseResultsProps) => {
    const allItems = sections.flatMap((s) => s.items);
    const done = completedIds.size
    const total = allItems.length
    const minLeft = allItems.filter((i) => !completedIds.has(i.id)).reduce((s, i) => s + i.mins, 0)

    const byType = ['quiz', 'scenario', 'drill'] as const;

    return (
        <div className="course-results-container">
            <div className="cr-header">
                <h3 className="cr-header-title"> Your Progress </h3>
                <p className="cr-header-sub">{done}/{total}</p>
            </div>

            <div className="cr-stats-grid">
                <div className="cr-stat">
                    <span className="cr-stat-value">{done}</span>
                    <span className="cr-stat-lbl"> Progress</span>
                </div>
                <div className="cr-stat">
                    <span className="cr-stat-value">{minLeft}</span>
                    <span className="cr-stat-lbl"> Minutes left</span>
                </div>
            </div>

            <div className="cr-by-type">
                <p className="cr-section-lbl"> By Type</p>
                {byType.map((type) => {
                    const cType = courseType[type];
                    const items = allItems.filter((i) => i.type === type);
                    const doneCount = items.filter((i) => completedIds.has(i.id)).length;
                    return (<CourseResultsType type={type} cType={cType} doneCount={doneCount} items={items}/>)
                })}
            </div>
        </div>
        
    )
}