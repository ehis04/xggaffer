import React from 'react';
import type { PointerEventHandler } from 'react';
import type {
  TacticsBallItem,
  TacticsRenderableBallItem,
} from '../../types/tactics';
import { pitchToSvg } from '../../utils/pitchCoords';

type BoardBallItem = TacticsBallItem | TacticsRenderableBallItem;

interface BoardBallProps {
  item: BoardBallItem;
  isSelected?: boolean;
  onPointerDown?: PointerEventHandler<SVGGElement>;
}

const BoardBall: React.FC<BoardBallProps> = ({
  item,
  isSelected = false,
  onPointerDown,
}) => {
  const { x, y } = pitchToSvg(item.x, item.y);
  const opacity = 'opacity' in item ? item.opacity : 1;

  return (
    <g
      transform={`translate(${x}, ${y})`}
      aria-label="Ball marker"
      onPointerDown={onPointerDown}
      style={{ cursor: onPointerDown ? 'pointer' : 'default', opacity }}
    >
      {isSelected ? (
        <circle
          r={16}
          fill="none"
          stroke="rgba(255, 255, 255, 0.65)"
          strokeWidth={3}
        />
      ) : null}

      <circle
        r={11}
        fill="#ffffff"
        stroke={isSelected ? '#111827' : 'rgba(17, 24, 39, 0.7)'}
        strokeWidth={isSelected ? 3 : 2}
      />

      <path
        d="M 0 -5 L 4 -1 L 2 5 L -2 5 L -4 -1 Z"
        fill="rgba(17, 24, 39, 0.9)"
        style={{ pointerEvents: 'none' }}
      />

      <path
        d="M -7 -2 L -3 -1 M 7 -2 L 3 -1 M -5 6 L -2 3 M 5 6 L 2 3"
        stroke="rgba(17, 24, 39, 0.85)"
        strokeWidth={1.5}
        strokeLinecap="round"
        fill="none"
        style={{ pointerEvents: 'none' }}
      />
    </g>
  );
};

export default BoardBall;