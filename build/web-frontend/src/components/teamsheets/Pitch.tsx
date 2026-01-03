import React from 'react';
import type { TeamsheetPlayer } from '../../types/teamsheet';
import PlayerMarker from './PlayerMarker';

interface PitchProps {
  players: TeamsheetPlayer[];
  width?: number;
  height?: number;
  selectedPlayerId?: number | null;
  onPlayerClick?: (player: TeamsheetPlayer) => void;
  onPlayerDragEnd?: (playerId: number, x: number, y: number) => void;
  editable?: boolean;
}

const Pitch: React.FC<PitchProps> = ({
  players,
  width = 600,
  height = 800,
  selectedPlayerId = null,
  onPlayerClick,
  onPlayerDragEnd,
  editable = false,
}) => {
  const starters = players.filter(p => !p.is_substitute);

  const toPixelX = (normalizedX: number) => (normalizedX / 100) * width;
  const toPixelY = (normalizedY: number) => (normalizedY / 100) * height;
  const toNormalizedX = (pixelX: number) => (pixelX / width) * 100;
  const toNormalizedY = (pixelY: number) => (pixelY / height) * 100;

  const handleDragEnd = (playerId: number, pixelX: number, pixelY: number) => {
    if (onPlayerDragEnd) {
      const clampedX = Math.max(0, Math.min(width, pixelX));
      const clampedY = Math.max(0, Math.min(height, pixelY));
      onPlayerDragEnd(playerId, toNormalizedX(clampedX), toNormalizedY(clampedY));
    }
  };

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: '100%', maxWidth: width, height: 'auto' }}
    >
      <defs>
        <pattern id="grass" patternUnits="userSpaceOnUse" width="40" height="40">
          <rect width="40" height="40" fill="#2d8a3e" />
          <rect x="0" y="0" width="20" height="40" fill="#2a8039" />
        </pattern>
      </defs>

      <rect x="0" y="0" width={width} height={height} fill="url(#grass)" />

      <rect
        x="10"
        y="10"
        width={width - 20}
        height={height - 20}
        fill="none"
        stroke="white"
        strokeWidth="2"
      />

      <line
        x1="10"
        y1={height / 2}
        x2={width - 10}
        y2={height / 2}
        stroke="white"
        strokeWidth="2"
      />

      <circle
        cx={width / 2}
        cy={height / 2}
        r="60"
        fill="none"
        stroke="white"
        strokeWidth="2"
      />
      <circle cx={width / 2} cy={height / 2} r="4" fill="white" />

      <rect
        x={(width - 200) / 2}
        y="10"
        width="200"
        height="80"
        fill="none"
        stroke="white"
        strokeWidth="2"
      />
      <rect
        x={(width - 80) / 2}
        y="10"
        width="80"
        height="30"
        fill="none"
        stroke="white"
        strokeWidth="2"
      />
      <circle
        cx={width / 2}
        cy="90"
        r="4"
        fill="white"
      />
      <path
        d={`M ${width / 2 - 50} 90 A 50 50 0 0 0 ${width / 2 + 50} 90`}
        fill="none"
        stroke="white"
        strokeWidth="2"
      />

      <rect
        x={(width - 200) / 2}
        y={height - 90}
        width="200"
        height="80"
        fill="none"
        stroke="white"
        strokeWidth="2"
      />
      <rect
        x={(width - 80) / 2}
        y={height - 40}
        width="80"
        height="30"
        fill="none"
        stroke="white"
        strokeWidth="2"
      />
      <circle
        cx={width / 2}
        cy={height - 90}
        r="4"
        fill="white"
      />
      <path
        d={`M ${width / 2 - 50} ${height - 90} A 50 50 0 0 1 ${width / 2 + 50} ${height - 90}`}
        fill="none"
        stroke="white"
        strokeWidth="2"
      />

      <path
        d="M 10 10 Q 10 10 10 10"
        fill="none"
        stroke="white"
        strokeWidth="2"
      />

      {starters.map(player => (
        <PlayerMarker
          key={player.id}
          player={player}
          x={toPixelX(player.position_x)}
          y={toPixelY(100 - player.position_y)}
          isSelected={selectedPlayerId === player.id}
          onClick={() => onPlayerClick?.(player)}
          onDragEnd={editable ? (x, y) => handleDragEnd(player.id, x, y) : undefined}
          draggable={editable}
        />
      ))}
    </svg>
  );
};

export default Pitch;