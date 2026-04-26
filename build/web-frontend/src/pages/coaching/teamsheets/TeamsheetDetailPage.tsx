import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { teamsheetApi, teamsheetPlayerApi } from '../../../services/api/teamsheetApi';
import type { Teamsheet, TeamsheetPlayer, PlayerPositionUpdate } from '../../../types/teamsheet';
import {
  Pitch,
  TeamsheetHeader,
  SubstitutesList,
  PlayerDetailPanel,
} from '../../../components/teamsheets';
import { chatQuery } from '../../../services/api/predictionsApi';
import AvailabilityBadge from '../../../components/predictions/AvailabilityBadge';
import ChatInterface from '../../../components/predictions/chat/ChatInterface';
import { Sidebar } from '../../../components/Navigation/SideBar';
import { CoachingNavBar } from '../../../components/Navigation/CoachingNavBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';
import styles from './css/TeamsheetDetailPage.module.css';
import { useAuth } from '../../../context/useAuth';
import { AppError } from '../../../common/AppError';
import { FullPageLoader } from '../../../common/components/FullPageLoader';
import { StatusBlock } from '../../../common/components/StatusBlock';
import { InlineRetry } from '../../../common/components/InlineRetry.tsx';
import { ResourceNotFoundPage } from '../../status/ResourceNotFoundpage.tsx';

interface PlayerAvailability {
  player_name: string;
  p_available?: number;
  status?: string;
}

const STATUS_TO_RISK_LABEL: Record<string, 'low' | 'medium' | 'high'> = {
  available:    'low',
  risk_flagged: 'medium',
  injured:      'high',
};

const normalise = (s: string | undefined | null) =>
  s ? s.toLowerCase().trim() : '';

const findAvailability = (
  playerName: string,
  data: PlayerAvailability[],
): PlayerAvailability | undefined => {
  const target = normalise(playerName);
  return (
    data.find(p => normalise(p.player_name) === target) ??
    data.find(p => {
      const src = normalise(p.player_name);
      return src.includes(target) || target.includes(src);
    })
  );
};

