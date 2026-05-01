import type { CourseItem } from "./types/CourseTypes";

interface CourseResultsTypeProps {
  cType: { label: string; colour: string; bg: string };
  doneCount: number;
  items: CourseItem[];
}

export const CourseResultsType = ({cType, doneCount, items}: CourseResultsTypeProps) => {
    return (
        <div className="crt-row">
            <div className="crt-left">
                <div className="crt-name" style={{background: cType.bg, color: cType.colour}}>
                    {cType.label} task
                </div>
            </div>
            <span className="crt-score">
                {doneCount}/{items.length}
            </span>
        </div>
    )
}