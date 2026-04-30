import { QueryClient } from '@tanstack/react-query';

const STALE_TIME_STANDARD = 5 * 60 * 1000;
const STALE_TIME_SHORT = 60 * 1000;
const GC_TIME_STANDARD = 10 * 60 * 1000;
const RETRY_COUNT = 1;

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: STALE_TIME_STANDARD,
            gcTime: GC_TIME_STANDARD,
            retry: RETRY_COUNT,
            refetchOnWindowFocus: true,
        },
    },
});

export { STALE_TIME_STANDARD, STALE_TIME_SHORT, GC_TIME_STANDARD };
