import React from 'react';
import type {
  TacticsActiveTool,
  TacticsPlaybackStatus,
} from '../../types/tactics';
import styles from './BoardToolbar.module.css';

interface BoardToolbarProps {
  title: string;
  isDirty: boolean;
  isSaving: boolean;
  activeTool: TacticsActiveTool;
  hasDraft: boolean;
  currentFrameIndex: number;
  targetFrameIndex: number | null;
  playbackStatus: TacticsPlaybackStatus;
  isAnimatedBoard: boolean;
  canPlay: boolean;
  isPresentationOpen: boolean;
  isExportingPng: boolean;
  exportError: string | null;
  canUndo: boolean;
  canRedo: boolean;
  onBack: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onSave: () => void;
  canSave: boolean;
  onPlay: () => void;
  onPause: () => void;
  onStop: () => void;
  onOpenPresentation: () => void;
  onExportPng: () => void;
  canExportPng: boolean;
}

const getSaveStatusLabel = (isDirty: boolean, isSaving: boolean) => {
  if (isSaving) {
    return 'Saving changes';
  }

  if (isDirty) {
    return 'Unsaved player movement';
  }

  return 'All saved';
};

const getToolLabel = (tool: TacticsActiveTool) => {
  switch (tool) {
    case 'select':
      return 'Select mode';
    case 'ball':
      return 'Ball tool';
    case 'arrow':
      return 'Arrow tool';
    case 'line':
      return 'Line tool';
    case 'zone':
      return 'Zone tool';
    case 'text':
      return 'Text tool';
    default:
      return 'Editor';
  }
};

const getPlaybackLabel = (
  playbackStatus: TacticsPlaybackStatus,
  currentFrameIndex: number,
  targetFrameIndex: number | null
) => {
  const frameLabel =
    targetFrameIndex === null
      ? `Frame ${currentFrameIndex}`
      : `Frame ${currentFrameIndex} → ${targetFrameIndex}`;

  switch (playbackStatus) {
    case 'playing':
      return `Playing · ${frameLabel}`;
    case 'paused':
      return `Paused · ${frameLabel}`;
    default:
      return `Ready · ${frameLabel}`;
  }
};

const getExportStatusLabel = (isExportingPng: boolean) => {
  return isExportingPng ? 'Exporting PNG' : 'PNG export ready';
};

const BoardToolbar: React.FC<BoardToolbarProps> = ({
  title,
  isDirty,
  isSaving,
  activeTool,
  hasDraft,
  currentFrameIndex,
  targetFrameIndex,
  playbackStatus,
  isAnimatedBoard,
  canPlay,
  isPresentationOpen,
  isExportingPng,
  exportError,
  canUndo,
  canRedo,
  onBack,
  onUndo,
  onRedo,
  onSave,
  canSave,
  onPlay,
  onPause,
  onStop,
  onOpenPresentation,
  onExportPng,
  canExportPng,
}) => {
  const saveStatusLabel = getSaveStatusLabel(isDirty, isSaving);
  const toolLabel = getToolLabel(activeTool);
  const playbackLabel = getPlaybackLabel(
    playbackStatus,
    currentFrameIndex,
    targetFrameIndex
  );
  const exportStatusLabel = getExportStatusLabel(isExportingPng);
  const isPlaying = playbackStatus === 'playing';

  return (
    <section className={styles.toolbar} aria-label="Board controls">
      <div className={styles.toolbarHeader}>
        <button type="button" onClick={onBack} className={styles.backButton}>
          ← Back to Tactics Boards
        </button>

        <h1 className={styles.title}>{title}</h1>

        <p className={styles.subtitle}>
          {saveStatusLabel}
          {hasDraft ? ' · Draft in progress' : ''}
        </p>

        {exportError ? (
          <p className={styles.errorText}>{exportError}</p>
        ) : null}
      </div>

      <div className={styles.metaRow}>
        <span className={styles.metaChip}>
          {toolLabel}
        </span>
        <span className={styles.metaChip}>
          {saveStatusLabel}
        </span>
        <span className={styles.metaChip}>
          {playbackLabel}
        </span>
        <span className={styles.metaChip}>
          {exportStatusLabel}
        </span>
      </div>

      <div className={styles.actionsRow}>
        <div className={styles.actionGroup} aria-label="History controls">
          <span className={styles.groupLabel}>Edit</span>
          <button type="button" onClick={onUndo} disabled={!canUndo} className={styles.secondaryButton}>
            Undo
          </button>
          <button type="button" onClick={onRedo} disabled={!canRedo} className={styles.secondaryButton}>
            Redo
          </button>
        </div>

        <span className={styles.actionDivider} aria-hidden="true">||</span>

        <div className={styles.actionGroup} aria-label="Playback controls">
          <span className={styles.groupLabel}>Playback</span>
          {isAnimatedBoard ? (
            <>
              {isPlaying ? (
                <button type="button" onClick={onPause} disabled={!canPlay} className={styles.secondaryButton}>
                  Pause
                </button>
              ) : (
                <button type="button" onClick={onPlay} disabled={!canPlay} className={styles.secondaryButton}>
                  Play
                </button>
              )}

              <button type="button" onClick={onStop} disabled={!canPlay} className={styles.secondaryButton}>
                Stop
              </button>

              <button
                type="button"
                onClick={onOpenPresentation}
                disabled={!canPlay || isPresentationOpen}
                className={styles.secondaryButton}
              >
                {isPresentationOpen ? 'Presentation Open' : 'Presentation'}
              </button>
            </>
          ) : (
            <span className={styles.staticNotice}>Static board: playback unavailable</span>
          )}
        </div>

        <span className={styles.actionDivider} aria-hidden="true">||</span>

        <div className={styles.actionGroup} aria-label="Output controls">
          <span className={styles.groupLabel}>Output</span>
          <button
            type="button"
            onClick={onExportPng}
            disabled={!canExportPng}
            className={styles.secondaryButton}
          >
            {isExportingPng ? 'Exporting...' : 'Export PNG'}
          </button>

          <button
            type="button"
            onClick={onSave}
            disabled={!canSave}
            className={styles.primaryButton}
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </section>
  );
};

export default BoardToolbar;