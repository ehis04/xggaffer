import React from 'react';
import type { PointerEventHandler } from 'react';
import type {
  TacticsArrowItem,
  TacticsRenderableArrowItem,
} from '../../types/tactics';
import { pitchToSvg } from '../../utils/pitchCoords';

type BoardArrowItem = TacticsArrowItem | TacticsRenderableArrowItem;

interface BoardArrowProps {
  item: BoardArrowItem;
  isSelected?: boolean;
  onPointerDown?: PointerEventHandler<SVGGElement>;
}

const getStrokeColour = (teamSide: BoardArrowItem['team_side']) => {
  if (teamSide === 'home') {
    return '#1E40AF';
  }

  if (teamSide === 'away') {
    return '#DC2626';
  }

  return '#F8FAFC';
};

const getArrowHeadPoints = (
  startX: number,
  startY: number,
  endX: number,
  endY: number,
  headLength = 16,
  headWidth = 10
) => {
  const dx = endX - startX;
  const dy = endY - startY;
  const length = Math.hypot(dx, dy) || 1;

  const ux = dx / length;
  const uy = dy / length;

  const baseX = endX - (ux * headLength);
  const baseY = endY - (uy * headLength);

  const perpX = -uy;
  const perpY = ux;

  const leftX = baseX + (perpX * headWidth);
  const leftY = baseY + (perpY * headWidth);
  const rightX = baseX - (perpX * headWidth);
  const rightY = baseY - (perpY * headWidth);

  return `${endX},${endY} ${leftX},${leftY} ${rightX},${rightY}`;
};

const BoardArrow: React.FC<BoardArrowProps> = ({
  item,
  isSelected = false,
  onPointerDown,
}) => {
  const start = pitchToSvg(item.x, item.y);
  const end = pitchToSvg(item.end_x, item.end_y);
  const stroke = getStrokeColour(item.team_side);
  const arrowHeadPoints = getArrowHeadPoints(start.x, start.y, end.x, end.y);
  const centreX = (start.x + end.x) / 2;
  const centreY = (start.y + end.y) / 2;
  const opacity = 'opacity' in item ? item.opacity : 1;

  return (
    <g
      aria-label="Arrow annotation"
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
          strokeWidth={22}
          strokeLinecap="round"
        />

        {isSelected ? (
          <>
            <line
              x1={start.x}
              y1={start.y}
              x2={end.x}
              y2={end.y}
              stroke="rgba(255, 255, 255, 0.45)"
              strokeWidth={9}
              strokeLinecap="round"
            />
            <polygon
              points={arrowHeadPoints}
              fill="rgba(255, 255, 255, 0.45)"
            />
          </>
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

        <polygon
          points={arrowHeadPoints}
          fill={stroke}
        />
      </g>
    </g>
  );
};

export default BoardArrow;