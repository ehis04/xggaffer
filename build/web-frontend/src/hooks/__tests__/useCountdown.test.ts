import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useCountdown } from '../useCountdown';

describe('useCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns the initial value immediately', () => {
    const { result } = renderHook(() => useCountdown(5));
    expect(result.current).toBe(5);
  });

  it('decrements by 1 each second', () => {
    const { result } = renderHook(() => useCountdown(5));

    act(() => { vi.advanceTimersByTime(1000); });
    expect(result.current).toBe(4);

    act(() => { vi.advanceTimersByTime(1000); });
    expect(result.current).toBe(3);
  });

  it('reaches 0 after the full duration', () => {
    const { result } = renderHook(() => useCountdown(3));

    act(() => { vi.advanceTimersByTime(3000); });
    expect(result.current).toBe(0);
  });

  it('calls onComplete when count reaches 0', () => {
    const onComplete = vi.fn();
    renderHook(() => useCountdown(2, onComplete));

    act(() => { vi.advanceTimersByTime(2000); });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('does not call onComplete before count reaches 0', () => {
    const onComplete = vi.fn();
    renderHook(() => useCountdown(3, onComplete));

    act(() => { vi.advanceTimersByTime(2000); });
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('does not decrement below 0', () => {
    const { result } = renderHook(() => useCountdown(1));

    act(() => { vi.advanceTimersByTime(3000); });
    expect(result.current).toBe(0);
  });

  it('cleans up interval on unmount', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const { unmount } = renderHook(() => useCountdown(10));

    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});