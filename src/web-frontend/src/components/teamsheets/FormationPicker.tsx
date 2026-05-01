import React from 'react';
import type { FormationWithTemplate } from '../../types/teamsheet';
import styles from './FormationPicker.module.css';

interface FormationPickerProps {
  formations: FormationWithTemplate[];
  selectedFormation: string;
  onSelect: (formation: FormationWithTemplate) => void;
}

const getPositionColor = (position: string): string => {
  if (position === 'GK') return '#f59e0b';
  if (['CB', 'RB', 'LB', 'RWB', 'LWB'].includes(position)) return '#3b82f6';
  if (['CM', 'CDM', 'CAM', 'RM', 'LM'].includes(position)) return '#22c55e';
  if (['ST', 'CF', 'RW', 'LW'].includes(position)) return '#ef4444';
  return '#6b7280';
};

const FormationPickerMiniPitch: React.FC<{ formation: FormationWithTemplate }> = ({
  formation,
}) => {
  const w = 64;
  const h = 80;
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={styles.FormationPickerMiniPitch}
    >
      <rect width={w} height={h} fill="#173820" rx="3" />
      <rect x="0" y="0" width={w / 2} height={h} fill="rgba(0,0,0,0.08)" />
      <line
        x1="0" y1={h / 2} x2={w} y2={h / 2}
        stroke="rgba(255,255,255,0.25)" strokeWidth="0.5"
      />
      <circle
        cx={w / 2} cy={h / 2} r="8"
        fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="0.5"
      />
      <rect
        x="1" y="1" width={w - 2} height={h - 2}
        fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="0.7" rx="2"
      />
      {formation.positions.map((pos, i) => (
        <circle
          key={i}
          cx={(pos.x / 100) * w}
          cy={((100 - pos.y) / 100) * h}
          r="3.5"
          fill={getPositionColor(pos.position)}
        />
      ))}
    </svg>
  );
};

const FormationPicker: React.FC<FormationPickerProps> = ({
  formations,
  selectedFormation,
  onSelect,
}) => {
  return (
    <div className={styles.FormationPickerContainer}>
      <div className={styles.FormationPickerTabStrip}>
        {formations.map(f => (
          <button
            key={f.value}
            type="button"
            className={`${styles.FormationPickerTab} ${
              selectedFormation === f.value ? styles.FormationPickerTabActive : ''
            }`}
            onClick={() => onSelect(f)}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default FormationPicker;
export { FormationPickerMiniPitch };