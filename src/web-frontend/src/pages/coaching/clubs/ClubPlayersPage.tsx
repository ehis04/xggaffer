import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { clubsApi } from '../../../services/api';
import { playerdataApi } from '../../../services/api/playerdataApi';
import CompactPlayerPreview from '../../../components/playerdata/CompactPlayerPreview';
import type { Club } from '../../../types/club';
import type {
  ClubPlayer,
  CreateClubPlayerPayload,
  UpdateClubPlayerPayload,
  LinkClubPlayerPayload,
  RelinkClubPlayerPayload,
} from '../../../types/clubPlayers';
import type { PlayerDataFilters, PlayerSeasonSummary } from '../../../types/playerdata';
import styles from './css/ClubPlayersPage.module.css';

interface PlayerFormState {
  first_name: string;
  last_name: string;
  display_name: string;
  squad_number: string;
  primary_position: string;
  secondary_positions: string;
  preferred_foot: string;
  date_of_birth: string;
  height_cm: string;
  is_public: boolean;
  is_active: boolean;
}

type CanonicalPlayerIdSource =
  | 'canonical_player_id'
  | 'player_id';

interface CanonicalPlayerResolution {
  id: number | null;
  source: CanonicalPlayerIdSource | null;
}

const POSITION_OPTIONS = [
  'GK',
  'RB',
  'RWB',
  'CB',
  'RCB',
  'LCB',
  'LB',
  'LWB',
  'CDM',
  'RDM',
  'LDM',
  'CM',
  'RM',
  'LM',
  'CAM',
  'RAM',
  'LAM',
  'RW',
  'LW',
  'CF',
  'ST',
];

const FOOT_OPTIONS = [
  { value: '', label: 'Not set' },
  { value: 'l', label: 'Left' },
  { value: 'r', label: 'Right' },
  { value: 'b', label: 'Both' },
];

const buildInternalPlayerProfileUrl = (
  playerId: number,
  options?: {
    clubId?: number | null;
    clubPlayerId?: number | null;
    filters?: PlayerDataFilters | null;
  }
): string => {
  const params = new URLSearchParams({
    playerId: String(playerId),
  });

  if (options?.clubId && Number.isInteger(options.clubId) && options.clubId > 0) {
    params.set('fromClubId', String(options.clubId));
  }

  if (
    options?.clubPlayerId &&
    Number.isInteger(options.clubPlayerId) &&
    options.clubPlayerId > 0
  ) {
    params.set('clubPlayerId', String(options.clubPlayerId));
  }

  if (options?.filters?.season) {
    params.set('season', options.filters.season);
  }

  if (options?.filters?.provider) {
    params.set('provider', options.filters.provider);
  }

  if (options?.filters?.competition_code) {
    params.set('competition_code', options.filters.competition_code);
  }

  if (options?.filters?.competition_name) {
    params.set('competition_name', options.filters.competition_name);
  }

  return `/coaching/playerdata/player?${params.toString()}`;
};

const emptyForm = (): PlayerFormState => ({
  first_name: '',
  last_name: '',
  display_name: '',
  squad_number: '',
  primary_position: '',
  secondary_positions: '',
  preferred_foot: '',
  date_of_birth: '',
  height_cm: '',
  is_public: false,
  is_active: true,
});

const getPlayerLabel = (player: ClubPlayer): string => {
  if (player.display_name?.trim()) {
    return player.display_name.trim();
  }

  if (player.full_name?.trim()) {
    return player.full_name.trim();
  }

  return `${player.first_name} ${player.last_name}`.trim() || `Player #${player.id}`;
};

const toFormState = (player: ClubPlayer): PlayerFormState => ({
  first_name: player.first_name || '',
  last_name: player.last_name || '',
  display_name: player.display_name || '',
  squad_number: player.squad_number?.toString() || '',
  primary_position: player.primary_position || '',
  secondary_positions: (player.secondary_positions || []).join(', '),
  preferred_foot: player.preferred_foot || '',
  date_of_birth: player.date_of_birth || '',
  height_cm: player.height_cm?.toString() || '',
  is_public: Boolean(player.is_public),
  is_active: Boolean(player.is_active),
});

