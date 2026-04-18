import React, { useEffect } from 'react';
import PitchCanvas from './PitchCanvas';
import type {
  TacticsBoardFrame,
  TacticsPlaybackStatus,
  TacticsRenderableItem,
} from '../../types/tactics';

interface PlaybackOverlayProps {
  isOpen: boolean;
  boardTitle: string;
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
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(3, 7, 18, 0.94)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: '16px',
          alignItems: 'center',
          padding: '18px 22px',
          borderBottom: '1px solid rgba(255,255,255,0.12)',
          color: '#F8FAFC',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>{boardTitle}</h2>
          <p style={{ margin: '6px 0 0 0', color: 'rgba(248,250,252,0.78)' }}>
            {getStatusLabel(status)} · Frame {sourceFrameIndex}
            {targetFrameIndex !== null ? ` → ${targetFrameIndex}` : ''}
          </p>
        </div>

        <div
          style={{
            display: 'flex',
            gap: '10px',
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          {status === 'playing' ? (
            <button
              type="button"
              onClick={onPause}
                style={{
                padding: '9px 14px',
                minHeight: '44px',
                minWidth: '44px',
                borderRadius: '999px',
                border: '1px solid rgba(255,255,255,0.22)',
                background: '#F8FAFC',
                color: '#111827',
                fontWeight: 700,
                cursor: 'pointer',
                touchAction: 'manipulation',
                }}
            >
              Pause
            </button>
          ) : (
            <button
              type="button"
              onClick={onPlay}
              style={{
                padding: '9px 14px',
                borderRadius: '999px',
                border: '1px solid rgba(255,255,255,0.22)',
                background: '#F8FAFC',
                color: '#111827',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Play
            </button>
          )}

          <button
            type="button"
            onClick={onStop}
            style={{
              padding: '9px 14px',
              borderRadius: '999px',
              border: '1px solid rgba(255,255,255,0.22)',
              background: 'transparent',
              color: '#F8FAFC',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Stop
          </button>

          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '9px 14px',
              borderRadius: '999px',
              border: '1px solid rgba(248,113,113,0.5)',
              background: 'transparent',
              color: '#FCA5A5',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      </div>

      <div
        style={{
          padding: '12px 22px 0 22px',
        }}
      >
        <div
          aria-label="Playback progress"
          style={{
            width: '100%',
            height: '10px',
            borderRadius: '999px',
            background: 'rgba(255,255,255,0.12)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${clampedProgress * 100}%`,
              height: '100%',
              background: '#F8FAFC',
              transition: 'width 80ms linear',
            }}
          />
        </div>
      </div>

      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '22px',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: '1280px',
          }}
        >
          <PitchCanvas
            frame={frame}
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