import "./css/ScenarioContent.css";
import type { ScenarioContentProps } from "./types/CourseTypes";

export const ScenarioContent = ({
  item,
  selectedOption,
  revealed,
  onSelect,
  onCheck,
  onReset,
}: ScenarioContentProps) => {
  const { scenario } = item;
  if (!scenario) return null;

  const getOptionClass = (optId: string) => {
    if (!revealed)
      return selectedOption === optId ? "sc-option selected" : "sc-option";
    if (optId === scenario?.cor) return "sc-option correct";
    if (optId === selectedOption) return "sc-option wrong";
    return "sc-option";
  };

  return (
    <div className="scenario-content">
      <div className="course-type-title"> Scenario </div>
      <h2 className="ct-title">{item.title}</h2>
      <div className="sc-divider" />

      <div className="sc-situation">{scenario?.sit}</div>
      <p className="sc-prompt"> What is your decision? </p>

      <div className="sc-options">
        {scenario?.opts.map((opt) => (
          <button
            key={opt.id}
            className={getOptionClass(opt.id)}
            onClick={() => !revealed && onSelect(opt.id)}
            disabled={revealed}
            aria-label={`Option ${opt.id.toUpperCase()}: ${opt.t}`}
          >
            <span className="sc-opt-key">{opt.id.toUpperCase()}</span>
            <span className="sc-opt-text">{opt.t}</span>
          </button>
        ))}
      </div>

      {!revealed && (
        <button
          className="sc-check-btn"
          disabled={!selectedOption}
          onClick={onCheck}
        >
          Check Answer
        </button>
      )}

      {revealed && (
        <div className="sc-explanation">
          <strong className="sc-expl-lbl">Explanation</strong>
          {scenario?.expl}{" "}
          <button className="content-reset-btn" onClick={onReset}>
            Try Again
          </button>
        </div>
      )}
    </div>
  );
};
