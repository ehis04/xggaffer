import "./css/PerformanceWidget.css";
const circumference = 2 * Math.PI * 28;

export const PerformanceRing = ({ score }: { score: number }) => {
  const filled = ((100 - score) / 100) * circumference;

  const ringColour =
    score >= 75 ? "#3ba735" : score >= 40 ? "#f19b39" : "#dc1515";

  return (
    <div className="pr-container">
      <svg
        className="pr-ring"
        viewBox="0 0 64 64"
        aria-label={`Overall performance score: ${score} out of 100`}
        role="img"
      >
        <circle
          cx="32"
          cy="32"
          r="28"
          fill="none"
          stroke="rgba(61,214,140,0.1)"
          strokeWidth="5.5"
        />
        <circle
          cx="32"
          cy="32"
          r="28"
          fill="none"
          stroke={ringColour}
          strokeWidth="5.5"
          strokeDasharray={circumference}
          strokeDashoffset={filled}
          strokeLinecap="round"
          transform="rotate(-90 32 32)"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        <text
          x="32"
          y="29"
          textAnchor="middle"
          dominantBaseline="central"
          className="pr-ring-score"
        >
          {score}
        </text>
        <text
          x="32"
          y="42"
          textAnchor="middle"
          dominantBaseline="central"
          className="pr-ring-sub"
        >
          / 100
        </text>
      </svg>

      <div className="pr-ring-lbl">
        <span className="pr-ring-title">Overall</span>
        <span className="pr-ring-hint">across all laws</span>
      </div>
    </div>
  );
};
