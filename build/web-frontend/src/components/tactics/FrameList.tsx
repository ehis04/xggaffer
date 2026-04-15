import React, { useMemo } from 'react';
import type { TacticsBoardFrame } from '../../types/tactics';

interface FrameListProps {
  frames: TacticsBoardFrame[];
  activeFrameIndex: number;
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
  isMutating = false,
  onSelectFrame,
  onAddFrame,
  onDuplicateFrame,
  onDeleteFrame,
}) => {
  const orderedFrames = useMemo(() => sortFrames(frames), [frames]);

  return (
    <section
      aria-label="Frames"
      style={{
        border: '1px solid #d1d5db',
        borderRadius: '14px',
        padding: '16px',
        marginBottom: '16px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: '12px',
          alignItems: 'center',
          marginBottom: '14px',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h2 style={{ margin: 0 }}>Frames</h2>
          <p style={{ margin: '6px 0 0 0', color: '#4b5563' }}>
            Select a frame to edit, or duplicate one to create animation continuity.
          </p>
        </div>

        <button
          type="button"
          onClick={onAddFrame}
          disabled={isMutating}
          style={{
            padding: '9px 14px',
            borderRadius: '999px',
            border: '1px solid #111827',
            background: '#111827',
            color: '#ffffff',
            fontWeight: 600,
            cursor: isMutating ? 'default' : 'pointer',
          }}
        >
          {isMutating ? 'Working...' : 'Add frame'}
        </button>
      </div>

      {orderedFrames.length === 0 ? (
        <div
          style={{
            padding: '14px',
            border: '1px dashed #9ca3af',
            borderRadius: '10px',
          }}
        >
          <p style={{ margin: 0 }}>No frames available.</p>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gap: '10px',
          }}
        >
          {orderedFrames.map((frame) => {
            const isActive = frame.frame_index === activeFrameIndex;

            return (
              <div
                key={frame.id}
                style={{
                  border: isActive ? '2px solid #111827' : '1px solid #d1d5db',
                  borderRadius: '12px',
                  padding: '12px',
                  background: isActive ? 'rgba(17, 24, 39, 0.04)' : '#ffffff',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: '10px',
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => onSelectFrame(frame.frame_index)}
                    disabled={isMutating}
                    aria-pressed={isActive}
                    style={{
                      flex: 1,
                      minWidth: '220px',
                      textAlign: 'left',
                      background: 'transparent',
                      border: 'none',
                      padding: 0,
                      cursor: isMutating ? 'default' : 'pointer',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        gap: '8px',
                        alignItems: 'center',
                        marginBottom: '6px',
                        flexWrap: 'wrap',
                      }}
                    >
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          minWidth: '32px',
                          height: '32px',
                          padding: '0 10px',
                          borderRadius: '999px',
                          border: '1px solid #9ca3af',
                          fontWeight: 700,
                          background: isActive ? '#111827' : '#ffffff',
                          color: isActive ? '#ffffff' : '#111827',
                        }}
                      >
                        {frame.frame_index}
                      </span>

                      <strong>{getFrameTitle(frame)}</strong>

                      {isActive ? (
                        <span
                          style={{
                            border: '1px solid #111827',
                            borderRadius: '999px',
                            padding: '4px 8px',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                          }}
                        >
                          Active
                        </span>
                      ) : null}
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        gap: '12px',
                        flexWrap: 'wrap',
                        color: '#4b5563',
                        fontSize: '0.95rem',
                      }}
                    >
                      <span>{frame.items.length} item{frame.items.length === 1 ? '' : 's'}</span>
                      <span>{getDurationLabel(frame.duration_ms)}</span>
                      {frame.notes.trim() ? <span>Has notes</span> : null}
                    </div>
                  </button>

                  <div
                    style={{
                      display: 'flex',
                      gap: '8px',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => onDuplicateFrame(frame)}
                      disabled={isMutating}
                      style={{
                        padding: '8px 12px',
                        borderRadius: '999px',
                        border: '1px solid #9ca3af',
                        background: '#ffffff',
                        fontWeight: 600,
                        cursor: isMutating ? 'default' : 'pointer',
                      }}
                    >
                      Duplicate
                    </button>

                    {onDeleteFrame ? (
                      <button
                        type="button"
                        onClick={() => onDeleteFrame(frame)}
                        disabled={isMutating || orderedFrames.length <= 1}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '999px',
                          border: '1px solid #b91c1c',
                          background: '#ffffff',
                          color: '#b91c1c',
                          fontWeight: 600,
                          cursor:
                            isMutating || orderedFrames.length <= 1
                              ? 'default'
                              : 'pointer',
                        }}
                      >
                        Delete
                      </button>
                    ) : null}
                  </div>
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