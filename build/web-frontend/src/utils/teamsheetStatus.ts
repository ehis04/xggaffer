export type StatusKey = 'incomplete' | 'dateNotSet' | 'notPlayed' | 'gamePlayed';

export interface StatusInfo {
  label: string;
  key: StatusKey;
}

export function getTeamsheetStatus(
  starterCount: number,
  matchDate: string | null | undefined
): StatusInfo {
  if (starterCount !== 11) {
    return { label: `${starterCount}/11`, key: 'incomplete' };
  }
  if (!matchDate) {
    return { label: 'Date Not Set', key: 'dateNotSet' };
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const match = new Date(matchDate);
  match.setHours(0, 0, 0, 0);
  if (match > today) {
    return { label: 'Game Not Played', key: 'notPlayed' };
  }
  return { label: 'Game Played', key: 'gamePlayed' };
}
