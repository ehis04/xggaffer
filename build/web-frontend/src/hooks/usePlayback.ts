import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  TacticsBoardFrame,
  TacticsPlaybackFramePair,
  TacticsPlaybackStatus,
} from '../types/tactics';
import { clampUnitInterval } from '../utils/easing';

interface UsePlaybackOptions {
  frames: TacticsBoardFrame[];
  initialFrameIndex?: number;
}

interface PlaybackState {
  status: TacticsPlaybackStatus;
  sourceFrameIndex: number;
  targetFrameIndex: number | null;
  progress: number;
}

const DEFAULT_IDLE_FRAME_INDEX = 0;

const sortFrames = (frames: TacticsBoardFrame[]): TacticsBoardFrame[] => {
  return [...frames].sort((left, right) => {
    if (left.frame_index !== right.frame_index) {
      return left.frame_index - right.frame_index;
    }

    return left.id - right.id;
  });
};

const resolveFrameIndex = (
  frames: TacticsBoardFrame[],
  requestedFrameIndex: number | undefined
): number => {
  if (frames.length === 0) {
    return DEFAULT_IDLE_FRAME_INDEX;
  }

  if (requestedFrameIndex !== undefined) {
    const exactMatch = frames.find(
      (frame) => frame.frame_index === requestedFrameIndex
    );
    if (exactMatch) {
      return exactMatch.frame_index;
    }
  }

  const frameZero = frames.find((frame) => frame.frame_index === 0);
  if (frameZero) {
    return frameZero.frame_index;
  }

  return frames[0].frame_index;
};

const findFramePosition = (
  frames: TacticsBoardFrame[],
  frameIndex: number
): number => {
  return frames.findIndex((frame) => frame.frame_index === frameIndex);
};

const getPairForSourceFrameIndex = (
  frames: TacticsBoardFrame[],
  sourceFrameIndex: number
): TacticsPlaybackFramePair | null => {
  const sourcePosition = findFramePosition(frames, sourceFrameIndex);
  if (sourcePosition === -1) {
    return null;
  }

  const sourceFrame = frames[sourcePosition];
  const targetFrame = frames[sourcePosition + 1] ?? null;

  return {
    sourceFrame,
    targetFrame,
    sourceFrameIndex: sourceFrame.frame_index,
    targetFrameIndex: targetFrame?.frame_index ?? null,
  };
};

const getInitialState = (
  frames: TacticsBoardFrame[],
  initialFrameIndex: number | undefined
): PlaybackState => {
  const resolvedFrameIndex = resolveFrameIndex(frames, initialFrameIndex);
  const initialPair = getPairForSourceFrameIndex(frames, resolvedFrameIndex);

  return {
    status: 'idle',
    sourceFrameIndex: initialPair?.sourceFrameIndex ?? resolvedFrameIndex,
    targetFrameIndex: initialPair?.targetFrameIndex ?? null,
    progress: 0,
  };
};

export interface UsePlaybackResult {
  status: TacticsPlaybackStatus;
  isPlaying: boolean;
  canPlay: boolean;
  sourceFrameIndex: number;
  targetFrameIndex: number | null;
  currentFrameIndex: number;
  progress: number;
  activePair: TacticsPlaybackFramePair | null;
  play: (startFrameIndex?: number) => void;
  pause: () => void;
  stop: () => void;
  reset: (frameIndex?: number) => void;
}

