import type { TrainingSessionStatus } from '../../types/training';
import styles from './css/TrainingComponents.module.css';

interface Props {
  status: TrainingSessionStatus;
}

const labels: Record<TrainingSessionStatus, string> = {
  draft: 'Draft',
  published: 'Published',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

export const SessionStatusBadge = ({ status }: Props) => (
  <span className={`${styles.statusBadge} ${styles[status]}`}>
    {labels[status]}
  </span>
);

export default SessionStatusBadge;
