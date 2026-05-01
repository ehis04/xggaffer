import type { ClauseContentProps } from "./types/CourseTypes";
import './css/ClauseContent.css'

export const ClauseContent = ({item, isRead}: ClauseContentProps) => {
    const {clause} = item;
    if (!clause) return null;

    const para = clause.txt.split('\n\n');

    return (
        <div className="clause-content">
            <div className="cc-meta">
                <div className="cc-meta-left">
                    <span className="cc-law-lbl">Law</span>
                    <span className="cc-index"> Clause {clause.n}</span>
                </div>
                {isRead && <span className="cc-read-badge"> ✓ Read</span>}
            </div>

            <h2 className="clause-c-title">
                <span className="cc-sec-num">
                    {clause.n}
                </span>
                {item.title}
            </h2>

            <div className="cc-body">
                {para.map((block, i) => {
                    return (
                        <div key={i} className="cc-paragraph"> {block.trim()} </div>

                    )
                })}
            </div>
        </div>
    )
}