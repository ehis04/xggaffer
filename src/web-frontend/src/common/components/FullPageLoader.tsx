import styles from "./css/FullPageLoader.module.css";

const DEFAULT_LABEL = "Loading";

interface FullPageLoaderProps {
  label?: string;
}

export function FullPageLoader({ label = DEFAULT_LABEL }: FullPageLoaderProps) {
  return (
    <div className={styles.overlay} role="status">
      <div className={styles.spinnerRing} aria-hidden="true" />
      <span className={styles.srOnly}>{label}</span>
    </div>
  );
}