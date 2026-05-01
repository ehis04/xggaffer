import React from 'react';
import type { SlotState } from '../../types/teamsheet';
import styles from './PlayerSlotSelector.module.css';

interface PlayerSlotSelectorProps {
  slots: SlotState[];
  selectedSlot: number | null;
  onSlotClick: (slotNumber: number) => void;
  onRemovePlayer: (slotNumber: number) => void;
}

const getPositionColor = (position: string): string => {
  if (position === 'GK') return '#f59e0b';
  if (['CB', 'RB', 'LB', 'RWB', 'LWB'].includes(position)) return '#3b82f6';
  if (['CM', 'CDM', 'CAM', 'RM', 'LM'].includes(position)) return '#22c55e';
  if (['ST', 'CF', 'RW', 'LW'].includes(position)) return '#ef4444';
  return '#6b7280';
};

const PlayerSlotSelector: React.FC<PlayerSlotSelectorProps> = ({
  slots,
  selectedSlot,
  onSlotClick,
  onRemovePlayer,
}) => {
  const starters    = slots.filter(s => !s.is_substitute).sort((a, b) => a.slot_number - b.slot_number);
  const substitutes = slots.filter(s =>  s.is_substitute).sort((a, b) => a.slot_number - b.slot_number);

  const getDisplayName = (slot: SlotState) =>
    slot.player?.display_name ?? slot.player?.full_name ?? slot.custom_name ?? null;

  const getDisplayNumber = (slot: SlotState) =>
    slot.player?.squad_number ?? slot.custom_number ?? slot.slot_number;

  return (
    <div className={styles.PlayerSlotSelectorContainer}>
      <div className={styles.PlayerSlotSelectorSection}>
        <h3 className={styles.PlayerSlotSelectorSectionTitle}>Starting XI</h3>
        <div className={styles.PlayerSlotSelectorGrid}>
          {starters.map(slot => (
            <PlayerSlotSelectorCard
              key={slot.slot_number}
              slot={slot}
              displayName={getDisplayName(slot)}
              displayNumber={getDisplayNumber(slot)}
              isSelected={selectedSlot === slot.slot_number}
              onClick={() => onSlotClick(slot.slot_number)}
              onRemove={() => onRemovePlayer(slot.slot_number)}
            />
          ))}
        </div>
      </div>

      {substitutes.length > 0 && (
        <div className={styles.PlayerSlotSelectorSection}>
          <h3 className={styles.PlayerSlotSelectorSectionTitle}>Substitutes</h3>
          <div className={styles.PlayerSlotSelectorGrid}>
            {substitutes.map(slot => (
              <PlayerSlotSelectorCard
                key={slot.slot_number}
                slot={slot}
                displayName={getDisplayName(slot)}
                displayNumber={getDisplayNumber(slot)}
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

interface PlayerSlotSelectorCardProps {
  slot: SlotState;
  displayName: string | null;
  displayNumber: number;
  isSelected: boolean;
  onClick: () => void;
  onRemove: () => void;
}

const PlayerSlotSelectorCard: React.FC<PlayerSlotSelectorCardProps> = ({
  slot,
  displayName,
  displayNumber,
  isSelected,
  onClick,
  onRemove,
}) => {
  const isEmpty = !slot.player && !slot.custom_name;

  return (
    <div
      className={[
        styles.PlayerSlotSelectorCard,
        isSelected ? styles.PlayerSlotSelectorSelected : '',
        isEmpty    ? styles.PlayerSlotSelectorEmpty    : '',
      ].join(' ')}
      onClick={onClick}
    >
      <div
        className={styles.PlayerSlotSelectorPosBadge}
        style={{ backgroundColor: getPositionColor(slot.position_label) }}
      >
        {slot.position_label}
      </div>

      <div className={styles.PlayerSlotSelectorContent}>
        {isEmpty ? (
          <span className={styles.PlayerSlotSelectorEmptyText}>Select Player</span>
        ) : (
          <>
            <span className={styles.PlayerSlotSelectorPlayerNum}>
              #{displayNumber}
            </span>
            <span className={styles.PlayerSlotSelectorPlayerName}>
              {displayName}
            </span>
          </>
        )}
      </div>

      {!isEmpty && (
        <button
          type="button"
          className={styles.PlayerSlotSelectorRemoveBtn}
          onClick={e => { e.stopPropagation(); onRemove(); }}
          aria-label="Remove player"
        >
          ×
        </button>
      )}
    </div>
  );
};

export default PlayerSlotSelector;