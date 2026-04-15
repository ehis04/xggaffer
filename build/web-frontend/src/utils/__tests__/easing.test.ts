import { describe, expect, it } from 'vitest';
import { easeInOutCubic } from '../easing';

describe('easeInOutCubic', () => {
  it('returns 0 at progress 0', () => {
    expect(easeInOutCubic(0)).toBe(0);
  });

  it('returns 1 at progress 1', () => {
    expect(easeInOutCubic(1)).toBe(1);
  });
});