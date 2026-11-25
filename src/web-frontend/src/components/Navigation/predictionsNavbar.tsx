import { useNavigate } from "react-router-dom";
import { PRED_SECTIONS } from "../../pages/predictions/PredictionsHub";
import styles from "./css/predictionsNavbar.module.css";

export const PredictionsNavbar = () => {
  const navigate = useNavigate();
  return (
    <nav aria-label="Prediction tools" className={styles.buttonContainer}>
      <select
        className={styles.select}
        aria-label="Prediction tools"
        value=""
        onChange={event => { if (event.target.value) navigate(event.target.value); }}
      >
        <option value="">Prediction tools</option>
        <option value="/predictions/hub">Predictions home</option>
        {PRED_SECTIONS.map(section => <option key={section.path} value={section.path}>{section.title}</option>)}
      </select>
    </nav>
  );
};
