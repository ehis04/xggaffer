import React from 'react';
import type { Teamsheet } from '../../types/teamsheet';
import styles from './TeamsheetHeader.module.css';

interface TeamsheetHeaderProps {
  teamsheet: Teamsheet;
  onBack?: () => void;
  onEdit?: () => void;
  onDuplicate?: () => void;
  onMoveToTrash?: () => void;
  onRestore?: () => void;
  onPermanentDelete?: () => void;
  actionLoading?: boolean;
}

const TeamsheetHeader: React.FC<TeamsheetHeaderProps> = ({
  teamsheet,
  onBack,
  onEdit,
  onDuplicate,
  onMoveToTrash,
  onRestore,
  onPermanentDelete,
  actionLoading = false,
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

  const formatExpiry = (dateStr: string | null) => {
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
          <button className={styles.backButton} onClick={onBack} disabled={actionLoading}>
            ← Back
          </button>
        )}

        <div className={styles.actions}>
          {!teamsheet.is_trashed && onDuplicate && (
            <button className={styles.actionButton} onClick={onDuplicate} disabled={actionLoading}>
              Duplicate
            </button>
          )}

          {!teamsheet.is_trashed && onEdit && (
            <button className={styles.actionButton} onClick={onEdit} disabled={actionLoading}>
              Edit
            </button>
          )}

          {!teamsheet.is_trashed && onMoveToTrash && (
            <button className={styles.dangerButton} onClick={onMoveToTrash} disabled={actionLoading}>
              {actionLoading ? 'Moving...' : 'Move to Trash'}
            </button>
          )}

          {teamsheet.is_trashed && onRestore && (
            <button className={styles.restoreButton} onClick={onRestore} disabled={actionLoading}>
              {actionLoading ? 'Restoring...' : 'Restore'}
            </button>
          )}

          {teamsheet.is_trashed && onPermanentDelete && (
            <button
              className={styles.dangerButton}
              onClick={onPermanentDelete}
              disabled={actionLoading}
            >
              {actionLoading ? 'Deleting...' : 'Delete Permanently'}
            </button>
          )}
        </div>
      </div>

      {teamsheet.is_trashed && (
        <div className={styles.trashedBanner}>
          This teamsheet is in trash.
          {teamsheet.trash_expires_at && (
            <span className={styles.trashedBannerSubtext}>
              {' '}It will be permanently removed after {formatExpiry(teamsheet.trash_expires_at)} unless restored first.
            </span>
          )}
        </div>
      )}

      <div className={styles.titleSection}>
        <h1 className={styles.title}>{teamsheet.title}</h1>

        {teamsheet.is_template && (
          <span className={styles.templateBadge}>Template</span>
        )}

        {teamsheet.is_trashed && (
          <span className={styles.trashedBadge}>In Trash</span>
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
          <span
            className={`${styles.metaValue} ${
              teamsheet.is_complete ? styles.complete : styles.incomplete
            }`}
          >
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