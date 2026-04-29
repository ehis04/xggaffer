import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { teamsheetApi } from "../../../services/api";
import type {
  TeamsheetChoices,
  FormationWithTemplate,
  AvailablePlayer,
  SlotState,
  CreateTeamsheetPayload,
  PlayerSlotAssignment,
} from "../../../types/teamsheet";
import {
  PlayerSlotSelector,
  AvailablePlayersList,
} from "../../../components/teamsheets";
import styles from "./css/TeamsheetCreatePage.module.css";
import { Sidebar } from "../../../components/Navigation/SideBar";
import { CoachingNavBar } from "../../../components/Navigation/CoachingNavBar";
import { SocialUserButtons } from "../../../components/Social/SocialUserButtons";

const getSlotDisplayName = (slot: SlotState): string => {
  if (slot.player) return slot.player.display_name || slot.player.full_name;
  if (slot.custom_name) return slot.custom_name;
  return "No player assigned yet";
};

const getSlotDisplayNumber = (slot: SlotState): string => {
  if (slot.player?.squad_number) return `#${slot.player.squad_number}`;
  if (slot.custom_number) return `#${slot.custom_number}`;
  return `Slot ${slot.slot_number}`;
};

const getSlotOccupantType = (slot: SlotState): string => {
  if (slot.player)
    return slot.player.source_type === "club_member"
      ? "Club member"
      : "Public player";
  if (slot.custom_name) return "Default player";
  return "Unassigned";
};

const getSlotHelperText = (slot: SlotState): string => {
  if (slot.player)
    return "Choose a different player below to replace the current assignment, or remove the player from the slot card.";
  if (slot.custom_name)
    return "Choose a real player below to replace the default placeholder if needed.";
  return "Choose a player below or use the default-player option to fill this slot.";
};

const Toggle: React.FC<{
  checked: boolean;
  onChange: (v: boolean) => void;
}> = ({ checked, onChange }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    onClick={() => onChange(!checked)}
    className={`${styles.TTSCreateToggle} ${checked ? styles.TTSCreateToggleOn : ""}`}
  >
    <span className={styles.TTSCreateToggleThumb} />
  </button>
);

