import React from 'react';
import type { PointerEventHandler } from 'react';
import type {
  TacticsRenderableZoneItem,
  TacticsZoneItem,
} from '../../types/tactics';
import { pitchToSvg } from '../../utils/pitchCoords';

type BoardZoneItem = TacticsZoneItem | TacticsRenderableZoneItem;

interface BoardZoneProps {
  item: BoardZoneItem;
  isSelected?: boolean;
  onPointerDown?: PointerEventHandler<SVGGElement>;
}

const getZoneColours = (teamSide: BoardZoneItem['team_side']) => {
  if (teamSide === 'home') {
    return {
      fill: 'rgba(30, 64, 175, 0.18)',
      stroke: '#60A5FA',
    };
  }

  if (teamSide === 'away') {
    return {
      fill: 'rgba(220, 38, 38, 0.18)',
      stroke: '#F87171',
    };
  }

  return {
    fill: 'rgba(255, 255, 255, 0.14)',
    stroke: '#F8FAFC',
  };
};

const BoardZone: React.FC<BoardZoneProps> = ({
  item,
  isSelected = false,
  onPointerDown,
}) => {
  const origin = pitchToSvg(item.x, item.y);
  const farCorner = pitchToSvg(item.x + item.width, item.y + item.height);

  const left = Math.min(origin.x, farCorner.x);
  const top = Math.min(origin.y, farCorner.y);
  const width = Math.abs(farCorner.x - origin.x);
  const height = Math.abs(farCorner.y - origin.y);

  const centreX = left + (width / 2);
  const centreY = top + (height / 2);

  const colours = getZoneColours(item.team_side);
  const opacity = 'opacity' in item ? item.opacity : 1;

  return (
    <g
      aria-label="Zone annotation"
      onPointerDown={onPointerDown}
      style={{ cursor: onPointerDown ? 'pointer' : 'default', opacity }}
    >
      <g transform={`rotate(${item.rotation} ${centreX} ${centreY})`}>
        <rect
          x={left}
          y={top}
          width={width}
          height={height}
          fill="transparent"
          stroke="transparent"
          strokeWidth={18}
        />

        {isSelected ? (
          <rect
            x={left}
            y={top}
            width={width}
            height={height}
            fill="none"
            stroke="rgba(255, 255, 255, 0.5)"
            strokeWidth={5}
            rx={10}
          />
        ) : null}

        <rect
          x={left}
          y={top}
          width={width}
          height={height}
          fill={colours.fill}
          stroke={colours.stroke}
          strokeWidth={isSelected ? 3 : 2}
          strokeDasharray="10 8"
          rx={10}
        />
      </g>
    </g>
  );
};

export default BoardZone;