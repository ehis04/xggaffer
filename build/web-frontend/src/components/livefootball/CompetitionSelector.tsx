import React, { useMemo } from 'react';
import type { CompetitionListItem } from '../../types/livefootball';

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

export interface CompetitionSelectorProps {
  competitions: CompetitionListItem[];
  value: number | null;
  onChange: (competition: CompetitionListItem | null) => void;
  loading?: boolean;
  error?: string | null;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  placeholder?: string;
  emptyStateText?: string;
  helperText?: string;
  id?: string;
  name?: string;
  className?: string;
}

const CompetitionSelector: React.FC<CompetitionSelectorProps> = ({
  competitions,
  value,
  onChange,
  loading = false,
  error = null,
  disabled = false,
  required = false,
  label = 'Competition',
  placeholder = 'Select a competition',
  emptyStateText = 'No competitions available',
  helperText,
  id = 'competition-selector',
  name = 'competition',
  className,
}) => {
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

  const selectPlaceholder =
    loading
      ? 'Loading competitions…'
      : competitions.length === 0
        ? emptyStateText
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
        disabled={disabled || loading || competitions.length === 0}
        required={required}
      >
        <option value="">{selectPlaceholder}</option>

        {competitions.map((competition) => (
          <option key={competition.id} value={competition.id}>
            {buildCompetitionLabel(competition)}
          </option>
        ))}
      </select>

      {helperText ? <div>{helperText}</div> : null}

      {selectedCompetition ? (
        <div>
          <small>
            Selected: {selectedCompetition.name}
            {selectedCompetition.area_name ? ` · ${selectedCompetition.area_name}` : ''}
            {selectedCompetition.current_season_label
              ? ` · ${selectedCompetition.current_season_label}`
              : ''}
          </small>
        </div>
      ) : null}

      {error ? <div role="alert">{error}</div> : null}
    </div>
  );
};

export default CompetitionSelector;