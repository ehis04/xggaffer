import apiClient from './client';
import type {
    CompetitionFixturesParams,
    CompetitionFixturesResponse,
    CompetitionListItem,
    CompetitionPlayersParams,
    CompetitionPlayersResponse,
    CompetitionPreviousNextFixturesParams,
    CompetitionPreviousNextFixturesResponse,
    CompetitionScorersParams,
    CompetitionTableParams,
    CompetitionTableResponse,
    CompetitionTeamsParams,
    CompetitionTeamsResponse,
    PlayerSearchParams,
    PlayerSearchResponse,
    TeamPlayersParams,
    TeamPlayersResponse,
    CompetitionTopScorersResponse,
    LiveFootballOverview,
    LeagueCompareResponse,
    LeagueExpectedTableResponse,
    LeagueProjectionParams,
    LeaguesMetaResponse,
    LeagueScenarioLockedResultInput,
    LeagueScenarioResponse,
    CreateSavedLeagueScenarioPayload,
    SavedLeagueScenarioDetail,
    SavedLeagueScenarioListResponse,
} from '../../types/livefootball';
import type { ApiEnvelope } from '../../common/types/response';

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

const buildCompetitionTableParams = (
    params?: CompetitionTableParams
): Record<string, string> | undefined =>
    cleanParams({
        season: cleanString(params?.season),
        snapshot: cleanString(params?.snapshot),
    });

const buildCompetitionFixturesParams = (
    params?: CompetitionFixturesParams
): Record<string, string> | undefined =>
    cleanParams({
        season: cleanString(params?.season),
        status: cleanString(params?.status),
        matchday: params?.matchday,
        limit: params?.limit,
    });

const buildCompetitionPreviousNextFixturesParams = (
    params?: CompetitionPreviousNextFixturesParams
): Record<string, string> | undefined =>
    cleanParams({
        season: cleanString(params?.season),
        previous_limit: params?.previous_limit,
        next_limit: params?.next_limit,
    });

const buildCompetitionScorersParams = (
    params?: CompetitionScorersParams
): Record<string, string> | undefined =>
    cleanParams({
        season: cleanString(params?.season),
        limit: params?.limit,
    });

const buildCompetitionTeamsParams = (
    params?: CompetitionTeamsParams
): Record<string, string> | undefined =>
    cleanParams({
        season: cleanString(params?.season),
    });

const buildTeamPlayersParams = (
    params?: TeamPlayersParams
): Record<string, string> | undefined =>
    cleanParams({
        active_only: params?.active_only,
    });

const buildCompetitionPlayersParams = (
    params?: CompetitionPlayersParams
): Record<string, string> | undefined =>
    cleanParams({
        season: cleanString(params?.season),
        active_only: params?.active_only,
    });

const buildPlayerSearchParams = (
    params?: PlayerSearchParams
): Record<string, string> | undefined =>
    cleanParams({
        q: cleanString(params?.q),
        competition_id: params?.competition_id,
        team_id: params?.team_id,
        season: cleanString(params?.season),
        active_only: params?.active_only,
        limit: params?.limit,
    });

const buildLeagueProjectionParams = (
    params?: LeagueProjectionParams
): Record<string, string> | undefined =>
    cleanParams({
        season: cleanString(params?.season),
        mode: cleanString(params?.mode),
        matchweek: params?.matchweek,
        projection_window: cleanString(params?.projection_window),
    });

const LIVEFOOTBALL_BASE = '/livefootball';

