export const clampUnitInterval = (value: number): number => {
  if (Number.isNaN(value)) {
    return 0;
  }

  if (value <= 0) {
    return 0;
  }

  if (value >= 1) {
    return 1;
  }

  return value;
};

export const easeInOutCubic = (value: number): number => {
  const clamped = clampUnitInterval(value);

  if (clamped < 0.5) {
    return 4 * clamped * clamped * clamped;
  }

  return 1 - Math.pow(-2 * clamped + 2, 3) / 2;
};

export default easeInOutCubic;