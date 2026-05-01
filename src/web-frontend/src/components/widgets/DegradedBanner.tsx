import styles from './css/DegradedBanner.module.css';

interface DegradedBannerProps {
  reason: string;
  cascade: boolean;
}

export default function DegradedBanner({ reason, cascade }: DegradedBannerProps) {
  const text = cascade
    ? `Upstream data issue — ${reason}`
    : `Model data may be outdated: ${reason}`;

  return <div className={styles.banner}>{text}</div>;
}