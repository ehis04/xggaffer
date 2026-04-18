import React from 'react';
import type {
  TacticsActiveTool,
  TacticsPlaybackStatus,
} from '../../types/tactics';

interface BoardToolbarProps {
  title: string;
  isDirty: boolean;
  isSaving: boolean;
  activeTool: TacticsActiveTool;
  hasDraft: boolean;
  currentFrameIndex: number;
  targetFrameIndex: number | null;
  playbackStatus: TacticsPlaybackStatus;
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
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        gap: '12px',
        alignItems: 'center',
        padding: '16px',
        border: '1px solid #d1d5db',
        borderRadius: '14px',
        marginBottom: '16px',
      }}
    >
      <div>
        <button type="button" onClick={onBack}>
          ← Back to Tactics Boards
        </button>

        <h1 style={{ margin: '12px 0 6px 0' }}>{title}</h1>

        <p style={{ margin: 0 }}>
          {saveStatusLabel}
          {hasDraft ? ' · Draft in progress' : ''}
        </p>

        {exportError ? (
          <p style={{ margin: '6px 0 0 0', color: '#b91c1c' }}>
            {exportError}
          </p>
        ) : null}
      </div>

      <div
        style={{
          display: 'flex',
          gap: '10px',
          alignItems: 'center',
          flexWrap: 'wrap',
          justifyContent: 'flex-end',
        }}
      >
        <span
          style={{
            border: '1px solid #9ca3af',
            borderRadius: '999px',
            padding: '6px 10px',
            fontSize: '0.95rem',
            whiteSpace: 'nowrap',
          }}
        >
          {toolLabel}
        </span>

        <span
          style={{
            border: '1px solid #9ca3af',
            borderRadius: '999px',
            padding: '6px 10px',
            fontSize: '0.95rem',
            whiteSpace: 'nowrap',
          }}
        >
          {saveStatusLabel}
        </span>

        <span
          style={{
            border: '1px solid #9ca3af',
            borderRadius: '999px',
            padding: '6px 10px',
            fontSize: '0.95rem',
            whiteSpace: 'nowrap',
          }}
        >
          {playbackLabel}
        </span>

        <span
          style={{
            border: '1px solid #9ca3af',
            borderRadius: '999px',
            padding: '6px 10px',
            fontSize: '0.95rem',
            whiteSpace: 'nowrap',
          }}
        >
          {exportStatusLabel}
        </span>

        <button
          type="button"
          onClick={onUndo}
          disabled={!canUndo}
        >
          Undo
        </button>

        <button
          type="button"
          onClick={onRedo}
          disabled={!canRedo}
        >
          Redo
        </button>

        {isPlaying ? (
          <button
            type="button"
            onClick={onPause}
            disabled={!canPlay}
          >
            Pause
          </button>
        ) : (
          <button
            type="button"
            onClick={onPlay}
            disabled={!canPlay}
          >
            Play
          </button>
        )}

        <button
          type="button"
          onClick={onStop}
          disabled={!canPlay}
        >
          Stop
        </button>

        <button
          type="button"
          onClick={onOpenPresentation}
          disabled={!canPlay || isPresentationOpen}
        >
          {isPresentationOpen ? 'Presentation Open' : 'Presentation Mode'}
        </button>

        <button
          type="button"
          onClick={onExportPng}
          disabled={!canExportPng}
        >
          {isExportingPng ? 'Exporting...' : 'Export PNG'}
        </button>

        <button
          type="button"
          onClick={onSave}
          disabled={!canSave}
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
};

export default BoardToolbar;