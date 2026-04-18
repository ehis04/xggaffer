import React from 'react';
import type { SlotState } from '../../types/teamsheet';
import styles from './PlayerSlotSelector.module.css';

interface PlayerSlotSelectorProps {
  slots: SlotState[];
  selectedSlot: number | null;
  onSlotClick: (slotNumber: number) => void;
  onRemovePlayer: (slotNumber: number) => void;
}

const PlayerSlotSelector: React.FC<PlayerSlotSelectorProps> = ({
  slots,
  selectedSlot,
  onSlotClick,
  onRemovePlayer,
}) => {
  const starters = slots.filter(s => !s.is_substitute).sort((a, b) => a.slot_number - b.slot_number);
  const substitutes = slots.filter(s => s.is_substitute).sort((a, b) => a.slot_number - b.slot_number);

  const getSlotDisplayName = (slot: SlotState) => {
    if (slot.player) {
      return slot.player.display_name || slot.player.full_name;
    }
    if (slot.custom_name) {
      return slot.custom_name;
    }
    return null;
  };

  const getSlotNumber = (slot: SlotState) => {
    if (slot.player?.squad_number) return slot.player.squad_number;
    if (slot.custom_number) return slot.custom_number;
    return slot.slot_number;
  };

  return (
    <div className={styles.container}>
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Starting XI</h3>
        <div className={styles.slotGrid}>
          {starters.map(slot => (
            <SlotCard
              key={slot.slot_number}
              slot={slot}
              displayName={getSlotDisplayName(slot)}
              displayNumber={getSlotNumber(slot)}
              isSelected={selectedSlot === slot.slot_number}
              onClick={() => onSlotClick(slot.slot_number)}
              onRemove={() => onRemovePlayer(slot.slot_number)}
            />
          ))}
        </div>
      </div>

      {substitutes.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Substitutes</h3>
          <div className={styles.slotGrid}>
            {substitutes.map(slot => (
              <SlotCard
                key={slot.slot_number}
                slot={slot}
                displayName={getSlotDisplayName(slot)}
                displayNumber={getSlotNumber(slot)}
                isSelected={selectedSlot === slot.slot_number}
                onClick={() => onSlotClick(slot.slot_number)}
                onRemove={() => onRemovePlayer(slot.slot_number)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

interface SlotCardProps {
  slot: SlotState;
  displayName: string | null;
  displayNumber: number;
  isSelected: boolean;
  onClick: () => void;
  onRemove: () => void;
}

const SlotCard: React.FC<SlotCardProps> = ({
  slot,
  displayName,
  displayNumber,
  isSelected,
  onClick,
  onRemove,
}) => {
  const isEmpty = !slot.player && !slot.custom_name;
  const positionColor = getPositionColor(slot.position_label);

  return (
    <div
      className={`${styles.slotCard} ${isSelected ? styles.selected : ''} ${isEmpty ? styles.empty : ''}`}
      onClick={onClick}
    >
      <div className={styles.positionBadge} style={{ backgroundColor: positionColor }}>
        {slot.position_label}
      </div>
      
      <div className={styles.slotContent}>
        {isEmpty ? (
          <span className={styles.emptyText}>Select Player</span>
        ) : (
          <>
            <span className={styles.playerNumber}>#{displayNumber}</span>
            <span className={styles.playerName}>{displayName}</span>
          </>
        )}
      </div>

      {!isEmpty && (
        <button
          type="button"
          className={styles.removeButton}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
        >
          ×
        </button>
      )}
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

export default PlayerSlotSelector;