import React, { useMemo } from 'react';
import type { TacticsBoardFrame } from '../../types/tactics';
import styles from './FrameList.module.css';

interface FrameListProps {
  frames: TacticsBoardFrame[];
  activeFrameIndex: number;
  allowAnimationActions?: boolean;
  isMutating?: boolean;
  onSelectFrame: (frameIndex: number) => void;
  onAddFrame: () => void;
  onDuplicateFrame: (frame: TacticsBoardFrame) => void;
  onDeleteFrame?: (frame: TacticsBoardFrame) => void;
}

const sortFrames = (frames: TacticsBoardFrame[]): TacticsBoardFrame[] => {
  return [...frames].sort((left, right) => {
    if (left.frame_index !== right.frame_index) {
      return left.frame_index - right.frame_index;
    }

    return left.id - right.id;
  });
};

const getFrameTitle = (frame: TacticsBoardFrame): string => {
  const trimmedLabel = frame.label.trim();
  if (trimmedLabel) {
    return trimmedLabel;
  }

  return `Frame ${frame.frame_index}`;
};

const getDurationLabel = (durationMs: number): string => {
  if (durationMs % 1000 === 0) {
    return `${durationMs / 1000}s`;
  }

  return `${(durationMs / 1000).toFixed(1)}s`;
};

const FrameList: React.FC<FrameListProps> = ({
  frames,
  activeFrameIndex,
  allowAnimationActions = true,
  isMutating = false,
  onSelectFrame,
  onAddFrame,
  onDuplicateFrame,
  onDeleteFrame,
}) => {
  const orderedFrames = useMemo(() => sortFrames(frames), [frames]);

  return (
    <section aria-label="Frames" className={styles.framePanel}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Frames</h2>
          <p className={styles.subtitle}>
            {allowAnimationActions
              ? 'Select a frame to edit, or duplicate one to create animation continuity.'
              : 'Static boards use a fixed frame setup. Frame animation controls are disabled.'}
          </p>
        </div>

        {allowAnimationActions ? (
          <button
            type="button"
            onClick={onAddFrame}
            disabled={isMutating}
            className={styles.primaryAction}
          >
            {isMutating ? 'Working...' : 'Add frame'}
          </button>
        ) : (
          <span className={styles.staticTag}>
            Static mode
          </span>
        )}
      </div>

      {orderedFrames.length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.emptyText}>No frames available.</p>
        </div>
      ) : (
        <div className={styles.frameGrid}>
          {orderedFrames.map((frame) => {
            const isActive = frame.frame_index === activeFrameIndex;

            return (
              <div
                key={frame.id}
                className={isActive ? `${styles.frameCard} ${styles.frameCardActive}` : styles.frameCard}
              >
                <div className={styles.frameCardHeader}>
                  <button
                    type="button"
                    onClick={() => onSelectFrame(frame.frame_index)}
                    disabled={isMutating}
                    aria-pressed={isActive}
                    className={styles.frameSelectButton}
                  >
                    <div className={styles.frameIdentity}>
                      <span className={isActive ? `${styles.frameIndex} ${styles.frameIndexActive}` : styles.frameIndex}>
                        {frame.frame_index}
                      </span>

                      <strong className={styles.frameName}>{getFrameTitle(frame)}</strong>

                      {isActive ? (
                        <span className={styles.activeBadge}>
                          Active
                        </span>
                      ) : null}
                    </div>

                    <div className={styles.frameMetaRow}>
                      <span>{frame.items.length} item{frame.items.length === 1 ? '' : 's'}</span>
                      <span>{getDurationLabel(frame.duration_ms)}</span>
                      {frame.notes.trim() ? <span>Has notes</span> : null}
                    </div>
                  </button>

                  {allowAnimationActions ? (
                    <div className={styles.frameActions}>
                      <button
                        type="button"
                        onClick={() => onDuplicateFrame(frame)}
                        disabled={isMutating}
                        className={styles.secondaryAction}
                      >
                        Duplicate
                      </button>

                      {onDeleteFrame ? (
                        <button
                          type="button"
                          onClick={() => onDeleteFrame(frame)}
                          disabled={isMutating || orderedFrames.length <= 1}
                          className={styles.dangerAction}
                        >
                          Delete
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};

export default FrameList;