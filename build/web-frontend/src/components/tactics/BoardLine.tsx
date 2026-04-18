import React from 'react';
import type { PointerEventHandler } from 'react';
import type {
  TacticsLineItem,
  TacticsRenderableLineItem,
} from '../../types/tactics';
import { pitchToSvg } from '../../utils/pitchCoords';

type BoardLineItem = TacticsLineItem | TacticsRenderableLineItem;

interface BoardLineProps {
  item: BoardLineItem;
  isSelected?: boolean;
  onPointerDown?: PointerEventHandler<SVGGElement>;
}

const getStrokeColour = (teamSide: BoardLineItem['team_side']) => {
  if (teamSide === 'home') {
    return '#1E40AF';
  }

  if (teamSide === 'away') {
    return '#DC2626';
  }

  return '#F8FAFC';
};

const BoardLine: React.FC<BoardLineProps> = ({
  item,
  isSelected = false,
  onPointerDown,
}) => {
  const start = pitchToSvg(item.x, item.y);
  const end = pitchToSvg(item.end_x, item.end_y);
  const stroke = getStrokeColour(item.team_side);
  const centreX = (start.x + end.x) / 2;
  const centreY = (start.y + end.y) / 2;
  const opacity = 'opacity' in item ? item.opacity : 1;

  return (
    <g
      aria-label="Line annotation"
      onPointerDown={onPointerDown}
      style={{ cursor: onPointerDown ? 'pointer' : 'default', opacity }}
    >
      <g transform={`rotate(${item.rotation} ${centreX} ${centreY})`}>
        <line
          x1={start.x}
          y1={start.y}
          x2={end.x}
          y2={end.y}
          stroke="transparent"
          strokeWidth={20}
          strokeLinecap="round"
        />

        {isSelected ? (
          <line
            x1={start.x}
            y1={start.y}
            x2={end.x}
            y2={end.y}
            stroke="rgba(255, 255, 255, 0.45)"
            strokeWidth={8}
            strokeLinecap="round"
          />
        ) : null}

        <line
          x1={start.x}
          y1={start.y}
          x2={end.x}
          y2={end.y}
          stroke={stroke}
          strokeWidth={isSelected ? 5 : 4}
          strokeLinecap="round"
        />
      </g>
    </g>
  );
};

export default BoardLine;