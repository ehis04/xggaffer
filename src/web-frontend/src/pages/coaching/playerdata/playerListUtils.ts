import type { EnrichedPlayerListItem } from '../../../types/playerdata';

export const getEnrichedPlayerListKey = (item: EnrichedPlayerListItem): string => {
  const playerId = item.player?.id;
  const clubId = item.club?.id;

  if (playerId != null) {
    return `${playerId}:${clubId ?? 'no-club'}`;
  }

  const name =
    item.player?.display_name ||
    item.player?.full_name ||
    item.player?.short_name ||
    'unknown-player';

  return `${name}:${clubId ?? 'no-club'}`;
};

export const dedupeEnrichedPlayers = (
  players: EnrichedPlayerListItem[],
): EnrichedPlayerListItem[] => {
  const seen = new Set<string>();

  return players.filter((item) => {
    const key = getEnrichedPlayerListKey(item);
    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
};
