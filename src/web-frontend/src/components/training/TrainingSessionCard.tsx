import type { TrainingSessionListItem } from '../../types/training';
import { SessionStatusBadge } from './SessionStatusBadge';
import styles from './css/TrainingComponents.module.css';

interface Props {
  session: TrainingSessionListItem;
  active?: boolean;
  onSelect: () => void;
}

const formatDateTime = (value: string) =>
  new Date(value).toLocaleString('en-IE', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });

export const TrainingSessionCard = ({ session, active = false, onSelect }: Props) => (
  <button
    type="button"
    className={`${styles.sessionCard}${active ? ' ' + styles.sessionCardActive : ''}`}
    onClick={onSelect}
  >
    <div className={styles.cardHeader}>
      <h3 className={styles.cardTitle}>{session.title}</h3>
      <SessionStatusBadge status={session.status} />
    </div>
    <div className={styles.cardMeta}>
      <span>{formatDateTime(session.start_datetime)}</span>
      <span>{session.session_type_display}</span>
      <span>{session.assigned_player_count} players</span>
      {session.status === 'completed' && (
        <span>{session.attended_count}/{session.assigned_player_count} attended</span>
      )}
    </div>
    {session.main_objective && (
      <p className={styles.cardObjective}>{session.main_objective}</p>
    )}
  </button>
);

export default TrainingSessionCard;