const parseSecondaryPositions = (value: string): string[] => {
  return value
    .split(',')
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
};

const normalizeError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object') {
    const values = Object.values(error as Record<string, unknown>).flatMap((value) => {
      if (Array.isArray(value)) {
        return value.map(String);
      }
      return [String(value)];
    });

    if (values.length > 0) {
      return values.join(' ');
    }
  }

  return 'Something went wrong.';
};

const formatLastSyncedAt = (value?: string | null): string => {
  if (!value) {
    return 'Never synced';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Last sync unavailable';
  }

  return `Last synced ${date.toLocaleString('en-IE', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })}`;
};

const formatMetricValue = (value?: string | null): string => {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  return value;
};

const getLatestPlayerSync = (players: ClubPlayer[]): string | null => {
  const timestamps = players
    .map((player) => player.last_synced_at)
    .filter((value): value is string => Boolean(value))
    .map((value) => new Date(value).getTime())
    .filter((value) => !Number.isNaN(value));

  if (timestamps.length === 0) {
    return null;
  }

  return new Date(Math.max(...timestamps)).toISOString();
};

const resolveCanonicalPlayerIdentity = (
  player?: ClubPlayer | null
): CanonicalPlayerResolution => {
  if (!player) {
    return { id: null, source: null };
  }

  const orderedCandidates: Array<{
    source: CanonicalPlayerIdSource;
    value: number | null | undefined;
  }> = [
    { source: 'canonical_player_id', value: player.canonical_player_id },
    { source: 'player_id', value: player.player_id },
  ];

  for (const entry of orderedCandidates) {
    if (
      typeof entry.value === 'number' &&
      Number.isInteger(entry.value) &&
      entry.value > 0
    ) {
      return {
        id: entry.value,
        source: entry.source,
      };
    }
  }

  return { id: null, source: null };
};

const buildFiltersFromSummary = (
  summary?: PlayerSeasonSummary | null
): PlayerDataFilters | null => {
  if (!summary) {
    return null;
  }

  const provider =
    summary.context?.provider?.trim() ||
    summary.provider_coverage?.provider?.trim() ||
    undefined;

  const season = summary.context?.season?.trim() || undefined;
  const competition_code = summary.context?.competition_code?.trim() || undefined;
  const competition_name = summary.context?.competition_name?.trim() || undefined;

  if (!provider && !season && !competition_code && !competition_name) {
    return null;
  }

  return {
    provider,
    season,
    competition_code,
    competition_name,
  };
};

const identityBadgeStyle = (isLinked: boolean): React.CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: '28px',
  padding: '0 10px',
  borderRadius: '999px',
  fontSize: '0.82rem',
  fontWeight: 600,
  background: isLinked ? 'rgba(34, 197, 94, 0.14)' : 'rgba(148, 163, 184, 0.14)',
  border: isLinked
    ? '1px solid rgba(34, 197, 94, 0.34)'
    : '1px solid rgba(148, 163, 184, 0.28)',
  color: isLinked ? '#86efac' : '#cbd5e1',
});

const identityPanelStyle: React.CSSProperties = {
  marginTop: '16px',
  borderTop: '1px solid #243041',
  paddingTop: '16px',
  display: 'flex',
  flexDirection: 'column',
  gap: '14px',
};

const identityNoticeStyle: React.CSSProperties = {
  borderRadius: '12px',
  padding: '14px 16px',
  background: '#0f172a',
  border: '1px solid #243041',
  color: '#cbd5e1',
  fontSize: '0.92rem',
  lineHeight: 1.5,
};

const identityRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: '10px',
};

const identityTextStyle: React.CSSProperties = {
  fontSize: '0.9rem',
  color: '#cbd5e1',
};

const identityMetaGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '10px 14px',
};

const identityActionsStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  flexWrap: 'wrap',
};

