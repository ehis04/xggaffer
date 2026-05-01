import React from 'react';
import styles from './css/MatchPredictionChip.module.css';

interface MatchPredictionChipProps {
  homeProb: number | null;
  drawProb: number | null;
  awayProb: number | null;
  isLoading: boolean;
}

const MatchPredictionChip: React.FC<MatchPredictionChipProps> = ({
  homeProb,
  drawProb,
  awayProb,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className={styles.chip}>
        <span className={styles.skeleton} />
        <span className={styles.skeleton} />
        <span className={styles.skeleton} />
      </div>
    );
  }

  if (homeProb === null || drawProb === null || awayProb === null) {
    return <div className={styles.chip}><span className={styles.unavailable}>—</span></div>;
  }

  return (
    <div className={styles.chip}>
      <span className={styles.cell}>{Math.round(homeProb * 100)}%</span>
      <span className={styles.divider}>·</span>
      <span className={styles.cell}>{Math.round(drawProb * 100)}%</span>
      <span className={styles.divider}>·</span>
      <span className={styles.cell}>{Math.round(awayProb * 100)}%</span>
    </div>
  );
};

export default MatchPredictionChip;