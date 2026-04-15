import React from 'react';
import type { PointerEventHandler } from 'react';
import type {
  TacticsRenderableTextItem,
  TacticsTextItem,
} from '../../types/tactics';
import { pitchToSvg } from '../../utils/pitchCoords';

type BoardTextItem = TacticsTextItem | TacticsRenderableTextItem;

interface BoardTextLabelProps {
  item: BoardTextItem;
  isSelected?: boolean;
  onPointerDown?: PointerEventHandler<SVGGElement>;
}

const BoardTextLabel: React.FC<BoardTextLabelProps> = ({
  item,
  isSelected = false,
  onPointerDown,
}) => {
  const { x, y } = pitchToSvg(item.x, item.y);
  const label = item.label.trim();
  const opacity = 'opacity' in item ? item.opacity : 1;

  return (
    <g
      transform={`translate(${x}, ${y}) rotate(${item.rotation})`}
      aria-label={`Text annotation ${label}`}
      onPointerDown={onPointerDown}
      style={{ cursor: onPointerDown ? 'pointer' : 'default', opacity }}
    >
      <rect
        x={-50}
        y={-16}
        width={100}
        height={32}
        rx={8}
        fill={isSelected ? 'rgba(17, 24, 39, 0.9)' : 'rgba(17, 24, 39, 0.72)'}
        stroke={isSelected ? '#F8FAFC' : 'rgba(255, 255, 255, 0.25)'}
        strokeWidth={isSelected ? 2.5 : 1.5}
      />

      <text
        x={0}
        y={1}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#F8FAFC"
        fontSize="14"
        fontWeight="700"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {label}
      </text>
    </g>
  );
};

export default BoardTextLabel;