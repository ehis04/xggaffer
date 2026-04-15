import type { DrillContentProps } from "./types/CourseTypes";
import "./css/DrillContent.css";

export const DrillContent = ({
  item,
  answers,
  submitted,
  onAnswer,
  onSubmit,
  onReset,
}: DrillContentProps) => {
  const { drill } = item;
  if (!drill) return null;

  const allAns = Object.keys(answers).length === drill.items.length;

  const score = submitted
    ? Object.entries(answers).filter(([i, a]) => a === drill.items[Number(i)].a)
        .length
    : 0;

  const getTrueClass = (i: number) => {
    const a = answers[i];
    const cor = drill.items[i].a;
    if (!submitted) return a === "true" ? "drill-btn selected" : "drill-btn";
    if (a === "true")
      return cor === "true" ? "drill-btn correct" : "drill-btn wrong";
    if (cor === "true") return "drill-btn correct-miss";
    return "drill-btn";
  };

  const getFalseClass = (i: number) => {
    const a = answers[i];
    const cor = drill.items[i].a;
    if (!submitted) return a === "false" ? "drill-btn selected" : "drill-btn";
    if (a === "false")
      return cor === "false" ? "drill-btn correct" : "drill-btn wrong";
    if (cor === "false") return "drill-btn correct-miss";
    return "drill-btn";
  };

  return (
    <div className="drill-content">
      <div className="course-type-title"> Quick Drill </div>
      <div className="ct-title">{item.title}</div>
      <div className="dc-divider" />
      <p className="dc-desc">{drill.desc}</p>
      <div className="dc-items">
        {drill.items.map((drItem, i) => (
          <div key={i} className="dc-item">
            <span className="dc-statement">{drItem.s}</span>
            <div className="dc-buttons">
              <button
                className={getTrueClass(i)}
                disabled={submitted}
                onClick={() => onAnswer(i, "true")}
              >
                {" "}
                True{" "}
              </button>
              <button
                className={getFalseClass(i)}
                disabled={submitted}
                onClick={() => onAnswer(i, "false")}
              >
                {" "}
                False{" "}
              </button>
            </div>
          </div>
        ))}
      </div>

      {submitted ? (
        <div className="dc-result">
          <p className="dc-score">
            Score: <span className="dc-score-val"> {score} </span> /{" "}
            {drill.items.length} correct
          </p>
          <button className="content-reset-btn" onClick={onReset}>
            Try Again
          </button>
        </div>
      ) : (
        <button className="dc-submit-btn" disabled={!allAns} onClick={onSubmit}>
          Submit Drill
        </button>
      )}
    </div>
  );
};
