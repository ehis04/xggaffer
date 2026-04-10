import React, { useEffect, useMemo, useRef, useState } from 'react';
import liveFootballApi from '../../services/api/livefootballApi';
import type { TeamLookupItem } from '../../types/livefootball';

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

  return 'Unable to load clubs.';
};

const buildTeamLabel = (team: TeamLookupItem): string => {
  const secondaryBits = [
    team.short_name || null,
    team.tla || null,
    team.season_label || null,
  ].filter(Boolean);

  if (secondaryBits.length === 0) {
    return team.name;
  }

  return `${team.name} (${secondaryBits.join(' · ')})`;
};

export interface ClubSelectorProps {
  competitionId: number | null;
  value: number | null;
  onChange: (team: TeamLookupItem | null) => void;
  season?: string;
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

const ClubSelector: React.FC<ClubSelectorProps> = ({
  competitionId,
  value,
  onChange,
  season,
  disabled = false,
  required = false,
  label = 'Club',
  placeholder = 'Select a club',
  helperText,
  emptyStateText = 'Select a league first',
  id,
  name,
  className,
}) => {
  const [teams, setTeams] = useState<TeamLookupItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const valueRef = useRef(value);
  valueRef.current = value;

  useEffect(() => {
    if (!competitionId) {
      setTeams([]);
      setError(null);

      if (valueRef.current !== null) {
        onChangeRef.current(null);
      }

      return;
    }

    let isActive = true;

    const loadTeams = async () => {
      try {
        setLoading(true);
        setError(null);

        const result = await liveFootballApi.getCompetitionTeams(competitionId, {
          season: season?.trim() || undefined,
        });

        if (!isActive) {
          return;
        }

        setTeams(result.items);
      } catch (err) {
        if (!isActive) {
          return;
        }

        setTeams([]);
        setError(normalizeError(err));
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void loadTeams();

    return () => {
      isActive = false;
    };
  }, [competitionId, season]);

  useEffect(() => {
    if (value === null) {
      return;
    }

    const selectedStillExists = teams.some((team) => team.id === value);

    if (!selectedStillExists) {
      onChangeRef.current(null);
    }
  }, [teams, value]);

  const selectedValue = value ? String(value) : '';

  const selectedTeam = useMemo(
    () => teams.find((team) => team.id === value) ?? null,
    [teams, value]
  );

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

    const nextTeam = teams.find((team) => team.id === parsedId) ?? null;
    onChange(nextTeam);
  };

  const selectPlaceholder = !competitionId
    ? emptyStateText
    : loading
      ? 'Loading clubs…'
      : placeholder;

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
        disabled={disabled || loading || !competitionId}
        required={required}
      >
        <option value="">{selectPlaceholder}</option>

        {teams.map((team) => (
          <option key={team.id} value={team.id}>
            {buildTeamLabel(team)}
          </option>
        ))}
      </select>

      {helperText ? <div>{helperText}</div> : null}

      {selectedTeam ? (
        <div>
          <small>
            Selected: {selectedTeam.name}
            {selectedTeam.venue ? ` · ${selectedTeam.venue}` : ''}
          </small>
        </div>
      ) : null}

      {error ? <div role="alert">{error}</div> : null}
    </div>
  );
};

export default ClubSelector;