export type LiveFootballLinkQueryValue =
  | string
  | number
  | boolean
  | null
  | undefined;

export const buildLiveFootballLink = (
  path: string,
  query?: Record<string, LiveFootballLinkQueryValue>
): string => {
  if (!query) {
    return path;
  }

  const params = new URLSearchParams();

  Object.entries(query).forEach(([key, value]) => {
    if (value === null || value === undefined || value === '') {
      return;
    }

    params.set(key, String(value));
  });

  const queryString = params.toString();
  return queryString ? `${path}?${queryString}` : path;
};