import React, { useState, useRef } from 'react';
import type { TeamsheetPlayer } from '../../types/teamsheet';

interface PlayerMarkerProps {
  player: TeamsheetPlayer;
  x: number;
  y: number;
  isSelected?: boolean;
  onClick?: () => void;
  onDragEnd?: (x: number, y: number) => void;
  draggable?: boolean;
}

const getPositionColor = (position: string): string => {
  if (position === 'GK') return '#f59e0b';
  if (['CB', 'RB', 'LB', 'RWB', 'LWB'].includes(position)) return '#3b82f6';
  if (['CM', 'CDM', 'CAM', 'RM', 'LM'].includes(position)) return '#22c55e';
  if (['ST', 'CF', 'RW', 'LW'].includes(position)) return '#ef4444';
  return '#6b7280';
};

const PlayerMarker: React.FC<PlayerMarkerProps> = ({
  player,
  x,
  y,
  isSelected = false,
  onClick,
  onDragEnd,
  draggable = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragPos, setDragPos] = useState({ x, y });
  const svgRef = useRef<SVGGElement>(null);

  const currentX = isDragging ? dragPos.x : x;
  const currentY = isDragging ? dragPos.y : y;
  const color = getPositionColor(player.position_label);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!draggable) return;
    e.preventDefault();
    setIsDragging(true);
    setDragPos({ x, y });

    const svg = svgRef.current?.ownerSVGElement;
    if (!svg) return;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const pt = svg.createSVGPoint();
      pt.x = moveEvent.clientX;
      pt.y = moveEvent.clientY;
      const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
      setDragPos({ x: svgP.x, y: svgP.y });
    };

    const handleMouseUp = (upEvent: MouseEvent) => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      setIsDragging(false);

      const pt = svg.createSVGPoint();
      pt.x = upEvent.clientX;
      pt.y = upEvent.clientY;
      const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
      onDragEnd?.(svgP.x, svgP.y);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <g
      ref={svgRef}
      transform={`translate(${currentX}, ${currentY})`}
      onClick={onClick}
      onMouseDown={handleMouseDown}
      style={{ cursor: draggable ? 'grab' : 'pointer' }}
    >
      <circle
        r={isSelected ? 28 : 24}
        fill={color}
        stroke={isSelected ? '#ffffff' : 'rgba(0,0,0,0.3)'}
        strokeWidth={isSelected ? 4 : 2}
        filter={isDragging ? 'drop-shadow(0 4px 6px rgba(0,0,0,0.4))' : undefined}
      />

      <text
        y="1"
        textAnchor="middle"
        dominantBaseline="middle"
        fill="white"
        fontSize="14"
        fontWeight="bold"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {player.display_number || player.slot_number}
      </text>

      <text
        y="38"
        textAnchor="middle"
        fill="white"
        fontSize="11"
        fontWeight="500"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {player.display_name?.split(' ').pop() || `Player ${player.slot_number}`}
      </text>

      <text
        y="52"
        textAnchor="middle"
        fill="rgba(255,255,255,0.7)"
        fontSize="9"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {player.position_label}
      </text>
    </g>
  );
};

export default PlayerMarker;