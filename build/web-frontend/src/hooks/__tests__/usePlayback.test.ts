import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import usePlayback from '../usePlayback';
import type { TacticsBoardFrame } from '../../types/tactics';

const createFrame = (
  frameIndex: number,
  durationMs = 100
): TacticsBoardFrame => ({
  id: frameIndex + 1,
  board: 1,
  frame_index: frameIndex,
  label: `Frame ${frameIndex}`,
  duration_ms: durationMs,
  notes: '',
  items: [],
});

describe('usePlayback', () => {
  let animationTime = 0;

  beforeEach(() => {
    vi.useFakeTimers();
    animationTime = 0;

    vi.stubGlobal(
      'requestAnimationFrame',
      ((callback: FrameRequestCallback) => {
        return setTimeout(() => {
          animationTime += 16;
          callback(animationTime);
        }, 16) as unknown as number;
      }) as typeof requestAnimationFrame
    );

    vi.stubGlobal(
      'cancelAnimationFrame',
      ((handle: number) => {
        clearTimeout(handle);
      }) as typeof cancelAnimationFrame
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('starts in an idle state', () => {
    const frames = [createFrame(0), createFrame(1)];
    const { result } = renderHook(() => usePlayback({ frames }));

    expect(result.current.status).toBe('idle');
    expect(result.current.isPlaying).toBe(false);
    expect(result.current.currentFrameIndex).toBe(0);
    expect(result.current.targetFrameIndex).toBe(1);
    expect(result.current.progress).toBe(0);
  });

  it('starts playback from the requested frame', () => {
    const frames = [createFrame(0), createFrame(1), createFrame(2)];
    const { result } = renderHook(() => usePlayback({ frames }));

    act(() => {
      result.current.play(1);
    });

    expect(result.current.status).toBe('playing');
    expect(result.current.sourceFrameIndex).toBe(1);
    expect(result.current.targetFrameIndex).toBe(2);
    expect(result.current.progress).toBe(0);
  });

  it('progresses to the next frame after the active duration elapses', () => {
    const frames = [createFrame(0, 50), createFrame(1, 50), createFrame(2, 50)];
    const { result } = renderHook(() => usePlayback({ frames }));

    act(() => {
      result.current.play(0);
    });

    act(() => {
      vi.advanceTimersByTime(96);
    });

    expect(result.current.sourceFrameIndex).toBe(1);
    expect(result.current.targetFrameIndex).toBe(2);
    expect(result.current.status).toBe('playing');
  });

  it('pauses and resumes cleanly', () => {
    const frames = [createFrame(0, 100), createFrame(1, 100), createFrame(2, 100)];
    const { result } = renderHook(() => usePlayback({ frames }));

    act(() => {
      result.current.play(0);
    });

    act(() => {
      vi.advanceTimersByTime(48);
    });

    const progressBeforePause = result.current.progress;

    act(() => {
      result.current.pause();
    });

    expect(result.current.status).toBe('paused');
    expect(result.current.progress).toBeGreaterThan(0);

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(result.current.progress).toBe(progressBeforePause);

    act(() => {
      result.current.play();
    });

    expect(result.current.status).toBe('playing');
  });

  it('stops and resets back to frame 0', () => {
    const frames = [createFrame(0), createFrame(1), createFrame(2)];
    const { result } = renderHook(() => usePlayback({ frames }));

    act(() => {
      result.current.play(1);
    });

    act(() => {
      result.current.stop();
    });

    expect(result.current.status).toBe('idle');
    expect(result.current.currentFrameIndex).toBe(0);
    expect(result.current.targetFrameIndex).toBe(1);
    expect(result.current.progress).toBe(0);
  });

  it('respects duration_ms before advancing', () => {
    const frames = [createFrame(0, 200), createFrame(1, 60), createFrame(2, 60)];
    const { result } = renderHook(() => usePlayback({ frames }));

    act(() => {
      result.current.play(0);
    });

    act(() => {
      vi.advanceTimersByTime(96);
    });

    expect(result.current.sourceFrameIndex).toBe(0);
    expect(result.current.targetFrameIndex).toBe(1);
    expect(result.current.status).toBe('playing');

    act(() => {
      vi.advanceTimersByTime(160);
    });

    expect(result.current.sourceFrameIndex).toBe(1);
    expect(result.current.targetFrameIndex).toBe(2);
  });
});