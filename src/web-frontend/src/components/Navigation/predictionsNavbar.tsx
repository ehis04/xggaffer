import { useNavigate } from "react-router-dom";
import { PRED_SECTIONS, type HubContext } from "../../pages/predictions/PredictionsHub";
import { resolveSectionPath } from "./functions/resolveSectionPath";
import styles from "./css/predictionsNavbar.module.css";

interface PredictionsNavbarProps {
  context?: HubContext;
}

export const PredictionsNavbar = ({ context }: PredictionsNavbarProps) => {
  const navigate = useNavigate();
  return (
    <div className={styles.buttonContainer}>
      {PRED_SECTIONS.map((section) => (
        <button
          key={section.title}
          className={styles.button}
          type="button"
          onClick={() => navigate(resolveSectionPath(section, context))}
          aria-label={section.label}
        >
          <span className={styles.cardIcon}>{section.icon}</span>
        </button>
      ))}
    </div>
  );
};
