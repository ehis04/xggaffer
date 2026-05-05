import { useCallback, useMemo, useState } from 'react';
import type {
  CompetitionListItem,
  PlayerLookupItem,
  TeamLookupItem,
} from '../types/livefootball';

export interface UsePlayerDiscoveryOptions {
  initialCompetition?: CompetitionListItem | null;
  initialTeam?: TeamLookupItem | null;
  initialPlayer?: PlayerLookupItem | null;
  initialSearchQuery?: string;
  initialSearchResult?: PlayerLookupItem | null;
}

export interface UsePlayerDiscoveryReturn {
  selectedCompetition: CompetitionListItem | null;
  selectedCompetitionId: number | null;
  selectedTeam: TeamLookupItem | null;
  selectedTeamId: number | null;
  selectedPlayer: PlayerLookupItem | null;
  selectedPlayerDirectoryId: number | null;
  selectedSearchResult: PlayerLookupItem | null;
  searchQuery: string;
  resolvedActivePlayer: PlayerLookupItem | null;
  resolvedCanonicalPlayerId: number | null;
  canOpenResolvedProfile: boolean;
  setCompetition: (competition: CompetitionListItem | null) => void;
  setTeam: (team: TeamLookupItem | null) => void;
  setPlayer: (player: PlayerLookupItem | null) => void;
  setSearchQuery: (query: string) => void;
  selectSearchResult: (player: PlayerLookupItem | null) => void;
  clearSearchResult: () => void;
  clearPlayer: () => void;
  clearTeam: () => void;
  clearCompetition: () => void;
  resetAll: () => void;
  getCanonicalPlayerId: (player?: PlayerLookupItem | null) => number | null;
}

const getCanonicalPlayerIdFromLookup = (player?: PlayerLookupItem | null): number | null => {
  const value = player?.canonical_player?.id;
  return typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null;
};

export const usePlayerDiscovery = (
  options: UsePlayerDiscoveryOptions = {}
): UsePlayerDiscoveryReturn => {
  const [selectedCompetition, setSelectedCompetition] = useState<CompetitionListItem | null>(
    options.initialCompetition ?? null
  );
  const [selectedTeam, setSelectedTeamState] = useState<TeamLookupItem | null>(
    options.initialTeam ?? null
  );
  const [selectedPlayer, setSelectedPlayerState] = useState<PlayerLookupItem | null>(
    options.initialPlayer ?? null
  );
  const [selectedSearchResult, setSelectedSearchResult] = useState<PlayerLookupItem | null>(
    options.initialSearchResult ?? null
  );
  const [searchQuery, setSearchQueryState] = useState<string>(
    options.initialSearchQuery ?? ''
  );

  const setCompetition = useCallback((competition: CompetitionListItem | null) => {
    setSelectedCompetition(competition);
    setSelectedTeamState(null);
    setSelectedPlayerState(null);
    setSelectedSearchResult(null);
  }, []);

  const setTeam = useCallback((team: TeamLookupItem | null) => {
    setSelectedTeamState(team);
    setSelectedPlayerState(null);
    setSelectedSearchResult(null);
  }, []);

  const setPlayer = useCallback((player: PlayerLookupItem | null) => {
    setSelectedPlayerState(player);
    setSelectedSearchResult(null);
  }, []);

  const selectSearchResult = useCallback((player: PlayerLookupItem | null) => {
    setSelectedSearchResult(player);
    setSelectedPlayerState(player);
  }, []);

  const setSearchQuery = useCallback((query: string) => {
    setSearchQueryState(query);
  }, []);

  const clearSearchResult = useCallback(() => {
    setSelectedSearchResult(null);
  }, []);

  const clearPlayer = useCallback(() => {
    setSelectedPlayerState(null);
    setSelectedSearchResult(null);
  }, []);

  const clearTeam = useCallback(() => {
    setSelectedTeamState(null);
    setSelectedPlayerState(null);
    setSelectedSearchResult(null);
  }, []);

  const clearCompetition = useCallback(() => {
    setSelectedCompetition(null);
    setSelectedTeamState(null);
    setSelectedPlayerState(null);
    setSelectedSearchResult(null);
  }, []);

  const resetAll = useCallback(() => {
    setSelectedCompetition(null);
    setSelectedTeamState(null);
    setSelectedPlayerState(null);
    setSelectedSearchResult(null);
    setSearchQueryState('');
  }, []);

  const resolvedActivePlayer = useMemo(
    () => selectedSearchResult ?? selectedPlayer ?? null,
    [selectedPlayer, selectedSearchResult]
  );

  const resolvedCanonicalPlayerId = useMemo(
    () => getCanonicalPlayerIdFromLookup(resolvedActivePlayer),
    [resolvedActivePlayer]
  );

  const selectedCompetitionId = selectedCompetition?.id ?? null;
  const selectedTeamId = selectedTeam?.id ?? null;
  const selectedPlayerDirectoryId = selectedPlayer?.id ?? null;
  const canOpenResolvedProfile = resolvedCanonicalPlayerId !== null;

  const getCanonicalPlayerId = useCallback(
    (player?: PlayerLookupItem | null) => getCanonicalPlayerIdFromLookup(player),
    []
  );

  return {
    selectedCompetition,
    selectedCompetitionId,
    selectedTeam,
    selectedTeamId,
    selectedPlayer,
    selectedPlayerDirectoryId,
    selectedSearchResult,
    searchQuery,
    resolvedActivePlayer,
    resolvedCanonicalPlayerId,
    canOpenResolvedProfile,
    setCompetition,
    setTeam,
    setPlayer,
    setSearchQuery,
    selectSearchResult,
    clearSearchResult,
    clearPlayer,
    clearTeam,
    clearCompetition,
    resetAll,
    getCanonicalPlayerId,
  };
};

export default usePlayerDiscovery;