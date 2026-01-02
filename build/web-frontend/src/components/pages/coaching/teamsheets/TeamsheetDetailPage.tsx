import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { teamsheetApi, teamsheetPlayerApi } from '../../../../services/api/teamsheetApi';
import type { Teamsheet, TeamsheetPlayer, PlayerPositionUpdate } from '../../../../types/teamsheet';
import {
  Pitch,
  TeamsheetHeader,
  SubstitutesList,
  PlayerDetailPanel,
} from '../../../../components/teamsheets';
import styles from './TeamsheetDetailPage.module.css';

const TeamsheetDetailPage: React.FC = () => {
  const { clubId, teamsheetId } = useParams<{ clubId: string; teamsheetId: string }>();
  const navigate = useNavigate();

  const [teamsheet, setTeamsheet] = useState<Teamsheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedPlayer, setSelectedPlayer] = useState<TeamsheetPlayer | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<Map<number, PlayerPositionUpdate>>(new Map());
  const [saving, setSaving] = useState(false);

  const fetchTeamsheet = useCallback(async () => {
    if (!clubId || !teamsheetId) return;

    try {
      setLoading(true);
      const data = await teamsheetApi.get(Number(clubId), Number(teamsheetId));
      setTeamsheet(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load teamsheet');
    } finally {
      setLoading(false);
    }
  }, [clubId, teamsheetId]);

  useEffect(() => {
    fetchTeamsheet();
  }, [fetchTeamsheet]);

  const handleBack = () => {
    navigate(`/clubs/${clubId}/teamsheets`);
  };

  const handlePlayerClick = (player: TeamsheetPlayer) => {
    setSelectedPlayer(prev => (prev?.id === player.id ? null : player));
  };

  const handlePlayerDragEnd = (playerId: number, x: number, y: number) => {
    if (!teamsheet) return;

    const update: PlayerPositionUpdate = { id: playerId, position_x: x, position_y: y };
    setPendingChanges(prev => new Map(prev).set(playerId, update));

    setTeamsheet(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        players: prev.players.map(p =>
          p.id === playerId ? { ...p, position_x: x, position_y: y } : p
        ),
      };
    });
  };

  const handleSaveChanges = async () => {
    if (!clubId || !teamsheetId || pendingChanges.size === 0) return;

    try {
      setSaving(true);
      await teamsheetPlayerApi.bulkUpdatePositions(
        Number(clubId),
        Number(teamsheetId),
        { updates: Array.from(pendingChanges.values()) }
      );
      setPendingChanges(new Map());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleDiscardChanges = () => {
    setPendingChanges(new Map());
    fetchTeamsheet();
  };

  const handleDuplicate = async () => {
    if (!clubId || !teamsheetId || !teamsheet) return;

    const newTitle = prompt('Enter title for the duplicate:', `Copy of ${teamsheet.title}`);
    if (!newTitle) return;

    try {
      const duplicate = await teamsheetApi.duplicate(Number(clubId), Number(teamsheetId), newTitle);
      navigate(`/clubs/${clubId}/teamsheets/${duplicate.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate teamsheet');
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading teamsheet...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          <p>{error}</p>
          <button onClick={fetchTeamsheet}>Retry</button>
        </div>
      </div>
    );
  }

  if (!teamsheet) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>Teamsheet not found</div>
      </div>
    );
  }

  const hasChanges = pendingChanges.size > 0;

  return (
    <div className={styles.container}>
      <TeamsheetHeader
        teamsheet={teamsheet}
        onBack={handleBack}
        onDuplicate={handleDuplicate}
        onEdit={() => setEditMode(!editMode)}
      />

      {hasChanges && (
        <div className={styles.changesBanner}>
          <span>You have unsaved changes ({pendingChanges.size} players moved)</span>
          <div className={styles.changesActions}>
            <button
              className={styles.discardButton}
              onClick={handleDiscardChanges}
              disabled={saving}
            >
              Discard
            </button>
            <button
              className={styles.saveButton}
              onClick={handleSaveChanges}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}

      <div className={styles.content}>
        <div className={styles.pitchContainer}>
          <div className={styles.pitchWrapper}>
            <Pitch
              players={teamsheet.players}
              selectedPlayerId={selectedPlayer?.id}
              onPlayerClick={handlePlayerClick}
              onPlayerDragEnd={handlePlayerDragEnd}
              editable={editMode}
            />
          </div>

          {editMode && (
            <div className={styles.editHint}>
              Drag players to reposition them on the pitch
            </div>
          )}
        </div>

        <div className={styles.sidebar}>
          <SubstitutesList
            players={teamsheet.players}
            selectedPlayerId={selectedPlayer?.id ?? null}
            onPlayerClick={handlePlayerClick}
          />
          {selectedPlayer && (
            <PlayerDetailPanel
              player={selectedPlayer}
              onClose={() => setSelectedPlayer(null)}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default TeamsheetDetailPage;