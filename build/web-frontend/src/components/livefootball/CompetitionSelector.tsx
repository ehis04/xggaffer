/**
 * CompetitionSelector.tsx
 *
 * Reusable dropdown for picking a tracked competition (league/cup).
 * Renders a labelled <select> with a helper/error text area below.
 *
 * CSS: CompetitionSelector.module.css  (prefix: lfcs-)
 */

import React, { useMemo } from 'react';
import type { CompetitionListItem } from '../../types/livefootball';
import styles from './css/CompetitionSelector.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const buildCompetitionLabel = (competition: CompetitionListItem): string => {
  const secondaryBits = [
    competition.code || null,
    competition.area_name || null,
    competition.current_season_label || null,
  ].filter(Boolean);

  return secondaryBits.length === 0
    ? competition.name
    : `${competition.name} (${secondaryBits.join(' · ')})`;
};

// ─── Props ────────────────────────────────────────────────────────────────────

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

// ─── Component ────────────────────────────────────────────────────────────────

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
    () => competitions.find((c) => c.id === value) ?? null,
    [competitions, value],
  );

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextValue = event.target.value.trim();
    if (!nextValue) { onChange(null); return; }

    const parsedId = Number(nextValue);
    if (!Number.isInteger(parsedId) || parsedId <= 0) { onChange(null); return; }

    onChange(competitions.find((c) => c.id === parsedId) ?? null);
  };

  const selectPlaceholder = loading
    ? 'Loading competitions…'
    : competitions.length === 0
      ? emptyStateText
      : placeholder;

  return (
    <div className={`${styles['lfcs-root']} ${className ?? ''}`}>
      <label className={styles['lfcs-label']} htmlFor={id}>
        {label}
        {required && <span className={styles['lfcs-required']}> *</span>}
      </label>

      <select
        className={`${styles['lfcs-select']} ${error ? styles['lfcs-select--error'] : ''}`}
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

      {helperText && (
        <div className={styles['lfcs-helper']}>{helperText}</div>
      )}

      {selectedCompetition && (
        <div className={styles['lfcs-selected-meta']}>
          {selectedCompetition.name}
          {selectedCompetition.area_name ? ` · ${selectedCompetition.area_name}` : ''}
          {selectedCompetition.current_season_label
            ? ` · ${selectedCompetition.current_season_label}`
            : ''}
        </div>
      )}

      {error && (
        <div className={styles['lfcs-error']} role="alert">{error}</div>
      )}
    </div>
  );
};

export default CompetitionSelector;