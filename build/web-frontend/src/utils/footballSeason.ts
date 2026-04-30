export interface PredictionLeagueOption {
  value: string;
  label: string;
  liveCompetitionCode: string;
}

export const PREDICTION_LEAGUE_OPTIONS: PredictionLeagueOption[] = [
  { value: 'EPL', label: 'Premier League', liveCompetitionCode: 'PL' },
  { value: 'La_Liga', label: 'La Liga', liveCompetitionCode: 'PD' },
  { value: 'Bundesliga', label: 'Bundesliga', liveCompetitionCode: 'BL1' },
  { value: 'Serie_A', label: 'Serie A', liveCompetitionCode: 'SA' },
  { value: 'Ligue_1', label: 'Ligue 1', liveCompetitionCode: 'FL1' },
];

export const LIVE_COMPETITION_TO_PREDICTION_LEAGUE = Object.fromEntries(
  PREDICTION_LEAGUE_OPTIONS.map((option) => [option.liveCompetitionCode, option.value]),
) as Record<string, string>;

export const PREDICTION_LEAGUE_TO_LIVE_COMPETITION = Object.fromEntries(
  PREDICTION_LEAGUE_OPTIONS.map((option) => [option.value, option.liveCompetitionCode]),
) as Record<string, string>;

export const getCurrentFootballSeason = (date = new Date()): string => {
  const year = date.getUTCFullYear();
  return String(date.getUTCMonth() >= 7 ? year : year - 1);
};

export const getFootballSeasonForDate = (
  value?: string | number | Date | null,
  fallback = getCurrentFootballSeason(),
): string => {
  if (!value) return fallback;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return getCurrentFootballSeason(date);
};

export const parseSeasonStartYear = (
  label?: string | number | null,
  fallback = getCurrentFootballSeason(),
): string => {
  const text = String(label ?? '').trim();
  const match = text.match(/\d{4}/);
  return match?.[0] ?? fallback;
};

export const formatSeasonDisplay = (season?: string | number | null): string => {
  const text = String(season ?? '').trim();
  const match = text.match(/^(\d{4})$/);
  if (!match) {
    return text || 'current season';
  }

  const startYear = Number(match[1]);
  return `${startYear}/${String(startYear + 1).slice(-2)}`;
};

export const predictionLeagueToLiveCompetitionCode = (league: string): string =>
  PREDICTION_LEAGUE_TO_LIVE_COMPETITION[league] ?? 'PL';

export const liveCompetitionCodeToPredictionLeague = (competitionCode?: string | null): string | null => {
  if (!competitionCode) {
    return null;
  }

  return LIVE_COMPETITION_TO_PREDICTION_LEAGUE[competitionCode] ?? null;
};
