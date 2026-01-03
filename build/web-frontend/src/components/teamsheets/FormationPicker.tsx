import React from 'react';
import type { FormationWithTemplate } from '../../types/teamsheet';
import styles from './FormationPicker.module.css';

interface FormationPickerProps {
  formations: FormationWithTemplate[];
  selectedFormation: string;
  onSelect: (formation: FormationWithTemplate) => void;
}

const FormationPicker: React.FC<FormationPickerProps> = ({
  formations,
  selectedFormation,
  onSelect,
}) => {
  const renderMiniPitch = (formation: FormationWithTemplate) => {
    const width = 80;
    const height = 100;

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className={styles.miniPitch}>
        <rect x="0" y="0" width={width} height={height} fill="#2d5a3d" rx="4" />
        <line x1="0" y1={height / 2} x2={width} y2={height / 2} stroke="rgba(255,255,255,0.3)" strokeWidth="0.5" />
        <circle cx={width / 2} cy={height / 2} r="8" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.5" />
        
        {formation.positions.map((pos, idx) => (
          <circle
            key={idx}
            cx={(pos.x / 100) * width}
            cy={((100 - pos.y) / 100) * height}
            r="4"
            fill={getPositionColor(pos.position)}
          />
        ))}
      </svg>
    );
  };

  return (
    <div className={styles.container}>
      <label className={styles.label}>Select Formation</label>
      <div className={styles.grid}>
        {formations.map((formation) => (
          <button
            key={formation.value}
            type="button"
            className={`${styles.card} ${selectedFormation === formation.value ? styles.selected : ''}`}
            onClick={() => onSelect(formation)}
          >
            {renderMiniPitch(formation)}
            <span className={styles.formationName}>{formation.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

const getPositionColor = (position: string): string => {
  if (position === 'GK') return '#f59e0b';
  if (['CB', 'RB', 'LB', 'RWB', 'LWB'].includes(position)) return '#3b82f6';
  if (['CM', 'CDM', 'CAM', 'RM', 'LM'].includes(position)) return '#22c55e';
  if (['ST', 'CF', 'RW', 'LW'].includes(position)) return '#ef4444';
  return '#6b7280';
};

export default FormationPicker;