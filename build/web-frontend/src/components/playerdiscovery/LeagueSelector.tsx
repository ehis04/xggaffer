import React, { useEffect, useMemo, useState } from 'react';
import liveFootballApi from '../../services/api/livefootballApi';
import type { CompetitionListItem } from '../../types/livefootball';

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

  return 'Unable to load leagues.';
};

const buildCompetitionLabel = (competition: CompetitionListItem): string => {
  const secondaryBits = [
    competition.code || null,
    competition.area_name || null,
    competition.current_season_label || null,
  ].filter(Boolean);

  if (secondaryBits.length === 0) {
    return competition.name;
  }

  return `${competition.name} (${secondaryBits.join(' · ')})`;
};

export interface LeagueSelectorProps {
  value: number | null;
  onChange: (competition: CompetitionListItem | null) => void;
  provider?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  placeholder?: string;
  helperText?: string;
  id?: string;
  name?: string;
  className?: string;
}

const LeagueSelector: React.FC<LeagueSelectorProps> = ({
  value,
  onChange,
  provider,
  disabled = false,
  required = false,
  label = 'League',
  placeholder = 'Select a league',
  helperText,
  id,
  name,
  className,
}) => {
  const [competitions, setCompetitions] = useState<CompetitionListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const loadCompetitions = async () => {
      try {
        setLoading(true);
        setError(null);

        const result = await liveFootballApi.getCompetitions(provider);

        if (!isActive) {
          return;
        }

        setCompetitions(result);
      } catch (err) {
        if (!isActive) {
          return;
        }

        setCompetitions([]);
        setError(normalizeError(err));
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void loadCompetitions();

    return () => {
      isActive = false;
    };
  }, [provider]);

  const selectedValue = value ? String(value) : '';

  const selectedCompetition = useMemo(
    () => competitions.find((competition) => competition.id === value) ?? null,
    [competitions, value]
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

    const nextCompetition =
      competitions.find((competition) => competition.id === parsedId) ?? null;

    onChange(nextCompetition);
  };

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
        disabled={disabled || loading}
        required={required}
      >
        <option value="">{loading ? 'Loading leagues…' : placeholder}</option>

        {competitions.map((competition) => (
          <option key={competition.id} value={competition.id}>
            {buildCompetitionLabel(competition)}
          </option>
        ))}
      </select>

      {helperText ? <div>{helperText}</div> : null}

      {selectedCompetition?.emblem_url ? (
        <div>
          <small>Selected: {selectedCompetition.name}</small>
        </div>
      ) : selectedCompetition ? (
        <div>
          <small>Selected: {selectedCompetition.name}</small>
        </div>
      ) : null}

      {error ? (
        <div role="alert">
          {error}
        </div>
      ) : null}
    </div>
  );
};

export default LeagueSelector;