const TeamsheetCreatePage: React.FC = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();

  const [choices, setChoices] = useState<TeamsheetChoices | null>(null);
  const [availablePlayers, setAvailablePlayers] = useState<AvailablePlayer[]>(
    [],
  );
  const [loadingChoices, setLoadingChoices] = useState(true);
  const [loadingPlayers, setLoadingPlayers] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [selectedFormation, setSelectedFormation] =
    useState<FormationWithTemplate | null>(null);
  const [matchDate, setMatchDate] = useState("");
  const [kickOff, setKickOff] = useState("");
  const [opponent, setOpponent] = useState("");
  const [competition, setCompetition] = useState("");
  const [venue, setVenue] = useState("");
  const [squad, setSquad] = useState("");
  const [homeAway, setHomeAway] = useState("Home");
  const [notes, setNotes] = useState("");
  const [isTemplate, setIsTemplate] = useState(false);

  const [startFrom, setStartFrom] = useState<"blank" | "duplicate" | "tactics">(
    "blank",
  );
  const [captain, setCaptain] = useState("auto");
  const [notifyOnPublish, setNotifyOnPublish] = useState(true);
  const [lockSubsAfterKickoff, setLockSubsAfterKickoff] = useState(false);
  const [trackMinutes, setTrackMinutes] = useState(true);

  const [slots, setSlots] = useState<SlotState[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [positionFilter, setPositionFilter] = useState("");

  useEffect(() => {
    if (!clubId) return;
    const fetchData = async () => {
      try {
        setLoadingChoices(true);
        const choicesData = await teamsheetApi.getChoices(Number(clubId));
        setChoices(choicesData);
        if (choicesData.formations_with_templates.length > 0) {
          const def =
            choicesData.formations_with_templates.find(
              (f) => f.value === "433",
            ) || choicesData.formations_with_templates[0];
          handleFormationSelect(def);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoadingChoices(false);
      }
    };
    fetchData();
  }, [clubId]);

  const fetchAvailablePlayers = useCallback(
    async (position?: string) => {
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
        console.error("Failed to load players:", err);
      } finally {
        setLoadingPlayers(false);
      }
    },
    [clubId, slots],
  );

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
    const subPositions = ["GK", "CB", "CB", "CM", "CM", "ST", "ST"];
    for (let i = 12; i <= 18; i++) {
      newSlots.push({
        slot_number: i,
        position_label: subPositions[i - 12] || "MID",
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
    setPositionFilter("");
  };

  const handlePlayerSelect = (player: AvailablePlayer) => {
    if (selectedSlot === null) return;
    setSlots((prev) =>
      prev.map((slot) =>
        slot.slot_number === selectedSlot
          ? {
              ...slot,
              player,
              custom_name: undefined,
              custom_number: undefined,
            }
          : slot,
      ),
    );
    const emptySlots = slots.filter(
      (s) => !s.player && !s.custom_name && s.slot_number !== selectedSlot,
    );
    if (emptySlots.length > 0) {
      const nextEmpty =
        emptySlots.find((s) => s.slot_number > selectedSlot) || emptySlots[0];
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
    setSlots((prev) =>
      prev.map((s) =>
        s.slot_number === selectedSlot
          ? {
              ...s,
              player: null,
              custom_name: defaultName,
              custom_number: s.slot_number,
            }
          : s,
      ),
    );
    const emptySlots = slots.filter(
      (s) => !s.player && !s.custom_name && s.slot_number !== selectedSlot,
    );
    if (emptySlots.length > 0) {
      const nextEmpty =
        emptySlots.find((s) => s.slot_number > selectedSlot) || emptySlots[0];
      setSelectedSlot(nextEmpty.slot_number);
    } else {
      setSelectedSlot(null);
    }
  };

  const handleRemovePlayer = (slotNumber: number) => {
    setSlots((prev) =>
      prev.map((slot) =>
        slot.slot_number === slotNumber
          ? {
              ...slot,
              player: null,
              custom_name: undefined,
              custom_number: undefined,
            }
          : slot,
      ),
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clubId || !selectedFormation) return;
    if (!title.trim()) {
      setError("Title is required");
      return;
    }

    const playerAssignments: PlayerSlotAssignment[] = slots
      .filter((s) => s.player || s.custom_name)
      .map((s) => ({
        slot_number: s.slot_number,
        club_player_id: s.player?.id || null,
        custom_name: s.custom_name || "",
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
      const teamsheet = await teamsheetApi.createWithPlayers(
        Number(clubId),
        payload,
      );
      navigate(`/clubs/${clubId}/teamsheets/${teamsheet.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create teamsheet",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => navigate(`/clubs/${clubId}/teamsheets`);

  const selectedSlotState = useMemo(
    () =>
      selectedSlot !== null
        ? (slots.find((slot) => slot.slot_number === selectedSlot) ?? null)
        : null,
    [selectedSlot, slots],
  );

  const selectedSlotCandidateCount = availablePlayers.length;
  const filledCount = slots.filter((s) => s.player || s.custom_name).length;
  const starterCount = slots.filter(
    (s) => !s.is_substitute && (s.player || s.custom_name),
  ).length;

  if (loadingChoices) {
    return (
      <div className={styles.TTSCreateContainer}>
        <div className={styles.sidebarSection}>
          <Sidebar />
        </div>
        <div className={styles.TTSCreateBody}>
          <div className={styles.TTSCreateLoading}>Loading…</div>
        </div>
      </div>
    );
  }

  const formations = choices?.formations_with_templates ?? [];

  return (
    <div className={styles.TTSCreateContainer}>
      <div className={styles.sidebarSection}>
        <Sidebar />
      </div>

      <div className={styles.TTSCreateBody}>
        <header className={styles.TTSCreateHeader}>
          <div className={styles.headerLeft}>
            <button
              type="button"
              className={styles.backButton}
              onClick={() => navigate(`/clubs/${clubId}/teamsheets`)}
            >
              ←
            </button>
            <div className={styles.TTSCreateBreadcrumb}>
              <span className={styles.TTSCreateBreadcrumbMuted}>
                {opponent ? opponent.toUpperCase() : "CLUB"}
              </span>
              <span className={styles.TTSCreateBreadcrumbSep}>/</span>
              <span className={styles.TTSCreateBreadcrumbMuted}>
                TEAMSHEETS
              </span>
              <span className={styles.TTSCreateBreadcrumbSep}>/</span>
              <span className={styles.TTSCreateBreadcrumbActive}>New</span>
            </div>
          </div>
          <div className={styles.headerCenter}>
            <CoachingNavBar />
          </div>
          <div className={styles.headerRight}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles.TTSCreateSubHeader}>
          <div className={styles.TTSCreateSubHeaderLeft}>
            <span className={styles.TTSCreateSubHeaderTitle}>COACHING</span>
            <span className={styles.TTSCreateSubHeaderDivider}>/</span>
            <span className={styles.TTSCreateSubHeaderPage}>New Teamsheet</span>
          </div>
          <div className={styles.TTSCreateActionGroup}>
            <button
              type="button"
              className={styles.TTSCreateBtnCancel}
              onClick={handleCancel}
            >
              Cancel
            </button>
            <button
              type="button"
              className={styles.TTSCreateBtnDraft}
              disabled={saving || !title.trim()}
            >
              Save draft
            </button>
            <button
              type="button"
              className={styles.TTSCreateBtnCreate}
              disabled={saving || !title.trim()}
              onClick={handleSubmit as unknown as React.MouseEventHandler}
            >
              {saving ? "Creating…" : "Create teamsheet"}
            </button>
          </div>
        </div>

        <div className={styles.TTSCreateContent}>
          {error && <div className={styles.TTSCreateError}>{error}</div>}

          <div className={styles.TTSCreateTwoCol}>
            <div className={styles.TTSCreateLeftCol}>
              <div className={styles.TTSCreatePanel}>
                <div className={styles.TTSCreatePanelHead}>
                  <h2 className={styles.TTSCreatePanelTitle}>Match details</h2>
                  <span className={styles.TTSCreatePanelRequired}>
                    REQUIRED
                  </span>
                </div>

                <div className={styles.TTSCreateFormGroup}>
                  <label className={styles.TTSCreateLabel}>
                    TEAMSHEET NAME
                  </label>
                  <input
                    type="text"
                    className={styles.TTSCreateInput}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="vs Northgate FC — League"
                    required
                  />
                </div>

                <div className={styles.TTSCreateFormGroup}>
                  <label className={styles.TTSCreateLabel}>OPPOSITION</label>
                  <input
                    type="text"
                    className={styles.TTSCreateInput}
                    value={opponent}
                    onChange={(e) => setOpponent(e.target.value)}
                    placeholder="Northgate FC"
                  />
                </div>

                <div className={styles.TTSCreateFormRow}>
                  <div className={styles.TTSCreateFormGroup}>
                    <label className={styles.TTSCreateLabel}>DATE</label>
                    <input
                      type="date"
                      className={styles.TTSCreateInput}
                      value={matchDate}
                      onChange={(e) => setMatchDate(e.target.value)}
                    />
                  </div>
                </div>

                <label className={styles.TTSCreateCheckRow}>
                  <input
                    type="checkbox"
                    checked={isTemplate}
                    onChange={(e) => setIsTemplate(e.target.checked)}
                    className={styles.TTSCreateCheckbox}
                  />
                  <span className={styles.TTSCreateCheckLabel}>
                    Save as template
                  </span>
                </label>
              </div>

              <div className={styles.TTSCreatePanel}>
                <div className={styles.TTSCreatePanelHead}>
                  <h2 className={styles.TTSCreatePanelTitle}>Formation</h2>
                </div>

                <div className={styles.TTSCreateFormationTabs}>
                  {formations.map((f) => (
                    <button
                      key={f.value}
                      type="button"
                      className={`${styles.TTSCreateFormationTab} ${selectedFormation?.value === f.value ? styles.TTSCreateFormationTabActive : ""}`}
                      onClick={() => handleFormationSelect(f)}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>

                {selectedFormation && (
                  <div className={styles.TTSCreateFormationHint}>
                    Selected: <strong>{selectedFormation.label}</strong> — pick
                    a starting formation now, you'll assign players in the next
                    step.
                  </div>
                )}
              </div>
              <div className={styles.TTSCreatePanel}>
                <div className={styles.TTSCreatePanelHead}>
                  <h2 className={styles.TTSCreatePanelTitle}>Notes</h2>
                </div>
                <textarea
                  className={styles.TTSCreateTextarea}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Tactical notes, key points, team talk prompts…"
                  rows={5}
                />
              </div>
            </div>

            <div className={styles.TTSCreateRightCol}>
              <div className={styles.TTSCreatePanel}>
                <div className={styles.TTSCreatePanelHead}>
                  <h2 className={styles.TTSCreatePanelTitle}>Players</h2>
                  <span className={styles.TTSCreatePanelCount}>
                    {starterCount}/11 starters · {filledCount} total
                  </span>
                </div>

                <PlayerSlotSelector
                  slots={slots}
                  selectedSlot={selectedSlot}
                  onSlotClick={handleSlotClick}
                  onRemovePlayer={handleRemovePlayer}
                />

                {selectedSlotState && (
                  <div className={styles.TTSCreateSlotDetail}>
                    <div className={styles.TTSCreateSlotDetailHead}>
                      <div>
                        <div className={styles.TTSCreateSlotDetailTitle}>
                          {selectedSlotState.position_label} ·{" "}
                          {selectedSlotState.is_substitute
                            ? "Substitute"
                            : "Starter"}
                        </div>
                        <div className={styles.TTSCreateSlotDetailSub}>
                          {getSlotHelperText(selectedSlotState)}
                        </div>
                      </div>
                    </div>

                    <div className={styles.TTSCreateSlotOccupant}>
                      <strong>{getSlotDisplayName(selectedSlotState)}</strong>
                      <span className={styles.TTSCreateSlotOccupantMeta}>
                        {getSlotDisplayNumber(selectedSlotState)} ·{" "}
                        {getSlotOccupantType(selectedSlotState)}
                      </span>
                      {selectedSlotState.player?.primary_position && (
                        <span className={styles.TTSCreateSlotOccupantMeta}>
                          Position: {selectedSlotState.player.primary_position}
                        </span>
                      )}
                    </div>

                    <div className={styles.TTSCreateSlotCandidateCount}>
                      {loadingPlayers
                        ? "Loading candidates…"
                        : `${selectedSlotCandidateCount} candidate${selectedSlotCandidateCount === 1 ? "" : "s"} available${positionFilter ? ` for ${positionFilter}` : ""}.`}
                    </div>

                    <AvailablePlayersList
                      players={availablePlayers}
                      loading={loadingPlayers}
                      onSelect={handlePlayerSelect}
                      onUseDefault={handleUseDefault}
                      positionFilter={positionFilter}
                      onPositionFilterChange={setPositionFilter}
                      positions={choices?.positions || []}
                      selectedIds={slots
                        .filter((s) => s.player)
                        .map((s) => s.player!.id)}
                    />
                  </div>
                )}

                {!selectedSlotState && slots.length > 0 && (
                  <div className={styles.TTSCreateSelectHint}>
                    Select a slot above to assign a player.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TeamsheetCreatePage;
