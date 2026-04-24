import { useNavigate } from "react-router-dom";
import { useCountdown } from "../../hooks/useCountdown";
import { StatusBlock } from "../../common/components/StatusBlock";
import styles from "./css/NotFoundPage.module.css";

const COUNTDOWN_START = 5;
const HOME_PATH = "/";

export function NotFoundPage() {
  const navigate = useNavigate();
  const count = useCountdown(COUNTDOWN_START, () => navigate(HOME_PATH));

  const actions = (
    <div className={styles.actions}>
      <button type="button" className={styles.homeButton} onClick={() => navigate(HOME_PATH)}>
        Go Home
      </button>
      <span className={styles.countdown}>Redirecting in {count}s</span>
    </div>
  );

  return (
    <div className={styles.page}>
      <StatusBlock variant="not-found" actions={actions} />
    </div>
  );
}