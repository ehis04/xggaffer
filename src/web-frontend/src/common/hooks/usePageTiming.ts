import { useCallback, useRef } from "react";

export function usePageTiming(pageName: string): { markDataReceived: () => void } {
    const mountedAt = useRef<number>(Date.now());

    const markDataReceived = useCallback(() => {
        if (!import.meta.env.DEV) return;
        const elapsed = Date.now() - mountedAt.current;
        console.log({ page: pageName, time_to_data_ms: elapsed });
    }, [pageName]);

    return { markDataReceived };
}
