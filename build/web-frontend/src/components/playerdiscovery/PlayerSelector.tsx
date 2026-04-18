import React, { useEffect, useMemo, useRef, useState } from 'react';
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

  return 'Unable to load players.';
};

const buildPlayerLabel = (player: PlayerLookupItem): string => {
  const secondaryBits = [
    player.primary_position || null,
    player.squad_number ? `#${player.squad_number}` : null,
    player.nationality || null,
  ].filter(Boolean);

  if (secondaryBits.length === 0) {
    return player.player_name;
  }

  return `${player.player_name} (${secondaryBits.join(' · ')})`;
};

export interface PlayerSelectorProps {
  competitionId?: number | null;
  teamId?: number | null;
  value: number | null;
  onChange: (player: PlayerLookupItem | null) => void;
  season?: string;
  activeOnly?: boolean;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  placeholder?: string;
  helperText?: string;
  emptyStateText?: string;
  id?: string;
  name?: string;
  className?: string;
}

const PlayerSelector: React.FC<PlayerSelectorProps> = ({
  competitionId = null,
  teamId = null,
  value,
  onChange,
  season,
  activeOnly = true,
  disabled = false,
  required = false,
  label = 'Player',
  placeholder = 'Select a player',
  helperText,
  emptyStateText = 'Select a league or club first',
  id,
  name,
  className,
}) => {
  const [players, setPlayers] = useState<PlayerLookupItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasSelectionContext = Boolean(teamId || competitionId);

  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const valueRef = useRef(value);
  valueRef.current = value;

  useEffect(() => {
    if (!hasSelectionContext) {
      setPlayers([]);
      setError(null);

      if (valueRef.current !== null) {
        onChangeRef.current(null);
      }

      return;
    }

    let isActive = true;

    const loadPlayers = async () => {
      try {
        setLoading(true);
        setError(null);

        const result = teamId
          ? await liveFootballApi.getTeamPlayers(teamId, {
              active_only: activeOnly,
            })
          : await liveFootballApi.getCompetitionPlayers(competitionId as number, {
              season: season?.trim() || undefined,
              active_only: activeOnly,
            });

        if (!isActive) {
          return;
        }

        setPlayers(result.items);
      } catch (err) {
        if (!isActive) {
          return;
        }

        setPlayers([]);
        setError(normalizeError(err));
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void loadPlayers();

    return () => {
      isActive = false;
    };
  }, [teamId, competitionId, season, activeOnly, hasSelectionContext]);

  useEffect(() => {
    if (value === null) {
      return;
    }

    const selectedStillExists = players.some((player) => player.id === value);

    if (!selectedStillExists) {
      onChangeRef.current(null);
    }
  }, [players, value]);

  const selectedPlayer = useMemo(
    () => players.find((player) => player.id === value) ?? null,
    [players, value]
  );

  const selectedValue = value ? String(value) : '';

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextValue = event.target.value.trim();

    if (!nextValue) {
      onChange(null);
      return;
    }

    const parsedId = Number(nextValue);

    if (!Number.isInteger(parsedId) || parsedId <= 0) {
      onChange(null);
      return;
    }

    const nextPlayer = players.find((player) => player.id === parsedId) ?? null;
    onChange(nextPlayer);
  };

  const selectPlaceholder = !hasSelectionContext
    ? emptyStateText
    : loading
      ? 'Loading players…'
      : placeholder;

  const canonicalStatusText = selectedPlayer?.canonical_player?.id
    ? `Canonical player linked: ${selectedPlayer.canonical_player.display_name || 'Yes'}`
    : selectedPlayer
      ? 'No canonical player link available yet.'
      : null;

  return (
    <div className={className}>
      <label htmlFor={id}>
        {label}
        {required ? ' *' : ''}
      </label>

      <select
        id={id}
        name={name}
        value={selectedValue}
        onChange={handleChange}
        disabled={disabled || loading || !hasSelectionContext}
        required={required}
      >
        <option value="">{selectPlaceholder}</option>

        {players.map((player) => (
          <option key={player.id} value={player.id}>
            {buildPlayerLabel(player)}
          </option>
        ))}
      </select>

      {helperText ? <div>{helperText}</div> : null}

      {selectedPlayer ? (
        <div>
          <small>
            Selected: {selectedPlayer.player_name}
            {selectedPlayer.team?.name ? ` · ${selectedPlayer.team.name}` : ''}
          </small>
          <br />
          <small>{canonicalStatusText}</small>
        </div>
      ) : null}

      {error ? <div role="alert">{error}</div> : null}
    </div>
  );
};

export default PlayerSelector;