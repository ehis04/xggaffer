export const queryKeys = {
    livefootball: {
        overview: () => ['livefootball', 'overview'] as const,
        leaguesMeta: () => ['livefootball', 'leaguesMeta'] as const,
        expectedTable: (competitionId: number, params: Record<string, string | undefined>) =>
            ['livefootball', 'expectedTable', competitionId, params] as const,
        compare: (competitionId: number, params: Record<string, string | undefined>) =>
            ['livefootball', 'compare', competitionId, params] as const,
    },
    predictions: {
        modelInfo: () => ['predictions', 'modelInfo'] as const,
        teams: (league: string, season: string) =>
            ['predictions', 'teams', league, season] as const,
        odds: {
            fixtures: (league: string, view: string, teamA?: string, teamB?: string) =>
                ['predictions', 'odds', 'fixtures', league, view, teamA ?? '', teamB ?? ''] as const,
            teams: (league: string) =>
                ['predictions', 'odds', 'teams', league] as const,
            accuracy: (league: string, season: string) =>
                ['predictions', 'odds', 'accuracy', league, season] as const,
        },
    },
} as const;
