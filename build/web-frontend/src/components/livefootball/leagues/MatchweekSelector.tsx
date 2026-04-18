import React from 'react';
import styles from './css/SeasonSelector.module.css';

interface MatchweekSelectorProps {
  value: number;
  onChange: (matchweek: number) => void;
  disabled?: boolean;
  maxMatchweek?: number | null;
}

const MatchweekSelector: React.FC<MatchweekSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  maxMatchweek,
}) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const nextValue = Number(event.target.value);

    if (!Number.isFinite(nextValue)) {
      return;
    }

    if (nextValue < 1) {
      onChange(1);
      return;
    }

    if (maxMatchweek && nextValue > maxMatchweek) {
      onChange(maxMatchweek);
      return;
    }

    onChange(nextValue);
  };

  return (
    <div className={styles.container}>
      <label className={styles.label} htmlFor="matchweek-selector">
        Matchweek
      </label>

      <input
        id="matchweek-selector"
        className={styles.select}
        type="number"
        min={1}
        max={maxMatchweek ?? undefined}
        step={1}
        value={value}
        onChange={handleChange}
        disabled={disabled}
      />
    </div>
  );
};

export default MatchweekSelector;