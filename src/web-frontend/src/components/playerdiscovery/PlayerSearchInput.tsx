import React, { useMemo, useState } from 'react';
import liveFootballApi from '../../services/api/livefootballApi';
import type { PlayerLookupItem } from '../../types/livefootball';

const normalizeError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object') {
    const values = Object.values(error as Record<string, unknown>).flatMap((value) => {
      if (Array.isArray(value)) {
        return value.map(String);
      }

      return [String(value)];
    });

    if (values.length > 0) {
      return values.join(' ');
    }
  }

  return 'Unable to search players.';
};

const buildSecondaryLine = (player: PlayerLookupItem): string => {
  const bits = [
    player.team?.name || null,
    player.primary_position || player.raw_position || null,
    player.nationality || null,
    player.squad_number ? `#${player.squad_number}` : null,
  ].filter(Boolean);

  return bits.join(' · ');
};

export interface PlayerSearchInputProps {
  query: string;
  onQueryChange: (value: string) => void;
  onSelectResult?: (player: PlayerLookupItem) => void;
  onOpenProfile?: (canonicalPlayerId: number, player: PlayerLookupItem) => void;
  competitionId?: number | null;
  teamId?: number | null;
  season?: string;
  activeOnly?: boolean;
  limit?: number;
  minQueryLength?: number;
  disabled?: boolean;
  placeholder?: string;
  helperText?: string;
  emptyStateText?: string;
  noResultsText?: string;
  className?: string;
}

const PlayerSearchInput: React.FC<PlayerSearchInputProps> = ({
  query,
  onQueryChange,
  onSelectResult,
  onOpenProfile,
  competitionId = null,
  teamId = null,
  season,
  activeOnly = true,
  limit = 10,
  minQueryLength = 2,
  disabled = false,
  placeholder = 'Search player name',
  helperText,
  emptyStateText = 'Search for a player by name.',
  noResultsText = 'No players matched that search.',
  className,
}) => {
  const [results, setResults] = useState<PlayerLookupItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const trimmedQuery = useMemo(() => query.trim(), [query]);

  const validationMessage = useMemo(() => {
    if (!trimmedQuery) {
      return null;
    }

    if (trimmedQuery.length < minQueryLength) {
      return `Enter at least ${minQueryLength} characters to search.`;
    }

    return null;
  }, [trimmedQuery, minQueryLength]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!trimmedQuery || trimmedQuery.length < minQueryLength) {
      setHasSearched(true);
      setResults([]);
      setError(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setHasSearched(true);

      const response = await liveFootballApi.searchPlayers({
        q: trimmedQuery,
        competition_id: competitionId || undefined,
        team_id: teamId || undefined,
        season: season?.trim() || undefined,
        active_only: activeOnly,
        limit,
      });

      setResults(response.items);
    } catch (err) {
      setResults([]);
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    onQueryChange('');
    setResults([]);
    setError(null);
    setHasSearched(false);
  };

  const renderResultActions = (player: PlayerLookupItem) => {
    const canonicalPlayerId = player.canonical_player?.id || null;
    const canOpenProfile = Boolean(canonicalPlayerId && onOpenProfile);

    return (
      <div>
        <button
          type="button"
          onClick={() => onSelectResult?.(player)}
          disabled={disabled}
        >
          Use result
        </button>

        <button
          type="button"
          onClick={() => {
            if (canonicalPlayerId && onOpenProfile) {
              onOpenProfile(canonicalPlayerId, player);
            }
          }}
          disabled={disabled || !canOpenProfile}
        >
          Open profile
        </button>
      </div>
    );
  };

  return (
    <div className={className}>
      <form onSubmit={handleSubmit}>
        <label htmlFor="player-search-input">Player search</label>

        <div>
          <input
            id="player-search-input"
            type="text"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder={placeholder}
            disabled={disabled || loading}
            autoComplete="off"
          />

          <button type="submit" disabled={disabled || loading}>
            {loading ? 'Searching…' : 'Search'}
          </button>

          <button
            type="button"
            onClick={handleClear}
            disabled={disabled || loading || (!query && results.length === 0)}
          >
            Clear
          </button>
        </div>
      </form>

      {helperText ? <div>{helperText}</div> : null}

      {competitionId || teamId || season ? (
        <div>
          <small>
            Search scope:
            {competitionId ? ` competition ${competitionId}` : ''}
            {teamId ? `${competitionId ? ' ·' : ''} team ${teamId}` : ''}
            {season ? `${competitionId || teamId ? ' ·' : ''} season ${season}` : ''}
          </small>
        </div>
      ) : null}

      {validationMessage ? <div role="status">{validationMessage}</div> : null}
      {error ? <div role="alert">{error}</div> : null}

      {!loading && !error && !hasSearched ? (
        <div>{emptyStateText}</div>
      ) : null}

      {!loading && !error && hasSearched && trimmedQuery.length >= minQueryLength && results.length === 0 ? (
        <div>{noResultsText}</div>
      ) : null}

      {results.length > 0 ? (
        <div>
          {results.map((player) => {
            const canonicalPlayerId = player.canonical_player?.id || null;
            const secondaryLine = buildSecondaryLine(player);

            return (
              <div key={player.id}>
                <div>
                  <strong>{player.player_name}</strong>
                </div>

                {secondaryLine ? <div>{secondaryLine}</div> : null}

                <div>
                  <small>
                    {canonicalPlayerId
                      ? `Canonical profile available (${canonicalPlayerId})`
                      : 'No canonical profile link available yet'}
                  </small>
                </div>

                {renderResultActions(player)}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
};

export default PlayerSearchInput;