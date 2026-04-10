import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { teamsheetApi } from '../../../services/api';
import type {
  TeamsheetChoices,
  FormationWithTemplate,
  AvailablePlayer,
  SlotState,
  CreateTeamsheetPayload,
  PlayerSlotAssignment,
} from '../../../types/teamsheet';
import { FormationPicker, PlayerSlotSelector, AvailablePlayersList } from '../../../components/teamsheets';
import styles from './TeamsheetCreatePage.module.css';

const getSlotDisplayName = (slot: SlotState): string => {
  if (slot.player) {
    return slot.player.display_name || slot.player.full_name;
  }

  if (slot.custom_name) {
    return slot.custom_name;
  }

  return 'No player assigned yet';
};

const getSlotDisplayNumber = (slot: SlotState): string => {
  if (slot.player?.squad_number) {
    return `#${slot.player.squad_number}`;
  }

  if (slot.custom_number) {
    return `#${slot.custom_number}`;
  }

  return `Slot ${slot.slot_number}`;
};

const getSlotOccupantType = (slot: SlotState): string => {
  if (slot.player) {
    return slot.player.source_type === 'club_member' ? 'Club member' : 'Public player';
  }

  if (slot.custom_name) {
    return 'Default player';
  }

  return 'Unassigned';
};

const getSlotHelperText = (slot: SlotState): string => {
  if (slot.player) {
    return 'Choose a different player below to replace the current assignment, or remove the player from the slot card.';
  }

  if (slot.custom_name) {
    return 'Choose a real player below to replace the default placeholder if needed.';
  }

  return 'Choose a player below or use the default-player option to fill this slot.';
};