const ClubPlayersPage: React.FC = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const navigate = useNavigate();

  const numericClubId = useMemo(() => Number(clubId), [clubId]);

  const [club, setClub] = useState<Club | null>(null);
  const [players, setPlayers] = useState<ClubPlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [editingPlayer, setEditingPlayer] = useState<ClubPlayer | null>(null);
  const [form, setForm] = useState<PlayerFormState>(emptyForm());

  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [selectedPlayerSummary, setSelectedPlayerSummary] =
    useState<PlayerSeasonSummary | null>(null);
  const [selectedPlayerSummaryLoading, setSelectedPlayerSummaryLoading] = useState(false);
  const [selectedPlayerSummaryError, setSelectedPlayerSummaryError] =
    useState<string | null>(null);

  const [canManageIdentity, setCanManageIdentity] = useState(false);
  const [identityLoading, setIdentityLoading] = useState(false);
  const [identityError, setIdentityError] = useState<string | null>(null);
  const [identityMessage, setIdentityMessage] = useState<string | null>(null);
  const [canonicalPlayerIdInput, setCanonicalPlayerIdInput] = useState('');

  const linkedCount = useMemo(
    () => players.filter((player) => Boolean(player.is_linked_to_player)).length,
    [players]
  );

  const latestSyncAt = useMemo(() => getLatestPlayerSync(players), [players]);

  const understatSummary = club?.latest_understat_summary ?? null;

  const selectedPlayer = useMemo(
    () => players.find((player) => player.id === selectedPlayerId) ?? null,
    [players, selectedPlayerId]
  );

  const selectedPlayerIdentity = useMemo(
    () => resolveCanonicalPlayerIdentity(selectedPlayer),
    [selectedPlayer]
  );

  const selectedCanonicalPlayerId = selectedPlayerIdentity.id;

  const selectedPlayerFilters = useMemo(
    () => buildFiltersFromSummary(selectedPlayerSummary),
    [selectedPlayerSummary]
  );

  const handleOpenSelectedPlayerReadPage = useCallback(() => {
    if (!selectedCanonicalPlayerId) {
      return;
    }

    navigate(
      buildInternalPlayerProfileUrl(selectedCanonicalPlayerId, {
        clubId: numericClubId,
        clubPlayerId: selectedPlayer?.id ?? null,
        filters: selectedPlayerFilters,
      })
    );
  }, [
    navigate,
    numericClubId,
    selectedCanonicalPlayerId,
    selectedPlayer?.id,
    selectedPlayerFilters,
  ]);

  const loadIdentityAccess = useCallback(async (clubIdValue: number) => {
    try {
      await clubsApi.listClubJoinRequests(clubIdValue);
      setCanManageIdentity(true);
    } catch {
      setCanManageIdentity(false);
    }
  }, []);

  const loadPage = useCallback(async () => {
    if (!numericClubId || Number.isNaN(numericClubId)) {
      setError('Invalid club ID.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const [clubData, playerData] = await Promise.all([
        clubsApi.get(numericClubId),
        clubsApi.listPlayers(numericClubId),
      ]);

      setClub(clubData);
      setPlayers(playerData);
      await loadIdentityAccess(numericClubId);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }, [numericClubId, loadIdentityAccess]);

  useEffect(() => {
    void loadPage();
  }, [loadPage]);

  useEffect(() => {
    setSelectedPlayerId((current) => {
      if (current === null) {
        return current;
      }

      return players.some((player) => player.id === current) ? current : null;
    });
  }, [players]);

  useEffect(() => {
    if (!selectedPlayer) {
      setCanonicalPlayerIdInput('');
      setIdentityError(null);
      setIdentityMessage(null);
      return;
    }

    const linkedId =
      selectedPlayer.canonical_player_id ??
      selectedPlayer.player_id ??
      null;

    setCanonicalPlayerIdInput(linkedId ? String(linkedId) : '');
    setIdentityError(null);
    setIdentityMessage(null);
  }, [selectedPlayer]);

  const resetForm = () => {
    setForm(emptyForm());
    setEditingPlayer(null);
    setFormError(null);
  };

  const resetSelectedPreviewState = () => {
    setSelectedPlayerSummary(null);
    setSelectedPlayerSummaryError(null);
    setSelectedPlayerSummaryLoading(false);
  };

  const clearSelectedPlayerPreview = () => {
    setSelectedPlayerId(null);
    resetSelectedPreviewState();
  };

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = event.target;

    if (type === 'checkbox' && 'checked' in event.target) {
      setForm((prev) => ({
        ...prev,
        [name]: (event.target as HTMLInputElement).checked,
      }));
      return;
    }

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleEditClick = (player: ClubPlayer) => {
    setEditingPlayer(player);
    setForm(toFormState(player));
    setFormError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePreviewSelect = (player: ClubPlayer) => {
    setSelectedPlayerId(player.id);
    resetSelectedPreviewState();
  };

  const handlePreviewToggle = (player: ClubPlayer) => {
    setSelectedPlayerId((current) => (current === player.id ? null : player.id));
    resetSelectedPreviewState();
  };

  const buildPayload = (): CreateClubPlayerPayload | UpdateClubPlayerPayload => {
    const payload: UpdateClubPlayerPayload = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      display_name: form.display_name.trim() || '',
      squad_number: form.squad_number ? Number(form.squad_number) : null,
      primary_position: form.primary_position || '',
      secondary_positions: parseSecondaryPositions(form.secondary_positions),
      preferred_foot: form.preferred_foot || '',
      date_of_birth: form.date_of_birth || null,
      height_cm: form.height_cm ? Number(form.height_cm) : null,
      is_public: form.is_public,
    };

    if (editingPlayer) {
      payload.is_active = form.is_active;
    }

    return payload;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!numericClubId || Number.isNaN(numericClubId)) {
      setFormError('Invalid club ID.');
      return;
    }

    if (!form.first_name.trim() || !form.last_name.trim()) {
      setFormError('First name and last name are required.');
      return;
    }

    try {
      setSaving(true);
      setFormError(null);

      const payload = buildPayload();

      if (editingPlayer) {
        await clubsApi.updatePlayer(numericClubId, editingPlayer.id, payload);
      } else {
        await clubsApi.createPlayer(numericClubId, payload);
      }

      await loadPage();
      resetForm();
    } catch (err) {
      setFormError(normalizeError(err));
    } finally {
      setSaving(false);
    }
  };

  const handleSyncSquad = async () => {
    if (!numericClubId || Number.isNaN(numericClubId)) {
      setSyncError('Invalid club ID.');
      return;
    }

    try {
      setSyncing(true);
      setSyncError(null);
      setSyncMessage(null);

      const result = await clubsApi.syncClubSquad(numericClubId);

      await loadPage();

      setSyncMessage(
        [
          result.status === 'partial' ? 'Squad sync partially completed.' : 'Squad sync completed.',
          `${result.records_processed} processed`,
          `${result.players_created} players created`,
          `${result.players_updated} players updated`,
          `${result.club_players_created} club players created`,
          `${result.club_players_updated} club players updated`,
        ].join(' ')
      );
    } catch (err) {
      setSyncError(normalizeError(err));
    } finally {
      setSyncing(false);
    }
  };

  const handleLinkPlayer = async () => {
    if (!numericClubId || Number.isNaN(numericClubId) || !selectedPlayer) {
      return;
    }

    const canonicalPlayerId = Number(canonicalPlayerIdInput);

    if (!Number.isInteger(canonicalPlayerId) || canonicalPlayerId <= 0) {
      setIdentityError('Enter a valid canonical player ID.');
      return;
    }

    try {
      setIdentityLoading(true);
      setIdentityError(null);
      setIdentityMessage(null);

      const payload: LinkClubPlayerPayload = {
        canonical_player_id: canonicalPlayerId,
      };

      await clubsApi.linkPlayer(numericClubId, selectedPlayer.id, payload);
      await loadPage();

      setIdentityMessage('Canonical player link saved.');
      setCanonicalPlayerIdInput(String(canonicalPlayerId));
    } catch (err) {
      setIdentityError(normalizeError(err));
    } finally {
      setIdentityLoading(false);
    }
  };

  const handleRelinkPlayer = async () => {
    if (!numericClubId || Number.isNaN(numericClubId) || !selectedPlayer) {
      return;
    }

    const canonicalPlayerId = Number(canonicalPlayerIdInput);

    if (!Number.isInteger(canonicalPlayerId) || canonicalPlayerId <= 0) {
      setIdentityError('Enter a valid canonical player ID.');
      return;
    }

    try {
      setIdentityLoading(true);
      setIdentityError(null);
      setIdentityMessage(null);

      const payload: RelinkClubPlayerPayload = {
        canonical_player_id: canonicalPlayerId,
      };

      await clubsApi.relinkPlayer(numericClubId, selectedPlayer.id, payload);
      await loadPage();

      setIdentityMessage('Canonical player link updated.');
      setCanonicalPlayerIdInput(String(canonicalPlayerId));
    } catch (err) {
      setIdentityError(normalizeError(err));
    } finally {
      setIdentityLoading(false);
    }
  };

  const handleUnlinkPlayer = async () => {
    if (!numericClubId || Number.isNaN(numericClubId) || !selectedPlayer) {
      return;
    }

    try {
      setIdentityLoading(true);
      setIdentityError(null);
      setIdentityMessage(null);

      await clubsApi.unlinkPlayer(numericClubId, selectedPlayer.id);
      await loadPage();

      setIdentityMessage('Canonical player link removed.');
      setCanonicalPlayerIdInput('');
    } catch (err) {
      setIdentityError(normalizeError(err));
    } finally {
      setIdentityLoading(false);
    }
  };

  useEffect(() => {
    if (!selectedPlayer) {
      setSelectedPlayerSummary(null);
      setSelectedPlayerSummaryError(null);
      setSelectedPlayerSummaryLoading(false);
      return;
    }

    if (!selectedCanonicalPlayerId) {
      setSelectedPlayerSummary(null);
      setSelectedPlayerSummaryLoading(false);
      setSelectedPlayerSummaryError(
        selectedPlayer.is_linked_to_player
          ? 'This player is linked, but no canonical player ID is exposed on this page yet.'
          : 'Deterministic season summaries are only available for canonically linked players.'
      );
      return;
    }

    let isActive = true;

    const loadSelectedPlayerSummary = async () => {
      try {
        setSelectedPlayerSummary(null);
        setSelectedPlayerSummaryLoading(true);
        setSelectedPlayerSummaryError(null);

        const summary = await playerdataApi.getPlayerSeasonSummary(selectedCanonicalPlayerId);

        if (!isActive) {
          return;
        }

        setSelectedPlayerSummary(summary);
      } catch (err) {
        if (!isActive) {
          return;
        }

        setSelectedPlayerSummary(null);
        setSelectedPlayerSummaryError(normalizeError(err));
      } finally {
        if (isActive) {
          setSelectedPlayerSummaryLoading(false);
        }
      }
    };

    void loadSelectedPlayerSummary();

    return () => {
      isActive = false;
    };
  }, [selectedPlayer, selectedCanonicalPlayerId]);

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading players...</div>
      </div>
    );
  }

  if (error || !club) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>{error || 'Club not found.'}</div>
        <button
          type="button"
          className={styles.backButton}
          onClick={() => navigate('/clubs')}
        >
          Back to Clubs
        </button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Players</h1>
          <p className={styles.subtitle}>{club.name}</p>
          <p className={styles.subtitle}>
            {linkedCount} canonical linked / {players.length - linkedCount} local-only
          </p>
          <p className={styles.subtitle}>{formatLastSyncedAt(latestSyncAt)}</p>
        </div>

        <div className={styles.formActions}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={handleSyncSquad}
            disabled={syncing}
          >
            {syncing ? 'Syncing Squad...' : 'Sync Squad'}
          </button>

          <button
            type="button"
            className={styles.backButton}
            onClick={() => navigate(`/clubs/${club.id}`)}
          >
            Back to Club
          </button>
        </div>
      </div>

      {syncError && <div className={styles.error}>{syncError}</div>}
      {syncMessage && <div className={styles.emptyState}>{syncMessage}</div>}

      {understatSummary && (
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Understat Summary</h2>
            <span className={styles.badge}>
              {understatSummary.season_label}
              {understatSummary.competition_code
                ? ` · ${understatSummary.competition_code}`
                : ''}
            </span>
          </div>

          <div className={styles.metaGrid}>
            <span className={styles.metaItem}>
              <strong>Source</strong> Understat
            </span>
            <span className={styles.metaItem}>
              <strong>Matches</strong> {understatSummary.matches_played}
            </span>
            <span className={styles.metaItem}>
              <strong>xG</strong> {formatMetricValue(understatSummary.xg)}
            </span>
            <span className={styles.metaItem}>
              <strong>xGA</strong> {formatMetricValue(understatSummary.xga)}
            </span>
            <span className={styles.metaItem}>
              <strong>npxG</strong> {formatMetricValue(understatSummary.npxg)}
            </span>
          </div>

          <p className={styles.secondaryPositions}>
            {formatLastSyncedAt(understatSummary.last_synced_at)}
          </p>
        </section>
      )}

      <div className={styles.layout}>
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Roster</h2>
            <span className={styles.badge}>{players.length} players</span>
          </div>

          {players.length === 0 ? (
            <div className={styles.emptyState}>
              No players added yet. Create your first player using the form.
            </div>
          ) : (
            <div className={styles.playerList}>
              {players.map((player) => {
                const isSelected = selectedPlayerId === player.id;
                const isCanonicallyLinked = Boolean(player.is_linked_to_player);

                return (
                  <div
                    key={player.id}
                    className={styles.playerCard}
                    style={
                      isSelected
                        ? {
                            outline: '2px solid rgba(255,255,255,0.18)',
                            outlineOffset: '2px',
                          }
                        : undefined
                    }
                  >
                    <div
                      className={styles.playerMain}
                      onClick={() => handlePreviewSelect(player)}
                      style={{ cursor: 'pointer' }}
                    >
                      <div className={styles.playerTopRow}>
                        <div>
                          <h3 className={styles.playerName}>{getPlayerLabel(player)}</h3>
                          <div className={styles.metaGrid}>
                            <span className={styles.metaItem}>
                              <strong>Source</strong>{' '}
                              {player.has_provider_identity ? 'Provider-linked' : 'Local-only'}
                            </span>
                            {player.provider_sources && player.provider_sources.length > 0 && (
                              <span className={styles.metaItem}>
                                <strong>Providers</strong> {player.provider_sources.join(', ')}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className={styles.formActions}>
                          <button
                            type="button"
                            className={styles.secondaryButton}
                            aria-pressed={isSelected}
                            onClick={(event) => {
                              event.stopPropagation();
                              handlePreviewToggle(player);
                            }}
                          >
                            {isSelected ? 'Hide Preview' : 'Preview'}
                          </button>

                          <button
                            type="button"
                            className={styles.editButton}
                            onClick={(event) => {
                              event.stopPropagation();
                              handleEditClick(player);
                            }}
                          >
                            Edit
                          </button>
                        </div>
                      </div>

                      <div style={identityRowStyle}>
                        <span style={identityBadgeStyle(isCanonicallyLinked)}>
                          {isCanonicallyLinked ? 'Canonical linked' : 'Local-only'}
                        </span>

                        {player.canonical_display_name ? (
                          <span style={identityTextStyle}>{player.canonical_display_name}</span>
                        ) : (
                          <span style={identityTextStyle}>No canonical player linked yet</span>
                        )}
                      </div>

                      <div className={styles.metaGrid}>
                        <span className={styles.metaItem}>
                          <strong>No.</strong> {player.squad_number ?? '—'}
                        </span>
                        <span className={styles.metaItem}>
                          <strong>Position</strong> {player.primary_position || '—'}
                        </span>
                        <span className={styles.metaItem}>
                          <strong>Visibility</strong> {player.is_public ? 'Public' : 'Private'}
                        </span>
                        <span className={styles.metaItem}>
                          <strong>Status</strong> {player.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>

                      <p className={styles.secondaryPositions}>
                        {formatLastSyncedAt(player.last_synced_at)}
                      </p>

                      {(player.secondary_positions?.length ?? 0) > 0 && (
                        <p className={styles.secondaryPositions}>
                          Secondary positions: {player.secondary_positions.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className={styles.playerCard}>
            <div className={styles.panelHeader}>
              <h3 className={styles.panelTitle}>Selected Player Preview</h3>

              <div className={styles.formActions}>
                {selectedPlayer && (
                  <span className={styles.badge}>{getPlayerLabel(selectedPlayer)}</span>
                )}

                {selectedPlayer && (
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={clearSelectedPlayerPreview}
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            <CompactPlayerPreview
              player={selectedPlayer}
              summary={selectedPlayerSummary}
              isLoading={selectedPlayerSummaryLoading}
              error={selectedPlayerSummaryError}
              canonicalPlayerId={selectedCanonicalPlayerId}
              onOpenReadPage={
                selectedCanonicalPlayerId && !selectedPlayerSummaryLoading
                  ? handleOpenSelectedPlayerReadPage
                  : null
              }
              emptyMessage="Select Preview on a player to load a compact deterministic summary at the point of action."
            />

            {selectedPlayer && (
              <div style={identityPanelStyle}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '12px',
                    flexWrap: 'wrap',
                  }}
                >
                  <h3
                    style={{
                      margin: 0,
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: '#ffffff',
                    }}
                  >
                    Canonical Alignment
                  </h3>

                  <span style={identityBadgeStyle(Boolean(selectedPlayer.is_linked_to_player))}>
                    {selectedPlayer.is_linked_to_player ? 'Linked' : 'Unlinked'}
                  </span>
                </div>

                <div style={identityMetaGridStyle}>
                  <span className={styles.metaItem}>
                    <strong>Club row</strong> {getPlayerLabel(selectedPlayer)}
                  </span>

                  <span className={styles.metaItem}>
                    <strong>Canonical ID</strong>{' '}
                    {selectedPlayer.canonical_player_id ??
                      selectedPlayer.player_id ??
                      '—'}
                  </span>

                  <span className={styles.metaItem}>
                    <strong>Canonical name</strong>{' '}
                    {selectedPlayer.canonical_display_name || '—'}
                  </span>

                  <span className={styles.metaItem}>
                    <strong>Canonical position</strong>{' '}
                    {selectedPlayer.canonical_primary_position || '—'}
                  </span>
                </div>

                {!canManageIdentity ? (
                  <div style={identityNoticeStyle}>
                    You can view alignment state here, but only authorised club reviewers can change canonical links.
                  </div>
                ) : (
                  <>
                    <div style={identityNoticeStyle}>
                      This phase uses an explicit canonical player ID input. No auto-match or heuristic suggestion flow is shown here.
                    </div>

                    {identityError && <div className={styles.error}>{identityError}</div>}
                    {identityMessage && <div className={styles.emptyState}>{identityMessage}</div>}

                    <div className={styles.formRow}>
                      <div className={styles.formGroup}>
                        <label className={styles.label} htmlFor="canonical_player_id">
                          Canonical Player ID
                        </label>
                        <input
                          id="canonical_player_id"
                          name="canonical_player_id"
                          type="number"
                          min="1"
                          className={styles.input}
                          value={canonicalPlayerIdInput}
                          onChange={(event) => setCanonicalPlayerIdInput(event.target.value)}
                          placeholder="Existing canonical Player ID"
                        />
                      </div>
                    </div>

                    <div style={identityActionsStyle}>
                      {!selectedPlayer.is_linked_to_player ? (
                        <button
                          type="button"
                          className={styles.primaryButton}
                          disabled={identityLoading}
                          onClick={handleLinkPlayer}
                        >
                          {identityLoading ? 'Linking...' : 'Link Canonical Player'}
                        </button>
                      ) : (
                        <>
                          <button
                            type="button"
                            className={styles.primaryButton}
                            disabled={identityLoading}
                            onClick={handleRelinkPlayer}
                          >
                            {identityLoading ? 'Updating...' : 'Relink'}
                          </button>

                          <button
                            type="button"
                            className={styles.secondaryButton}
                            disabled={identityLoading}
                            onClick={handleUnlinkPlayer}
                          >
                            {identityLoading ? 'Removing...' : 'Unlink'}
                          </button>
                        </>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </section>

        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>
              {editingPlayer ? 'Edit Player' : 'Add Player'}
            </h2>

            {editingPlayer && (
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={resetForm}
              >
                Cancel Edit
              </button>
            )}
          </div>

          <form className={styles.form} onSubmit={handleSubmit}>
            {formError && <div className={styles.error}>{formError}</div>}

            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="first_name">
                  First Name
                </label>
                <input
                  id="first_name"
                  name="first_name"
                  className={styles.input}
                  value={form.first_name}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="last_name">
                  Last Name
                </label>
                <input
                  id="last_name"
                  name="last_name"
                  className={styles.input}
                  value={form.last_name}
                  onChange={handleInputChange}
                  required
                />
              </div>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor="display_name">
                Display Name
              </label>
              <input
                id="display_name"
                name="display_name"
                className={styles.input}
                value={form.display_name}
                onChange={handleInputChange}
                placeholder="Optional nickname or preferred name"
              />
            </div>

            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="squad_number">
                  Squad Number
                </label>
                <input
                  id="squad_number"
                  name="squad_number"
                  type="number"
                  min="1"
                  max="99"
                  className={styles.input}
                  value={form.squad_number}
                  onChange={handleInputChange}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="primary_position">
                  Primary Position
                </label>
                <select
                  id="primary_position"
                  name="primary_position"
                  className={styles.select}
                  value={form.primary_position}
                  onChange={handleInputChange}
                >
                  <option value="">Select position</option>
                  {POSITION_OPTIONS.map((position) => (
                    <option key={position} value={position}>
                      {position}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor="secondary_positions">
                Secondary Positions
              </label>
              <input
                id="secondary_positions"
                name="secondary_positions"
                className={styles.input}
                value={form.secondary_positions}
                onChange={handleInputChange}
                placeholder="e.g. RB, RWB, CB"
              />
            </div>

            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="preferred_foot">
                  Preferred Foot
                </label>
                <select
                  id="preferred_foot"
                  name="preferred_foot"
                  className={styles.select}
                  value={form.preferred_foot}
                  onChange={handleInputChange}
                >
                  {FOOT_OPTIONS.map((foot) => (
                    <option key={foot.value} value={foot.value}>
                      {foot.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="date_of_birth">
                  Date of Birth
                </label>
                <input
                  id="date_of_birth"
                  name="date_of_birth"
                  type="date"
                  className={styles.input}
                  value={form.date_of_birth}
                  onChange={handleInputChange}
                />
              </div>
            </div>

            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor="height_cm">
                  Height (cm)
                </label>
                <input
                  id="height_cm"
                  name="height_cm"
                  type="number"
                  min="1"
                  className={styles.input}
                  value={form.height_cm}
                  onChange={handleInputChange}
                />
              </div>

              <div className={styles.formGroupCheckbox}>
                <label className={styles.checkboxLabel}>
                  <input
                    name="is_public"
                    type="checkbox"
                    checked={form.is_public}
                    onChange={handleInputChange}
                  />
                  Public player
                </label>

                {editingPlayer && (
                  <label className={styles.checkboxLabel}>
                    <input
                      name="is_active"
                      type="checkbox"
                      checked={form.is_active}
                      onChange={handleInputChange}
                    />
                    Active player
                  </label>
                )}
              </div>
            </div>

            <div className={styles.formActions}>
              <button
                type="submit"
                className={styles.primaryButton}
                disabled={saving}
              >
                {saving
                  ? editingPlayer
                    ? 'Saving...'
                    : 'Creating...'
                  : editingPlayer
                    ? 'Save Changes'
                    : 'Create Player'}
              </button>

              {editingPlayer && (
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={resetForm}
                  disabled={saving}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </section>
      </div>
    </div>
  );
};

export default ClubPlayersPage;
