import React from 'react';
import {
  PITCH_PADDING,
  PITCH_VIEWBOX_HEIGHT,
  PITCH_VIEWBOX_WIDTH,
} from '../../utils/pitchCoords';

const STROKE_COLOUR = 'rgba(255, 255, 255, 0.85)';
const STROKE_WIDTH = 3;

const PitchMarkings: React.FC = () => {
  const left = PITCH_PADDING;
  const top = PITCH_PADDING;
  const width = PITCH_VIEWBOX_WIDTH - (PITCH_PADDING * 2);
  const height = PITCH_VIEWBOX_HEIGHT - (PITCH_PADDING * 2);
  const bottom = top + height;
  const centreX = left + (width / 2);
  const centreY = top + (height / 2);

  const penaltyAreaWidth = 165;
  const penaltyAreaHeight = 403;
  const sixYardWidth = 55;
  const sixYardHeight = 183;
  const centreCircleRadius = 91.5;
  const penaltySpotOffset = 110;

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
        x={left + ((width - penaltyAreaWidth) / 2)}
        y={top}
        width={penaltyAreaWidth}
        height={penaltyAreaHeight}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <rect
        x={left + ((width - penaltyAreaWidth) / 2)}
        y={bottom - penaltyAreaHeight}
        width={penaltyAreaWidth}
        height={penaltyAreaHeight}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <rect
        x={left + ((width - sixYardWidth) / 2)}
        y={top}
        width={sixYardWidth}
        height={sixYardHeight}
        fill="none"
        stroke={STROKE_COLOUR}
        strokeWidth={STROKE_WIDTH}
      />

      <rect
        x={left + ((width - sixYardWidth) / 2)}
        y={bottom - sixYardHeight}
        width={sixYardWidth}
        height={sixYardHeight}
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
};

export default PitchMarkings;