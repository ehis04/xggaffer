import React, { useEffect } from 'react';
import PitchCanvas from './PitchCanvas';
import styles from './PlaybackOverlay.module.css';
import type {
  TacticsBoardFrame,
  TacticsPitchOrientation,
  TacticsPlaybackStatus,
  TacticsRenderableItem,
} from '../../types/tactics';

interface PlaybackOverlayProps {
  isOpen: boolean;
  boardTitle: string;
  pitchOrientation: TacticsPitchOrientation;
  frame: TacticsBoardFrame;
  renderItems: TacticsRenderableItem[];
  status: TacticsPlaybackStatus;
  sourceFrameIndex: number;
  targetFrameIndex: number | null;
  progress: number;
  onPlay: () => void;
  onPause: () => void;
  onStop: () => void;
  onClose: () => void;
}

const clampProgress = (value: number): number => {
  if (Number.isNaN(value)) {
    return 0;
  }

  if (value <= 0) {
    return 0;
  }

  if (value >= 1) {
    return 1;
  }

  return value;
};

const getStatusLabel = (status: TacticsPlaybackStatus): string => {
  switch (status) {
    case 'playing':
      return 'Playing';
    case 'paused':
      return 'Paused';
    default:
      return 'Ready';
  }
};



const PlaybackOverlay: React.FC<PlaybackOverlayProps> = ({
  isOpen,
  boardTitle,
  pitchOrientation,
  frame,
  renderItems,
  status,
  sourceFrameIndex,
  targetFrameIndex,
  progress,
  onPlay,
  onPause,
  onStop,
  onClose,
}) => {
  const clampedProgress = clampProgress(progress);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Presentation playback"
      className={styles.overlay}
    >
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>{boardTitle}</h2>
          <p className={styles.subtitle}>
            {getStatusLabel(status)} · Frame {sourceFrameIndex}
            {targetFrameIndex !== null ? ` → ${targetFrameIndex}` : ''}
          </p>
        </div>

        <div className={styles.controls}>
          {status === 'playing' ? (
            <button
              type="button"
              onClick={onPause}
              className={styles.primaryControl}
            >
              Pause
            </button>
          ) : (
            <button
              type="button"
              onClick={onPlay}
              className={styles.primaryControl}
            >
              Play
            </button>
          )}

          <button
            type="button"
            onClick={onStop}
            className={styles.secondaryControl}
          >
            Stop
          </button>

          <button
            type="button"
            onClick={onClose}
            className={styles.closeControl}
          >
            Close
          </button>
        </div>
      </div>

      <div className={styles.progressWrap}>
        <div
          aria-label="Playback progress"
          className={styles.progressTrack}
        >
          <div
            className={styles.progressFill}
            style={{ width: `${clampedProgress * 100}%` }}
          />
        </div>
      </div>

      <div className={styles.canvasRegion}>
        <div className={styles.canvasWrap}>
          <PitchCanvas
            frame={frame}
            pitchOrientation={pitchOrientation}
            renderItems={renderItems}
            isPlaybackMode
            selectedItemId={null}
            draftItem={null}
          />
        </div>
      </div>
    </div>
  );
};

export default PlaybackOverlay;