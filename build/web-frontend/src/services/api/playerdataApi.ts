import apiClient from './client';
import type {
  ClubSeasonSummary,
  EnrichedPlayerListFilters,
  EnrichedPlayerListResponse,
  PlayerComparisonParams,
  PlayerComparisonResult,
  PlayerDataFilters,
  PlayerOverview,
  PlayerOverviewComparison,
  PlayerSeasonSummary,
} from '../../types/playerdata';

type ApiParamValue = string | number | boolean | undefined | null;
type ApiParamRecord = Record<string, ApiParamValue>;

const cleanString = (value?: string | null): string | undefined => {
  if (value === undefined || value === null) {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
};

const cleanParams = (params?: ApiParamRecord): Record<string, string> | undefined => {
  if (!params) {
    return undefined;
  }

  const cleanedEntries = Object.entries(params)
    .map(([key, value]) => {
      if (typeof value === 'string') {
        const trimmed = value.trim();
        return [key, trimmed] as const;
      }

      return [key, value] as const;
    })
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => [key, String(value)] as [string, string]);

  if (cleanedEntries.length === 0) {
    return undefined;
  }

  return Object.fromEntries(cleanedEntries);
};

const buildPlayerDataFilterParams = (
  filters?: PlayerDataFilters
): Record<string, string> | undefined =>
  cleanParams({
    provider: cleanString(filters?.provider),
    season: cleanString(filters?.season),
    competition_code: cleanString(filters?.competition_code),
    competition_name: cleanString(filters?.competition_name),
  });

const buildPlayerComparisonParams = (
  params: PlayerComparisonParams
): Record<string, string> | undefined =>
  cleanParams({
    player_a_id: params.player_a_id,
    player_b_id: params.player_b_id,
    provider: cleanString(params.provider),
    season: cleanString(params.season),
    competition_code: cleanString(params.competition_code),
    competition_name: cleanString(params.competition_name),
  });

const buildEnrichedPlayerListParams = (
  params?: EnrichedPlayerListFilters
): Record<string, string> | undefined =>
  cleanParams({
    club_id: params?.club_id,
    position: cleanString(params?.position),
    search: cleanString(params?.search),
    ordering: cleanString(params?.ordering),
    limit: params?.limit,
    include_unavailable: params?.include_unavailable,
    provider: cleanString(params?.provider),
    season: cleanString(params?.season),
    competition_code: cleanString(params?.competition_code),
    competition_name: cleanString(params?.competition_name),
  });

const PLAYERDATA_BASE = '/playerdata';
const PLAYER_SUMMARY_BASE = `${PLAYERDATA_BASE}/players`;
const CLUB_SUMMARY_BASE = `${PLAYERDATA_BASE}/clubs`;

export const playerdataApi = {
  getPlayerSeasonSummary: (playerId: number, filters?: PlayerDataFilters) =>
    apiClient.get<PlayerSeasonSummary>(
      `${PLAYER_SUMMARY_BASE}/${playerId}/season-summary/`,
      buildPlayerDataFilterParams(filters)
    ),

  getPlayerOverview: (playerId: number, filters?: PlayerDataFilters) =>
    apiClient.get<PlayerOverview>(
      `${PLAYER_SUMMARY_BASE}/${playerId}/overview/`,
      buildPlayerDataFilterParams(filters)
    ),

  getClubSeasonSummary: (clubId: number, filters?: PlayerDataFilters) =>
    apiClient.get<ClubSeasonSummary>(
      `${CLUB_SUMMARY_BASE}/${clubId}/season-summary/`,
      buildPlayerDataFilterParams(filters)
    ),

  comparePlayers: (params: PlayerComparisonParams) =>
    apiClient.get<PlayerComparisonResult>(
      `${PLAYER_SUMMARY_BASE}/compare/`,
      buildPlayerComparisonParams(params)
    ),

  getPlayerOverviewComparison: (params: PlayerComparisonParams) =>
    apiClient.get<PlayerOverviewComparison>(
      `${PLAYER_SUMMARY_BASE}/overview-compare/`,
      buildPlayerComparisonParams(params)
    ),

  listEnrichedPlayers: (params?: EnrichedPlayerListFilters) =>
    apiClient.get<EnrichedPlayerListResponse>(
      `${PLAYER_SUMMARY_BASE}/enriched/`,
      buildEnrichedPlayerListParams(params)
    ),
};

export {
  buildPlayerDataFilterParams,
  buildPlayerComparisonParams,
  buildEnrichedPlayerListParams,
};

export default playerdataApi;