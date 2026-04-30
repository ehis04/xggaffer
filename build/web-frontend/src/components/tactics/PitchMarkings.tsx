import React from 'react';
import {
  PITCH_PADDING,
  PITCH_VIEWBOX_HEIGHT,
  PITCH_VIEWBOX_WIDTH,
} from '../../utils/pitchCoords';
import type { TacticsPitchOrientation } from '../../types/tactics';

const STROKE_COLOUR = 'rgba(255, 255, 255, 0.85)';
const STROKE_WIDTH = 3;

interface PitchMarkingsProps {
  orientation?: TacticsPitchOrientation;
}

const PitchMarkings: React.FC<PitchMarkingsProps> = ({
  orientation = 'vertical',
}) => {
  const left = PITCH_PADDING;
  const top = PITCH_PADDING;
  const width = PITCH_VIEWBOX_WIDTH - (PITCH_PADDING * 2);
  const height = PITCH_VIEWBOX_HEIGHT - (PITCH_PADDING * 2);
  const bottom = top + height;
  const centreX = left + (width / 2);
  const centreY = top + (height / 2);

  const penaltyAreaDepth = 165;
  const penaltyAreaSpan = 403;
  const sixYardDepth = 55;
  const sixYardSpan = 183;
  const centreCircleRadius = 91.5;
  const penaltySpotOffset = 110;

  if (orientation === 'vertical') {
    return (
      <g aria-label="Pitch markings">
        <rect
          x={left}
          y={top}
          width={width}
          height={height}
          fill="none"
          stroke={STROKE_COLOUR}
          strokeWidth={STROKE_WIDTH}
        />

        <line
          x1={left}
          y1={centreY}
          x2={left + width}
          y2={centreY}
          stroke={STROKE_COLOUR}
          strokeWidth={STROKE_WIDTH}
        />

        <circle
          cx={centreX}
          cy={centreY}
          r={centreCircleRadius}
          fill="none"
          stroke={STROKE_COLOUR}
          strokeWidth={STROKE_WIDTH}
        />

        <circle
          cx={centreX}
          cy={centreY}
          r={3.5}
          fill={STROKE_COLOUR}
        />

        <rect
          x={left + ((width - penaltyAreaSpan) / 2)}
          y={top}
          width={penaltyAreaSpan}
          height={penaltyAreaDepth}
          fill="none"
          stroke={STROKE_COLOUR}
          strokeWidth={STROKE_WIDTH}
        />

        <rect
          x={left + ((width - penaltyAreaSpan) / 2)}
          y={bottom - penaltyAreaDepth}
          width={penaltyAreaSpan}
          height={penaltyAreaDepth}
          fill="none"
          stroke={STROKE_COLOUR}
          strokeWidth={STROKE_WIDTH}
        />

        <rect
          x={left + ((width - sixYardSpan) / 2)}
          y={top}
          width={sixYardSpan}
          height={sixYardDepth}
          fill="none"
          stroke={STROKE_COLOUR}
          strokeWidth={STROKE_WIDTH}
        />

        <rect
          x={left + ((width - sixYardSpan) / 2)}
          y={bottom - sixYardDepth}
          width={sixYardSpan}
          height={sixYardDepth}
          fill="none"
          stroke={STROKE_COLOUR}
          strokeWidth={STROKE_WIDTH}
        />

        <circle
          cx={centreX}
          cy={top + penaltySpotOffset}
          r={3.5}
          fill={STROKE_COLOUR}
        />

        <circle
          cx={centreX}
          cy={bottom - penaltySpotOffset}
          r={3.5}
          fill={STROKE_COLOUR}
        />
      </g>
    );
  }

  return (
    <g aria-label="Pitch markings">
      <rect
        x={left}
        y={top}
        width={width}
        height={height}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <line
        x1={centreX}
        y1={top}
        x2={centreX}
        y2={bottom}
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <circle
        cx={centreX}
        cy={centreY}
        r={centreCircleRadius}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <circle
        cx={centreX}
        cy={centreY}
        r={3.5}
        fill={STROKE_COLOUR}
      />

      <rect
        x={left}
        y={top + ((height - penaltyAreaSpan) / 2)}
        width={penaltyAreaDepth}
        height={penaltyAreaSpan}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <rect
        x={left + width - penaltyAreaDepth}
        y={top + ((height - penaltyAreaSpan) / 2)}
        width={penaltyAreaDepth}
        height={penaltyAreaSpan}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <rect
        x={left}
        y={top + ((height - sixYardSpan) / 2)}
        width={sixYardDepth}
        height={sixYardSpan}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <rect
        x={left + width - sixYardDepth}
        y={top + ((height - sixYardSpan) / 2)}
        width={sixYardDepth}
        height={sixYardSpan}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <circle
        cx={left + penaltySpotOffset}
        cy={centreY}
        r={3.5}
        fill={STROKE_COLOUR}
      />

      <circle
        cx={left + width - penaltySpotOffset}
          cy={centreY}
          r={3.5}
          fill={STROKE_COLOUR}
        />
    </g>
  );
};

export default PitchMarkings;