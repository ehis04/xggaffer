import React from 'react';
import type { PointerEventHandler } from 'react';
import type {
  TacticsBoardItem,
  TacticsRenderablePlayerItem,
} from '../../types/tactics';
import { pitchToSvg } from '../../utils/pitchCoords';

type BoardPlayerMarkerItem = TacticsBoardItem | TacticsRenderablePlayerItem;

interface BoardPlayerMarkerProps {
  item: BoardPlayerMarkerItem;
  isSelected?: boolean;
  isDragging?: boolean;
  onPointerDown?: PointerEventHandler<SVGGElement>;
}

const getTeamColour = (teamSide: BoardPlayerMarkerItem['team_side']) => {
  if (teamSide === 'away') {
    return '#DC2626';
  }

  return '#1E40AF';
};

const getDisplayName = (item: BoardPlayerMarkerItem) => {
  if (item.player_summary?.display_name) {
    return item.player_summary.display_name;
  }

  if (item.player_summary?.full_name) {
    return item.player_summary.full_name;
  }

  if (item.label) {
    return item.label;
  }

  return '';
};

const getShortName = (value: string) => {
  if (!value.trim()) {
    return '';
  }

  const parts = value.trim().split(/\s+/);
  return parts[parts.length - 1];
};

const BoardPlayerMarker: React.FC<BoardPlayerMarkerProps> = ({
  item,
  isSelected = false,
  isDragging = false,
  onPointerDown,
}) => {
  const { x, y } = pitchToSvg(item.x, item.y);
  const teamColour = getTeamColour(item.team_side);
  const displayName = getDisplayName(item);
  const shortName = getShortName(displayName);
  const displayNumber =
    item.shirt_number ??
    item.player_summary?.squad_number ??
    null;
  const opacity = 'opacity' in item ? item.opacity : 1;

  return (
    <g
      transform={`translate(${x}, ${y})`}
      aria-label={`Player marker ${displayName || item.position_label || 'unlabelled'}`}
      onPointerDown={onPointerDown}
      style={{
        cursor: onPointerDown ? (isDragging ? 'grabbing' : 'grab') : 'default',
        opacity: opacity * (isDragging ? 0.72 : 1),
        touchAction: onPointerDown ? 'none' : 'auto',
      }}
    >
      <circle
        r={20}
        fill={teamColour}
        stroke={isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.95)'}
        strokeWidth={isSelected ? 5 : 3}
      />

      {isSelected ? (
        <circle
          r={25}
          fill="none"
          stroke="rgba(255, 255, 255, 0.55)"
          strokeWidth={2}
        />
      ) : null}

      <text
        x={0}
        y={1}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#ffffff"
        fontSize="14"
        fontWeight="700"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {displayNumber ?? ''}
      </text>

      {item.position_label ? (
        <text
          x={0}
          y={-28}
          textAnchor="middle"
          fill="rgba(255, 255, 255, 0.75)"
          fontSize="10"
          fontWeight="600"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          {item.position_label}
        </text>
      ) : null}

      {shortName ? (
        <text
          x={0}
          y={36}
          textAnchor="middle"
          fill={teamColour}
          fontSize="11"
          fontWeight="700"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          {shortName}
        </text>
      ) : null}
    </g>
  );
};

export default BoardPlayerMarker;