export const PITCH_VIEWBOX_WIDTH = 1050;
export const PITCH_VIEWBOX_HEIGHT = 680;
export const PITCH_PADDING = 30;

export const PITCH_MIN = 0;
export const PITCH_MAX = 100;

export const INNER_PITCH_WIDTH = PITCH_VIEWBOX_WIDTH - (PITCH_PADDING * 2);
export const INNER_PITCH_HEIGHT = PITCH_VIEWBOX_HEIGHT - (PITCH_PADDING * 2);

export interface PitchPoint {
  x: number;
  y: number;
}

export interface SvgPoint {
  x: number;
  y: number;
}

export const clampPitchCoordinate = (value: number): number => {
  if (Number.isNaN(value)) {
    return PITCH_MIN;
  }

  if (value < PITCH_MIN) {
    return PITCH_MIN;
  }

  if (value > PITCH_MAX) {
    return PITCH_MAX;
  }

  return value;
};

export const clampPitchPoint = (point: PitchPoint): PitchPoint => {
  return {
    x: clampPitchCoordinate(point.x),
    y: clampPitchCoordinate(point.y),
  };
};

export const pitchToSvg = (pitchX: number, pitchY: number): SvgPoint => {
  const clamped = clampPitchPoint({ x: pitchX, y: pitchY });

  return {
    x: PITCH_PADDING + (clamped.x / 100) * INNER_PITCH_WIDTH,
    y: PITCH_PADDING + ((100 - clamped.y) / 100) * INNER_PITCH_HEIGHT,
  };
};

export const svgToPitch = (svgX: number, svgY: number): PitchPoint => {
  const rawX = ((svgX - PITCH_PADDING) / INNER_PITCH_WIDTH) * 100;
  const rawY = 100 - (((svgY - PITCH_PADDING) / INNER_PITCH_HEIGHT) * 100);

  return clampPitchPoint({
    x: rawX,
    y: rawY,
  });
};