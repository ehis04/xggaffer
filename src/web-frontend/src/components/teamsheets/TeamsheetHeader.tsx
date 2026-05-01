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

  return (
    <div className={styles.teamsheetHeaderRoot}>
      <div className={styles.teamsheetHeaderTopRow}>
        {onBack && (
          <button
            className={styles.teamsheetHeaderBackButton}
            onClick={onBack}
            disabled={actionLoading}
          >
            ← Back
          </button>
        )}

        <div className={styles.teamsheetHeaderActions}>
          {!teamsheet.is_trashed && onDuplicate && (
            <button
              className={styles.teamsheetHeaderActionButton}
              onClick={onDuplicate}
              disabled={actionLoading}
            >
              Duplicate
            </button>
          )}

          {!teamsheet.is_trashed && onEdit && (
            <button
              className={styles.teamsheetHeaderActionButton}
              onClick={onEdit}
              disabled={actionLoading}
            >
              Edit
            </button>
          )}

          {!teamsheet.is_trashed && onMoveToTrash && (
            <button
              className={styles.teamsheetHeaderDangerButton}
              onClick={onMoveToTrash}
              disabled={actionLoading}
            >
              {actionLoading ? 'Moving…' : 'Move to Trash'}
            </button>
          )}

          {teamsheet.is_trashed && onRestore && (
            <button
              className={styles.teamsheetHeaderRestoreButton}
              onClick={onRestore}
              disabled={actionLoading}
            >
              {actionLoading ? 'Restoring…' : 'Restore'}
            </button>
          )}

          {teamsheet.is_trashed && onPermanentDelete && (
            <button
              className={styles.teamsheetHeaderDangerButton}
              onClick={onPermanentDelete}
              disabled={actionLoading}
            >
              {actionLoading ? 'Deleting…' : 'Delete Permanently'}
            </button>
          )}
        </div>
      </div>

      {teamsheet.is_trashed && (
        <div className={styles.teamsheetHeaderTrashedBanner}>
          This teamsheet is in trash.
          {teamsheet.trash_expires_at && (
            <span className={styles.teamsheetHeaderTrashedBannerSubtext}>
              {' '}It will be permanently removed after{' '}
              {formatDate(teamsheet.trash_expires_at)} unless restored first.
            </span>
          )}
        </div>
      )}

      <div className={styles.teamsheetHeaderTitleSection}>
        <h1 className={styles.teamsheetHeaderTitle}>{teamsheet.title}</h1>

        {teamsheet.is_template && (
          <span className={styles.teamsheetHeaderTemplateBadge}>Template</span>
        )}

        {teamsheet.is_trashed && (
          <span className={styles.teamsheetHeaderTrashedBadge}>In Trash</span>
        )}
      </div>

      <div className={styles.teamsheetHeaderMeta}>
        <div className={styles.teamsheetHeaderMetaItem}>
          <span className={styles.teamsheetHeaderMetaLabel}>Formation</span>
          <span className={styles.teamsheetHeaderMetaValue}>
            {teamsheet.formation_display}
          </span>
        </div>

        {teamsheet.opponent && (
          <div className={styles.teamsheetHeaderMetaItem}>
            <span className={styles.teamsheetHeaderMetaLabel}>Opponent</span>
            <span className={styles.teamsheetHeaderMetaValue}>{teamsheet.opponent}</span>
          </div>
        )}

        {teamsheet.match_date && (
          <div className={styles.teamsheetHeaderMetaItem}>
            <span className={styles.teamsheetHeaderMetaLabel}>Date</span>
            <span className={styles.teamsheetHeaderMetaValue}>
              {formatDate(teamsheet.match_date)}
            </span>
          </div>
        )}

        <div className={styles.teamsheetHeaderMetaItem}>
          <span className={styles.teamsheetHeaderMetaLabel}>Status</span>
          <span
            className={`${styles.teamsheetHeaderMetaValue} ${
              teamsheet.is_complete
                ? styles.teamsheetHeaderMetaComplete
                : styles.teamsheetHeaderMetaIncomplete
            }`}
          >
            {teamsheet.is_complete ? 'Complete' : `${teamsheet.starter_count}/11`}
          </span>
        </div>
      </div>

      {teamsheet.notes && (
        <div className={styles.teamsheetHeaderNotes}>
          <span className={styles.teamsheetHeaderNotesLabel}>Notes</span>
          <p className={styles.teamsheetHeaderNotesText}>{teamsheet.notes}</p>
        </div>
      )}
    </div>
  );
};

export default TeamsheetHeader;