const TeamsheetDetailPage: React.FC = () => {
  const { clubId, teamsheetId } = useParams<{ clubId: string; teamsheetId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [teamsheet, setTeamsheet] = useState<Teamsheet | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<AppError | null>(null);

  const [selectedPlayer, setSelectedPlayer] = useState<TeamsheetPlayer | null>(null);
  const [pendingChanges, setPendingChanges] = useState<Map<number, PlayerPositionUpdate>>(new Map());
  const [saving, setSaving]                = useState(false);

  const [availabilityData, setAvailabilityData]       = useState<PlayerAvailability[]>([]);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilityError, setAvailabilityError]     = useState(false);
  const [availabilityRetryKey, setAvailabilityRetryKey] = useState(0);

  const [searchParams]     = useSearchParams();
  const isTrashView        = searchParams.get('view') === 'trash';
  const numericClubId      = clubId       ? Number(clubId)       : NaN;
  const numericTeamsheetId = teamsheetId  ? Number(teamsheetId)  : NaN;
  const [actionLoading, setActionLoading] = useState(false);

  const canManageTrash =
    typeof user?.id === 'number' &&
    typeof teamsheet?.created_by === 'number' &&
    user.id === teamsheet.created_by;

  const fetchTeamsheet = useCallback(async () => {
    if (!clubId || !teamsheetId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await teamsheetApi.get(Number(clubId), Number(teamsheetId), {
        ...(isTrashView ? { trash: 'only' } : {}),
      });
      setTeamsheet(data);
    } catch (err) {
      setError(err instanceof AppError ? err : new AppError(0, 'UNKNOWN', 'Failed to load teamsheet'));
    } finally {
      setLoading(false);
    }
  }, [clubId, teamsheetId, isTrashView]);

  useEffect(() => { fetchTeamsheet(); }, [fetchTeamsheet]);

  useEffect(() => {
    if (!teamsheet) return;
    const starters = teamsheet.players.filter(p => !p.is_substitute);
    if (starters.length === 0) return;

    setAvailabilityLoading(true);
    setAvailabilityError(false);
    Promise.all(
      starters.map(player =>
        chatQuery(`injury risk ${player.display_name}`)
          .then((response) => {
            const players = response.data?.structured_data?.engine_data?.players;
            if (Array.isArray(players) && players.length > 0) {
              return players[0] as PlayerAvailability;
            }
            return null;
          })
          .catch(() => null),
      ),
    )
      .then(results => {
        setAvailabilityData(results.filter((r): r is PlayerAvailability => r !== null));
      })
      .catch(() => {
        setAvailabilityError(true);
      })
      .finally(() => {
        setAvailabilityLoading(false);
      });
  }, [teamsheet, availabilityRetryKey]);

  const handleBack = () => {
    navigate(`/clubs/${clubId}/?tab=schedule${isTrashView ? '&view=trash' : ''}`);
  };

  const handlePlayerClick = (player: TeamsheetPlayer) =>
    setSelectedPlayer(prev => (prev?.id === player.id ? null : player));

  const handlePlayerDragEnd = (playerId: number, x: number, y: number) => {
    if (!teamsheet) return;
    const update: PlayerPositionUpdate = { id: playerId, position_x: x, position_y: y };
    setPendingChanges(prev => new Map(prev).set(playerId, update));
    setTeamsheet(prev =>
      prev
        ? {
            ...prev,
            players: prev.players.map(p =>
              p.id === playerId ? { ...p, position_x: x, position_y: y } : p,
            ),
          }
        : prev,
    );
  };

  const handleSaveChanges = async () => {
    if (!clubId || !teamsheetId || pendingChanges.size === 0) return;
    try {
      setSaving(true);
      await teamsheetPlayerApi.bulkUpdatePositions(
        Number(clubId),
        Number(teamsheetId),
        { updates: Array.from(pendingChanges.values()) },
      );
      setPendingChanges(new Map());
    } catch (err) {
      setError(err instanceof AppError ? err : new AppError(0, 'UNKNOWN', 'Failed to save changes'));
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
      const dup = await teamsheetApi.duplicate(Number(clubId), Number(teamsheetId), newTitle);
      navigate(`/clubs/${clubId}/teamsheets/${dup.id}/edit`);
    } catch (err) {
      setError(err instanceof AppError ? err : new AppError(0, 'UNKNOWN', 'Failed to duplicate teamsheet'));
    }
  };

  const handleMoveToTrash = async () => {
    if (!Number.isInteger(numericClubId) || !Number.isInteger(numericTeamsheetId)) return;
    if (!window.confirm('Move this teamsheet to trash?')) return;
    try {
      setActionLoading(true);
      setError(null);
      await teamsheetApi.trash(numericClubId, numericTeamsheetId);
      navigate(`/clubs/${numericClubId}/?tab=schedule&view=trash`);
    } catch (err) {
      setError(err instanceof AppError ? err : new AppError(0, 'UNKNOWN', 'Failed to move teamsheet to trash'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRestore = async () => {
    if (!Number.isInteger(numericClubId) || !Number.isInteger(numericTeamsheetId)) return;
    try {
      setActionLoading(true);
      setError(null);
      await teamsheetApi.restore(numericClubId, numericTeamsheetId);
      navigate(`/clubs/${numericClubId}/teamsheets/${numericTeamsheetId}`);
    } catch (err) {
      setError(err instanceof AppError ? err : new AppError(0, 'UNKNOWN', 'Failed to restore teamsheet'));
    } finally {
      setActionLoading(false);
    }
  };

  const handlePermanentDelete = async () => {
    if (!Number.isInteger(numericClubId) || !Number.isInteger(numericTeamsheetId)) return;
    if (!window.confirm('Delete this teamsheet permanently? This cannot be undone.')) return;
    try {
      setActionLoading(true);
      setError(null);
      await teamsheetApi.permanentDelete(numericClubId, numericTeamsheetId);
      navigate(`/clubs/${numericClubId}/?tab=schedule&view=trash`);
    } catch (err) {
      setError(err instanceof AppError ? err : new AppError(0, 'UNKNOWN', 'Failed to permanently delete teamsheet'));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <FullPageLoader label="Loading teamsheet" />;
  }

  if (error?.code === 'NOT_FOUND' || !teamsheet) {
    return (
      <ResourceNotFoundPage
        backPath={`/clubs/${clubId}/`}
        backLabel="Back to Club"
      />
    );
  }

  if (error) {
    return (
      <div className={styles.teamsheetDetailsContainer}>
        <StatusBlock
          variant="error"
          message={error.detail}
          actions={
            <button type="button" onClick={fetchTeamsheet}>
              Retry
            </button>
          }
        />
      </div>
    );
  }

  const hasChanges = pendingChanges.size > 0;
  const starters   = teamsheet.players.filter(p => !p.is_substitute);

  return (
    <div className={styles.teamsheetDetailsContainer}>

      <div className={styles.teamsheetDetailsSidebarSection}>
        <Sidebar />
      </div>

      <div className={styles.teamsheetDetailsMain}>

        <header className={styles.teamsheetDetailsHeader}>
          <div className={styles.teamsheetDetailsHeaderLeft}>
            Teamsheets
          </div>
          <div>
            <CoachingNavBar />
          </div>
          <div className={styles.teamsheetDetailsHeaderRight}>
            <SocialUserButtons />
          </div>
        </header>

        <div className={styles.teamsheetDetailsContent}>

          <TeamsheetHeader
            teamsheet={teamsheet}
            onBack={handleBack}
            onDuplicate={!teamsheet.is_trashed ? handleDuplicate : undefined}
            onEdit={
              !teamsheet.is_trashed
                ? () => navigate(`/clubs/${clubId}/teamsheets/${teamsheetId}/edit`)
                : undefined
            }
            onMoveToTrash={!teamsheet.is_trashed && canManageTrash ? handleMoveToTrash : undefined}
            onRestore={teamsheet.is_trashed && canManageTrash ? handleRestore : undefined}
            onPermanentDelete={
              teamsheet.is_trashed && canManageTrash ? handlePermanentDelete : undefined
            }
            actionLoading={actionLoading}
          />

          {hasChanges && !teamsheet.is_trashed && (
            <div className={styles.teamsheetDetailsChangesBanner}>
              <span>
                You have unsaved changes ({pendingChanges.size} player
                {pendingChanges.size !== 1 ? 's' : ''} moved)
              </span>
              <div className={styles.teamsheetDetailsChangesActions}>
                <button
                  className={styles.teamsheetDetailsDiscardButton}
                  onClick={handleDiscardChanges}
                  disabled={saving}
                >
                  Discard
                </button>
                <button
                  className={styles.teamsheetDetailsSaveButton}
                  onClick={handleSaveChanges}
                  disabled={saving}
                >
                  {saving ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </div>
          )}

          <div className={styles.teamsheetDetailsGrid}>

            <div className={styles.teamsheetDetailsPitchPanel}>
              <Pitch
                players={teamsheet.players}
                selectedPlayerId={selectedPlayer?.id}
                onPlayerClick={handlePlayerClick}
                onPlayerDragEnd={handlePlayerDragEnd}
                editable={!teamsheet.is_trashed}
              />
            </div>

            <div className={styles.teamsheetDetailsSidebar}>

              <SubstitutesList
                players={teamsheet.players}
                selectedPlayerId={selectedPlayer?.id ?? null}
                onPlayerClick={handlePlayerClick}
              />

              {starters.length > 0 && (
                <div className={styles.teamsheetDetailsAvailabilityPanel}>
                  <h3 className={styles.teamsheetDetailsAvailabilityTitle}>
                    Availability
                  </h3>
                  {availabilityError ? (
                    <InlineRetry
                      message="Failed to load availability"
                      onRetry={() => setAvailabilityRetryKey(k => k + 1)}
                      retrying={availabilityLoading}
                    />
                  ) : (
                    <ul className={styles.teamsheetDetailsAvailabilityList}>
                      {starters.map(player => {
                        const av = findAvailability(player.display_name, availabilityData);
                        return (
                          <li key={player.id} className={styles.teamsheetDetailsAvailabilityRow}>
                            <span className={styles.teamsheetDetailsAvailabilityName}>
                              {player.display_name}
                            </span>
                            <AvailabilityBadge
                              riskLabel={
                                av?.status ? (STATUS_TO_RISK_LABEL[av.status] ?? null) : null
                              }
                              riskScore={
                                av?.p_available != null ? 1 - av.p_available : undefined
                              }
                              isLoading={availabilityLoading}
                            />
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              )}

              {selectedPlayer && (
                <PlayerDetailPanel
                  player={selectedPlayer}
                  onClose={() => setSelectedPlayer(null)}
                />
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default TeamsheetDetailPage;