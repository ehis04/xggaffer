import React, { useMemo } from 'react';
import type { LeagueMetaItem } from '../../../types/livefootball';
import styles from './css/SeasonSelector.module.css';

interface LeagueSelectorProps {
  leagues: LeagueMetaItem[];
  value: number | null;
  onChange: (competitionId: number) => void;
  disabled?: boolean;
}

const LeagueSelector: React.FC<LeagueSelectorProps> = ({
  leagues,
  value,
  onChange,
  disabled = false,
}) => {
  const currentIndex = useMemo(
    () => leagues.findIndex((league) => league.id === value),
    [leagues, value]
  );

  const canGoPrevious = !disabled && currentIndex > 0;
  const canGoNext = !disabled && currentIndex >= 0 && currentIndex < leagues.length - 1;

  const handlePrevious = (): void => {
    if (!canGoPrevious) {
      return;
    }
    onChange(leagues[currentIndex - 1].id);
  };

  const handleNext = (): void => {
    if (!canGoNext) {
      return;
    }
    onChange(leagues[currentIndex + 1].id);
  };

  return (
    <div className={styles.container}>
      <label className={styles.label} htmlFor="league-selector">
        League
      </label>

      <div className={styles.controls}>
        <button
          type="button"
          className={styles.arrowButton}
          onClick={handlePrevious}
          disabled={!canGoPrevious}
          aria-label="Previous league"
        >
          ‹
        </button>

        <select
          id="league-selector"
          className={styles.select}
          value={value ?? ''}
          onChange={(event) => onChange(Number(event.target.value))}
          disabled={disabled || leagues.length === 0}
        >
          {leagues.map((league) => (
            <option key={league.id} value={league.id}>
              {league.name}
            </option>
          ))}
        </select>

        <button
          type="button"
          className={styles.arrowButton}
          onClick={handleNext}
          disabled={!canGoNext}
          aria-label="Next league"
        >
          ›
        </button>
      </div>
    </div>
  );
};

export default LeagueSelector;