export const usePlayback = ({
  frames,
  initialFrameIndex = DEFAULT_IDLE_FRAME_INDEX,
}: UsePlaybackOptions): UsePlaybackResult => {
  const sortedFrames = useMemo(() => sortFrames(frames), [frames]);

  const [state, setState] = useState<PlaybackState>(() =>
    getInitialState(sortedFrames, initialFrameIndex)
  );

  const animationFrameIdRef = useRef<number | null>(null);
  const lastTimestampRef = useRef<number | null>(null);
  const elapsedMsRef = useRef<number>(0);
  const statusRef = useRef<TacticsPlaybackStatus>('idle');
  const sourceFrameIndexRef = useRef<number>(
    resolveFrameIndex(sortedFrames, initialFrameIndex)
  );
  const targetFrameIndexRef = useRef<number | null>(
    getPairForSourceFrameIndex(
      sortedFrames,
      resolveFrameIndex(sortedFrames, initialFrameIndex)
    )?.targetFrameIndex ?? null
  );

  const syncRefsFromState = useCallback((nextState: PlaybackState) => {
    statusRef.current = nextState.status;
    sourceFrameIndexRef.current = nextState.sourceFrameIndex;
    targetFrameIndexRef.current = nextState.targetFrameIndex;
  }, []);

  const cancelPlaybackFrame = useCallback(() => {
    if (animationFrameIdRef.current !== null) {
      cancelAnimationFrame(animationFrameIdRef.current);
      animationFrameIdRef.current = null;
    }
  }, []);

  const applyState = useCallback(
    (nextState: PlaybackState) => {
      syncRefsFromState(nextState);
      setState(nextState);
    },
    [syncRefsFromState]
  );

  const resetTimingRefs = useCallback(() => {
    lastTimestampRef.current = null;
    elapsedMsRef.current = 0;
  }, []);

  const stop = useCallback(() => {
    cancelPlaybackFrame();
    resetTimingRefs();

    const resetPair = getPairForSourceFrameIndex(
      sortedFrames,
      DEFAULT_IDLE_FRAME_INDEX
    );
    const fallbackFrameIndex = resolveFrameIndex(
      sortedFrames,
      DEFAULT_IDLE_FRAME_INDEX
    );

    applyState({
      status: 'idle',
      sourceFrameIndex: resetPair?.sourceFrameIndex ?? fallbackFrameIndex,
      targetFrameIndex: resetPair?.targetFrameIndex ?? null,
      progress: 0,
    });
  }, [applyState, cancelPlaybackFrame, resetTimingRefs, sortedFrames]);

  const reset = useCallback(
    (frameIndex?: number) => {
      cancelPlaybackFrame();
      resetTimingRefs();

      const resolvedFrameIndex = resolveFrameIndex(sortedFrames, frameIndex);
      const nextPair = getPairForSourceFrameIndex(sortedFrames, resolvedFrameIndex);

      applyState({
        status: 'idle',
        sourceFrameIndex: nextPair?.sourceFrameIndex ?? resolvedFrameIndex,
        targetFrameIndex: nextPair?.targetFrameIndex ?? null,
        progress: 0,
      });
    },
    [applyState, cancelPlaybackFrame, resetTimingRefs, sortedFrames]
  );

  const pause = useCallback(() => {
    if (statusRef.current !== 'playing') {
      return;
    }

    cancelPlaybackFrame();
    lastTimestampRef.current = null;

    applyState({
      status: 'paused',
      sourceFrameIndex: sourceFrameIndexRef.current,
      targetFrameIndex: targetFrameIndexRef.current,
      progress: state.progress,
    });
  }, [applyState, cancelPlaybackFrame, state.progress]);

  const tick = useCallback(
    (timestamp: number) => {
      if (statusRef.current !== 'playing') {
        return;
      }

      const currentPair = getPairForSourceFrameIndex(
        sortedFrames,
        sourceFrameIndexRef.current
      );

      if (!currentPair || !currentPair.targetFrame) {
        stop();
        return;
      }

      if (lastTimestampRef.current === null) {
        lastTimestampRef.current = timestamp;
        animationFrameIdRef.current = requestAnimationFrame(tick);
        return;
      }

      const deltaMs = timestamp - lastTimestampRef.current;
      lastTimestampRef.current = timestamp;
      elapsedMsRef.current += deltaMs;

      let activePair = currentPair;
      let activeDurationMs = Math.max(1, activePair.sourceFrame.duration_ms);

      while (elapsedMsRef.current >= activeDurationMs) {
        elapsedMsRef.current -= activeDurationMs;

        const nextPair = getPairForSourceFrameIndex(
          sortedFrames,
          activePair.targetFrameIndex ?? DEFAULT_IDLE_FRAME_INDEX
        );

        if (!nextPair || !nextPair.targetFrame) {
          stop();
          return;
        }

        activePair = nextPair;
        sourceFrameIndexRef.current = activePair.sourceFrameIndex;
        targetFrameIndexRef.current = activePair.targetFrameIndex;
        activeDurationMs = Math.max(1, activePair.sourceFrame.duration_ms);
      }

      const nextProgress = clampUnitInterval(
        elapsedMsRef.current / activeDurationMs
      );

      applyState({
        status: 'playing',
        sourceFrameIndex: activePair.sourceFrameIndex,
        targetFrameIndex: activePair.targetFrameIndex,
        progress: nextProgress,
      });

      animationFrameIdRef.current = requestAnimationFrame(tick);
    },
    [applyState, sortedFrames, stop]
  );

  const play = useCallback(
    (startFrameIndex?: number) => {
      if (sortedFrames.length < 2) {
        reset(startFrameIndex);
        return;
      }

      cancelPlaybackFrame();

      if (
        statusRef.current === 'paused' &&
        startFrameIndex === undefined &&
        targetFrameIndexRef.current !== null
      ) {
        applyState({
          status: 'playing',
          sourceFrameIndex: sourceFrameIndexRef.current,
          targetFrameIndex: targetFrameIndexRef.current,
          progress: state.progress,
        });
        lastTimestampRef.current = null;
        animationFrameIdRef.current = requestAnimationFrame(tick);
        return;
      }

      const resolvedFrameIndex = resolveFrameIndex(
        sortedFrames,
        startFrameIndex ?? initialFrameIndex
      );
      const initialPair = getPairForSourceFrameIndex(
        sortedFrames,
        resolvedFrameIndex
      );

      if (!initialPair || !initialPair.targetFrame) {
        reset(resolvedFrameIndex);
        return;
      }

      resetTimingRefs();

      applyState({
        status: 'playing',
        sourceFrameIndex: initialPair.sourceFrameIndex,
        targetFrameIndex: initialPair.targetFrameIndex,
        progress: 0,
      });

      animationFrameIdRef.current = requestAnimationFrame(tick);
    },
    [
      applyState,
      cancelPlaybackFrame,
      initialFrameIndex,
      reset,
      resetTimingRefs,
      sortedFrames,
      state.progress,
      tick,
    ]
  );

  useEffect(() => {
    if (sortedFrames.length === 0) {
      cancelPlaybackFrame();
      resetTimingRefs();

      applyState({
        status: 'idle',
        sourceFrameIndex: DEFAULT_IDLE_FRAME_INDEX,
        targetFrameIndex: null,
        progress: 0,
      });
      return;
    }

    const currentSourceStillExists = sortedFrames.some(
      (frame) => frame.frame_index === sourceFrameIndexRef.current
    );

    if (!currentSourceStillExists) {
      reset(initialFrameIndex);
      return;
    }

    const nextPair = getPairForSourceFrameIndex(
      sortedFrames,
      sourceFrameIndexRef.current
    );

    if (statusRef.current === 'playing' && (!nextPair || !nextPair.targetFrame)) {
      stop();
      return;
    }

    applyState({
      status: statusRef.current,
      sourceFrameIndex: nextPair?.sourceFrameIndex ?? sourceFrameIndexRef.current,
      targetFrameIndex: nextPair?.targetFrameIndex ?? null,
      progress: statusRef.current === 'idle' ? 0 : state.progress,
    });
  }, [
    applyState,
    cancelPlaybackFrame,
    initialFrameIndex,
    reset,
    resetTimingRefs,
    sortedFrames,
    state.progress,
    stop,
  ]);

  useEffect(() => {
    return () => {
      cancelPlaybackFrame();
    };
  }, [cancelPlaybackFrame]);

  const activePair = useMemo(() => {
    return getPairForSourceFrameIndex(sortedFrames, state.sourceFrameIndex);
  }, [sortedFrames, state.sourceFrameIndex]);

  return {
    status: state.status,
    isPlaying: state.status === 'playing',
    canPlay: sortedFrames.length > 1,
    sourceFrameIndex: state.sourceFrameIndex,
    targetFrameIndex: state.targetFrameIndex,
    currentFrameIndex: state.sourceFrameIndex,
    progress: state.progress,
    activePair,
    play,
    pause,
    stop,
    reset,
  };
};

export default usePlayback;