const TeamsheetCreatePage: React.FC = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();

  const [choices, setChoices] = useState<TeamsheetChoices | null>(null);
  const [availablePlayers, setAvailablePlayers] = useState<AvailablePlayer[]>([]);
  const [loadingChoices, setLoadingChoices] = useState(true);
  const [loadingPlayers, setLoadingPlayers] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [selectedFormation, setSelectedFormation] = useState<FormationWithTemplate | null>(null);
  const [matchDate, setMatchDate] = useState('');
  const [opponent, setOpponent] = useState('');
  const [notes, setNotes] = useState('');
  const [isTemplate, setIsTemplate] = useState(false);

  const [slots, setSlots] = useState<SlotState[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [positionFilter, setPositionFilter] = useState('');

  useEffect(() => {
    if (!clubId) return;

    const fetchData = async () => {
      try {
        setLoadingChoices(true);
        const choicesData = await teamsheetApi.getChoices(Number(clubId));
        setChoices(choicesData);

        if (choicesData.formations_with_templates.length > 0) {
          const defaultFormation =
            choicesData.formations_with_templates.find((f) => f.value === '442') ||
            choicesData.formations_with_templates[0];
          handleFormationSelect(defaultFormation);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoadingChoices(false);
      }
    };

    fetchData();
  }, [clubId]);

  const fetchAvailablePlayers = useCallback(async (position?: string) => {
    if (!clubId) return;

    try {
      setLoadingPlayers(true);
      const assignedIds = slots
        .filter((s) => s.player)
        .map((s) => s.player!.id);

      const players = await teamsheetApi.getAvailablePlayers(Number(clubId), {
        position: position || undefined,
        exclude: assignedIds,
      });
      setAvailablePlayers(players);
    } catch (err) {
      console.error('Failed to load players:', err);
    } finally {
      setLoadingPlayers(false);
    }
  }, [clubId, slots]);

  useEffect(() => {
    if (selectedSlot !== null) {
      const slot = slots.find((s) => s.slot_number === selectedSlot);
      fetchAvailablePlayers(positionFilter || slot?.position_label);
    }
  }, [selectedSlot, positionFilter, fetchAvailablePlayers, slots]);

  const handleFormationSelect = (formation: FormationWithTemplate) => {
    setSelectedFormation(formation);

    const newSlots: SlotState[] = formation.positions.map((pos) => ({
      slot_number: pos.slot,
      position_label: pos.position,
      position_x: pos.x,
      position_y: pos.y,
      is_substitute: false,
      player: null,
      custom_name: undefined,
      custom_number: undefined,
    }));

    const subPositions = ['GK', 'CB', 'CB', 'CM', 'CM', 'ST', 'ST'];
    for (let i = 12; i <= 18; i++) {
      newSlots.push({
        slot_number: i,
        position_label: subPositions[i - 12] || 'MID',
        position_x: 50,
        position_y: 50,
        is_substitute: true,
        player: null,
        custom_name: undefined,
        custom_number: undefined,
      });
    }

    setSlots(newSlots);
    setSelectedSlot(null);
  };

  const handleSlotClick = (slotNumber: number) => {
    setSelectedSlot(slotNumber);
    setPositionFilter('');
  };

  const handlePlayerSelect = (player: AvailablePlayer) => {
    if (selectedSlot === null) return;

    setSlots((prev) => prev.map((slot) => {
      if (slot.slot_number === selectedSlot) {
        return {
          ...slot,
          player,
          custom_name: undefined,
          custom_number: undefined,
        };
      }
      return slot;
    }));

    const emptySlots = slots.filter(
      (s) => !s.player && !s.custom_name && s.slot_number !== selectedSlot
    );

    if (emptySlots.length > 0) {
      const nextEmpty = emptySlots.find((s) => s.slot_number > selectedSlot) || emptySlots[0];
      setSelectedSlot(nextEmpty.slot_number);
    } else {
      setSelectedSlot(null);
    }
  };

  const handleUseDefault = () => {
    if (selectedSlot === null) return;

    const slot = slots.find((s) => s.slot_number === selectedSlot);
    if (!slot) return;

    const defaultName = `${slot.position_label} #${slot.slot_number}`;

    setSlots((prev) => prev.map((s) => {
      if (s.slot_number === selectedSlot) {
        return {
          ...s,
          player: null,
          custom_name: defaultName,
          custom_number: s.slot_number,
        };
      }
      return s;
    }));

    const emptySlots = slots.filter(
      (s) => !s.player && !s.custom_name && s.slot_number !== selectedSlot
    );

    if (emptySlots.length > 0) {
      const nextEmpty = emptySlots.find((s) => s.slot_number > selectedSlot) || emptySlots[0];
      setSelectedSlot(nextEmpty.slot_number);
    } else {
      setSelectedSlot(null);
    }
  };

  const handleRemovePlayer = (slotNumber: number) => {
    setSlots((prev) => prev.map((slot) => {
      if (slot.slot_number === slotNumber) {
        return {
          ...slot,
          player: null,
          custom_name: undefined,
          custom_number: undefined,
        };
      }
      return slot;
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!clubId || !selectedFormation) return;
    if (!title.trim()) {
      setError('Title is required');
      return;
    }

    const playerAssignments: PlayerSlotAssignment[] = slots
      .filter((s) => s.player || s.custom_name)
      .map((s) => ({
        slot_number: s.slot_number,
        club_player_id: s.player?.id || null,
        custom_name: s.custom_name || '',
        custom_number: s.custom_number || null,
        position_label: s.position_label,
        position_x: s.position_x,
        position_y: s.position_y,
        is_substitute: s.is_substitute,
      }));

    const payload: CreateTeamsheetPayload = {
      title: title.trim(),
      formation: selectedFormation.value,
      match_date: matchDate || null,
      opponent: opponent.trim(),
      notes: notes.trim(),
      is_template: isTemplate,
      player_assignments: playerAssignments,
    };

    try {
      setSaving(true);
      setError(null);
      const teamsheet = await teamsheetApi.createWithPlayers(Number(clubId), payload);
      navigate(`/clubs/${clubId}/teamsheets/${teamsheet.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create teamsheet');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate(`/clubs/${clubId}/teamsheets`);
  };

  const selectedSlotState = useMemo(
    () => (selectedSlot !== null
      ? slots.find((slot) => slot.slot_number === selectedSlot) ?? null
      : null),
    [selectedSlot, slots]
  );

  const selectedSlotCandidateCount = availablePlayers.length;

  if (loadingChoices) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading...</div>
      </div>
    );
  }

  const filledCount = slots.filter((s) => s.player || s.custom_name).length;
  const starterCount = slots.filter((s) => !s.is_substitute && (s.player || s.custom_name)).length;

  return (
    <div className={styles.container}>
      <form onSubmit={handleSubmit}>
        <div className={styles.header}>
          <h1 className={styles.title}>Create Teamsheet</h1>
          <div className={styles.headerActions}>
            <button
              type="button"
              className={styles.cancelButton}
              onClick={handleCancel}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={saving || !title.trim()}
            >
              {saving ? 'Creating...' : 'Create Teamsheet'}
            </button>
          </div>
        </div>

        {error && (
          <div className={styles.error}>{error}</div>
        )}

        <div className={styles.content}>
          <div className={styles.mainColumn}>
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Basic Information</h2>

              <div className={styles.formGroup}>
                <label className={styles.label}>Title *</label>
                <input
                  type="text"
                  className={styles.input}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., vs Liverpool - Home"
                  required
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label className={styles.label}>Match Date</label>
                  <input
                    type="date"
                    className={styles.input}
                    value={matchDate}
                    onChange={(e) => setMatchDate(e.target.value)}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.label}>Opponent</label>
                  <input
                    type="text"
                    className={styles.input}
                    value={opponent}
                    onChange={(e) => setOpponent(e.target.value)}
                    placeholder="e.g., Liverpool"
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>Notes</label>
                <textarea
                  className={styles.textarea}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Tactical notes, key points, etc."
                  rows={3}
                />
              </div>

              <div className={styles.checkbox}>
                <input
                  type="checkbox"
                  id="isTemplate"
                  checked={isTemplate}
                  onChange={(e) => setIsTemplate(e.target.checked)}
                />
                <label htmlFor="isTemplate">Save as template</label>
              </div>
            </div>

            {choices && (
              <div className={styles.section}>
                <FormationPicker
                  formations={choices.formations_with_templates}
                  selectedFormation={selectedFormation?.value || ''}
                  onSelect={handleFormationSelect}
                />
              </div>
            )}

            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Players</h2>
                <span className={styles.counter}>
                  {starterCount}/11 starters • {filledCount} total
                </span>
              </div>
              <PlayerSlotSelector
                slots={slots}
                selectedSlot={selectedSlot}
                onSlotClick={handleSlotClick}
                onRemovePlayer={handleRemovePlayer}
              />
            </div>
          </div>

          <div className={styles.sidebar}>
            {selectedSlotState ? (
              <>
                <div
                  style={{
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '12px',
                    padding: '0.9rem',
                    marginBottom: '1rem',
                    display: 'grid',
                    gap: '0.65rem',
                    background: 'rgba(255,255,255,0.02)',
                  }}
                >
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1rem' }}>Selected Slot</h3>
                    <p style={{ margin: '0.3rem 0 0 0', opacity: 0.82 }}>
                      {selectedSlotState.position_label} ·{' '}
                      {selectedSlotState.is_substitute ? 'Substitute' : 'Starter'}
                    </p>
                  </div>

                  <div
                    style={{
                      border: '1px solid rgba(255,255,255,0.06)',
                      borderRadius: '10px',
                      padding: '0.75rem',
                      display: 'grid',
                      gap: '0.25rem',
                    }}
                  >
                    <strong>{getSlotDisplayName(selectedSlotState)}</strong>
                    <span style={{ opacity: 0.82 }}>
                      {getSlotDisplayNumber(selectedSlotState)} · {getSlotOccupantType(selectedSlotState)}
                    </span>

                    {selectedSlotState.player?.primary_position ? (
                      <span style={{ opacity: 0.82 }}>
                        Position: {selectedSlotState.player.primary_position}
                      </span>
                    ) : null}
                  </div>

                  <div style={{ fontSize: '0.92rem', opacity: 0.82 }}>
                    {getSlotHelperText(selectedSlotState)}
                  </div>

                  <div style={{ fontSize: '0.88rem', opacity: 0.72 }}>
                    {loadingPlayers
                      ? 'Loading candidates…'
                      : `${selectedSlotCandidateCount} candidate${selectedSlotCandidateCount === 1 ? '' : 's'} available${positionFilter ? ` for ${positionFilter}` : ''}.`}
                  </div>
                </div>

                <AvailablePlayersList
                  players={availablePlayers}
                  loading={loadingPlayers}
                  onSelect={handlePlayerSelect}
                  onUseDefault={handleUseDefault}
                  positionFilter={positionFilter}
                  onPositionFilterChange={setPositionFilter}
                  positions={choices?.positions || []}
                  selectedIds={slots.filter((s) => s.player).map((s) => s.player!.id)}
                />
              </>
            ) : (
              <div className={styles.selectSlotHint}>
                <p>Select a slot to assign a player</p>
              </div>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};

export default TeamsheetCreatePage;