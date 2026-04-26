import type { ReactElement } from 'react';
import styles from './css/NullStatePlaceholder.module.css';

type IconVariant = 'bookmark' | 'chart' | 'shield' | 'default';

interface NullStatePlaceholderProps {
  message: string;
  icon?: IconVariant;
}

function BookmarkIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function DefaultIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

const ICONS: Record<IconVariant, () => ReactElement> = {
  bookmark: BookmarkIcon,
  chart: ChartIcon,
  shield: ShieldIcon,
  default: DefaultIcon,
};

export default function NullStatePlaceholder({ message, icon = 'default' }: NullStatePlaceholderProps) {
  const Icon = ICONS[icon];
  return (
    <div className={styles.container}>
      <span className={styles.icon}><Icon /></span>
      <p className={styles.message}>{message}</p>
    </div>
  );
}