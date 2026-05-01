import { StatusBlock } from "../../common/components/StatusBlock";
import styles from "./css/AppErrorPage.module.css";

interface AppErrorPageProps {
  error?: unknown;
  onReset?: () => void;
}

export function AppErrorPage({ onReset }: AppErrorPageProps) {  const actions = (
    <div className={styles.actions}>
      {onReset && (
        <button type="button" className={styles.resetButton} onClick={onReset}>
          Try Again
        </button>
      )}
      <button type="button" className={styles.homeButton} onClick={() => { window.location.href = "/social"; }}>
        Go Home
      </button>
    </div>
  );

  return (
    <div className={styles.page}>
      <StatusBlock variant="error" actions={actions} />
    </div>
  );
}