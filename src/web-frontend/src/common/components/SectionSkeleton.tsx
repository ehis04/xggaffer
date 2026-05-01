import styles from "./css/SectionSkeleton.module.css";

const DEFAULT_ROWS = 3;
const DEFAULT_HEIGHT = "48px";
const DEFAULT_GAP = "12px";

interface SectionSkeletonProps {
  rows?: number;
  height?: string;
  gap?: string;
}

export function SectionSkeleton({
  rows = DEFAULT_ROWS,
  height = DEFAULT_HEIGHT,
  gap = DEFAULT_GAP,
}: SectionSkeletonProps) {
  return (
    <div className={styles.container} style={{ gap }} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className={styles.bar} style={{ height }} />
      ))}
    </div>
  );
}