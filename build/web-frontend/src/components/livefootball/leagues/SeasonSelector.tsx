import React from 'react';
import styles from './css/SeasonSelector.module.css';

interface SeasonSelectorProps {
  seasons: string[];
  value: string | null;
  onChange: (season: string) => void;
  disabled?: boolean;
}

const SeasonSelector: React.FC<SeasonSelectorProps> = ({
  seasons,
  value,
  onChange,
  disabled = false,
}) => {
  return (
    <div className={styles.container}>
      <label className={styles.label} htmlFor="season-selector">
        Season
      </label>

      <select
        id="season-selector"
        className={styles.select}
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || seasons.length === 0}
      >
        {seasons.map((season) => (
          <option key={season} value={season}>
            {season}
          </option>
        ))}
      </select>
    </div>
  );
};

export default SeasonSelector;