export const liveFootballApi = {
    getCompetitions: (provider?: string) =>
        apiClient.get<CompetitionListItem[]>(
            `${LIVEFOOTBALL_BASE}/competitions/`,
            provider ? { provider } : undefined
        ),

    getCompetitionTable: (competitionId: number, params?: CompetitionTableParams) =>
        apiClient.get<CompetitionTableResponse>(
            `${LIVEFOOTBALL_BASE}/competitions/${competitionId}/table/`,
            buildCompetitionTableParams(params)
        ),

    getCompetitionFixtures: (competitionId: number, params?: CompetitionFixturesParams) =>
        apiClient.get<CompetitionFixturesResponse>(
            `${LIVEFOOTBALL_BASE}/competitions/${competitionId}/fixtures/`,
            buildCompetitionFixturesParams(params)
        ),

    getCompetitionPreviousNextFixtures: (
        competitionId: number,
        params?: CompetitionPreviousNextFixturesParams
    ) =>
        apiClient.get<CompetitionPreviousNextFixturesResponse>(
            `${LIVEFOOTBALL_BASE}/competitions/${competitionId}/fixtures/split/`,
            buildCompetitionPreviousNextFixturesParams(params)
        ),

    getCompetitionScorers: (competitionId: number, params?: CompetitionScorersParams) =>
        apiClient.get<CompetitionTopScorersResponse>(
            `${LIVEFOOTBALL_BASE}/competitions/${competitionId}/scorers/`,
            buildCompetitionScorersParams(params)
        ),

    getCompetitionTeams: (competitionId: number, params?: CompetitionTeamsParams) =>
        apiClient.get<CompetitionTeamsResponse>(
            `${LIVEFOOTBALL_BASE}/competitions/${competitionId}/teams/`,
            buildCompetitionTeamsParams(params)
        ),

    getTeamPlayers: (teamId: number, params?: TeamPlayersParams) =>
        apiClient.get<TeamPlayersResponse>(
            `${LIVEFOOTBALL_BASE}/teams/${teamId}/players/`,
            buildTeamPlayersParams(params)
        ),

    getCompetitionPlayers: (competitionId: number, params?: CompetitionPlayersParams) =>
        apiClient.get<CompetitionPlayersResponse>(
            `${LIVEFOOTBALL_BASE}/competitions/${competitionId}/players/`,
            buildCompetitionPlayersParams(params)
        ),

    searchPlayers: (params?: PlayerSearchParams) =>
        apiClient.get<PlayerSearchResponse>(
            `${LIVEFOOTBALL_BASE}/players/search/`,
            buildPlayerSearchParams(params)
        ),
        
getLeaguesMeta: () =>
    apiClient.get<ApiEnvelope<LeaguesMetaResponse>>(`${LIVEFOOTBALL_BASE}/leagues/meta/`),

getLeagueExpectedTable: (competitionId: number, params?: LeagueProjectionParams) =>
    apiClient.get<ApiEnvelope<LeagueExpectedTableResponse>>(
        `${LIVEFOOTBALL_BASE}/leagues/${competitionId}/expected-table/`,
        buildLeagueProjectionParams(params)
    ),

getLeagueComparison: (competitionId: number, params?: LeagueProjectionParams) =>
    apiClient.get<ApiEnvelope<LeagueCompareResponse>>(
        `${LIVEFOOTBALL_BASE}/leagues/${competitionId}/compare/`,
        buildLeagueProjectionParams(params)
    ),

    runLeagueScenario: (
        competitionId: number,
        params?: LeagueProjectionParams,
        lockedResults: LeagueScenarioLockedResultInput[] = []
    ) => {
        const projectionParams = buildLeagueProjectionParams(params);
        const queryString = projectionParams
            ? `?${new URLSearchParams(projectionParams).toString()}`
            : '';

        return apiClient.post<LeagueScenarioResponse>(
            `${LIVEFOOTBALL_BASE}/leagues/${competitionId}/scenario/${queryString}`,
            { locked_results: lockedResults }
        );
    },

    listSavedLeagueScenarios: (competitionId: number, params?: LeagueProjectionParams) =>
        apiClient.get<SavedLeagueScenarioListResponse>(
            `${LIVEFOOTBALL_BASE}/leagues/${competitionId}/saved-scenarios/`,
            buildLeagueProjectionParams(params)
        ),

    createSavedLeagueScenario: (
        competitionId: number,
        payload: CreateSavedLeagueScenarioPayload,
        params?: LeagueProjectionParams
    ) => {
        const projectionParams = buildLeagueProjectionParams(params);
        const queryString = projectionParams
            ? `?${new URLSearchParams(projectionParams).toString()}`
            : '';

        return apiClient.post<SavedLeagueScenarioDetail>(
            `${LIVEFOOTBALL_BASE}/leagues/${competitionId}/saved-scenarios/${queryString}`,
            payload
        );
    },

    getSavedLeagueScenario: (scenarioId: number) =>
        apiClient.get<SavedLeagueScenarioDetail>(
            `${LIVEFOOTBALL_BASE}/leagues/saved-scenarios/${scenarioId}/`
        ),

    deleteSavedLeagueScenario: (scenarioId: number) =>
        apiClient.delete<void>(
            `${LIVEFOOTBALL_BASE}/leagues/saved-scenarios/${scenarioId}/`
        ),
};

export const getLiveFootballOverview = async (): Promise<ApiEnvelope<LiveFootballOverview>> => {
    return apiClient.get<ApiEnvelope<LiveFootballOverview>>('/livefootball/overview/');
};

export {
    buildCompetitionTableParams,
    buildCompetitionFixturesParams,
    buildCompetitionPreviousNextFixturesParams,
    buildCompetitionScorersParams,
    buildCompetitionTeamsParams,
    buildTeamPlayersParams,
    buildCompetitionPlayersParams,
    buildPlayerSearchParams,
    buildLeagueProjectionParams,
};



export default liveFootballApi;