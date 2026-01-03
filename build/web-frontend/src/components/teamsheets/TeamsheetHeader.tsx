import React from 'react';
import type { Teamsheet } from '../../types/teamsheet';
import styles from './TeamsheetHeader.module.css';

interface TeamsheetHeaderProps {
  teamsheet: Teamsheet;
  onBack?: () => void;
  onEdit?: () => void;
  onDuplicate?: () => void;
}

const TeamsheetHeader: React.FC<TeamsheetHeaderProps> = ({
  teamsheet,
  onBack,
  onEdit,
  onDuplicate,
}) => {
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('en-IE', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div className={styles.header}>
      <div className={styles.topRow}>
        {onBack && (
          <button className={styles.backButton} onClick={onBack}>
            ← Back
          </button>
        )}
        <div className={styles.actions}>
          {onDuplicate && (
            <button className={styles.actionButton} onClick={onDuplicate}>
              Duplicate
            </button>
          )}
          {onEdit && (
            <button className={styles.actionButton} onClick={onEdit}>
              Edit
            </button>
          )}
        </div>
      </div>

      <div className={styles.titleSection}>
        <h1 className={styles.title}>{teamsheet.title}</h1>
        {teamsheet.is_template && (
          <span className={styles.templateBadge}>Template</span>
        )}
      </div>

      <div className={styles.meta}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Formation</span>
          <span className={styles.metaValue}>{teamsheet.formation_display}</span>
        </div>

        {teamsheet.opponent && (
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Opponent</span>
            <span className={styles.metaValue}>{teamsheet.opponent}</span>
          </div>
        )}

        {teamsheet.match_date && (
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Date</span>
            <span className={styles.metaValue}>{formatDate(teamsheet.match_date)}</span>
          </div>
        )}

        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Status</span>
          <span className={`${styles.metaValue} ${teamsheet.is_complete ? styles.complete : styles.incomplete}`}>
            {teamsheet.is_complete ? 'Complete' : `${teamsheet.starter_count}/11`}
          </span>
        </div>
      </div>

      {teamsheet.notes && (
        <div className={styles.notes}>
          <span className={styles.notesLabel}>Notes:</span>
          <p className={styles.notesText}>{teamsheet.notes}</p>
        </div>
      )}
    </div>
  );
};

export default TeamsheetHeader;