import styles from "./css/InlineRetry.module.css";

const DEFAULT_MESSAGE = "Failed to load";
const RETRY_LABEL = "Retry";
const RETRYING_LABEL = "Retrying...";

interface InlineRetryProps {
  message?: string;
  onRetry: () => void;
  retrying?: boolean;
}

export function InlineRetry({
  message = DEFAULT_MESSAGE,
  onRetry,
  retrying = false,
}: InlineRetryProps) {
  return (
    <div className={styles.container} role="alert">
      <span className={styles.message}>{message}</span>
      <button
        type="button"
        className={styles.retryButton}
        onClick={onRetry}
        disabled={retrying}
      >
        {retrying ? RETRYING_LABEL : RETRY_LABEL}
      </button>
    </div>
  );
}