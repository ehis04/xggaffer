import React from 'react';
import type { ClubPlayer } from '../../types/clubPlayers';
import type { PlayerSeasonSummary } from '../../types/playerdata';

type CanonicalPlayerIdSource =
  | 'player_id'
  | 'canonical_player_id'
  | 'linked_player_id'
  | string;

interface CompactPlayerPreviewProps {
  player: ClubPlayer | null;
  summary?: PlayerSeasonSummary | null;
  isLoading?: boolean;
  error?: string | null;
  canonicalPlayerId?: number | null;
  canonicalPlayerIdSource?: CanonicalPlayerIdSource | null;
  onOpenReadPage?: (() => void) | null;
  emptyMessage?: string;
  className?: string;
}

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const getNestedValue = (source: unknown, path: string[]): unknown => {
  let current: unknown = source;

  for (const key of path) {
    if (!isRecord(current) || !(key in current)) {
      return undefined;
    }

    current = current[key];
  }

  return current;
};

const getFirstPresentValue = (source: unknown, paths: string[][]): string | null => {
  for (const path of paths) {
    const value = getNestedValue(source, path);

    if (typeof value === 'number' && Number.isFinite(value)) {
      return String(value);
    }

    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return null;
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

const getPlayerLabel = (player: ClubPlayer): string => {
  if (player.display_name?.trim()) {
    return player.display_name.trim();
  }

  if (player.full_name?.trim()) {
    return player.full_name.trim();
  }

  return `${player.first_name} ${player.last_name}`.trim() || `Player #${player.id}`;
};

const buildContextLine = (summary?: PlayerSeasonSummary | null): string | null => {
  if (!summary) {
    return null;
  }

  const provider =
    getFirstPresentValue(summary, [
      ['context', 'provider'],
      ['provider_coverage', 'provider'],
    ]) || null;

  const season =
    getFirstPresentValue(summary, [
      ['context', 'season'],
      ['season'],
    ]) || null;

  const competition =
    getFirstPresentValue(summary, [
      ['context', 'competition_name'],
      ['context', 'competition_code'],
      ['competition_name'],
      ['competition_code'],
    ]) || null;

  const bits = [provider, season, competition].filter(Boolean);

  return bits.length > 0 ? bits.join(' · ') : null;
};


const buildMetricItems = (summary?: PlayerSeasonSummary | null) => {
  if (!summary?.metrics) return [];
  return summary.metrics
    .filter((m) => m.is_available !== false && m.value != null)
    .map((m) => ({
      label: m.label,
      value: m.formatted_value?.trim() || String(m.value),
    }));
};

const CompactPlayerPreview: React.FC<CompactPlayerPreviewProps> = ({
  player,
  summary = null,
  isLoading = false,
  error = null,
  canonicalPlayerId = null,
  canonicalPlayerIdSource = null,
  onOpenReadPage = null,
  emptyMessage = 'Select a player to preview useful summary information.',
  className,
}) => {
  if (!player) {
    return <div className={className}>{emptyMessage}</div>;
  }

  const contextLine = buildContextLine(summary);
  const metricItems = buildMetricItems(summary);

  return (
    <div
      className={className}
      style={{
        display: 'grid',
        gap: '1rem',
      }}
    >
      <div
        style={{
          display: 'grid',
          gap: '0.5rem',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: '0.75rem',
            flexWrap: 'wrap',
            alignItems: 'center',
          }}
        >
          <div>
            <h4 style={{ margin: 0 }}>{getPlayerLabel(player)}</h4>
            <p style={{ margin: '0.35rem 0 0 0', opacity: 0.82 }}>
              {player.primary_position || 'Position not set'}
              {player.squad_number ? ` · #${player.squad_number}` : ''}
              {player.is_public ? ' · Public' : ' · Private'}
              {player.is_active ? ' · Active' : ' · Inactive'}
            </p>
          </div>

          <span
            style={{
              padding: '0.35rem 0.65rem',
              borderRadius: '999px',
              border: '1px solid rgba(255,255,255,0.12)',
              fontSize: '0.85rem',
              whiteSpace: 'nowrap',
            }}
          >
            {player.has_provider_identity ? 'Provider-linked' : 'Local-only'}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gap: '0.45rem',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          }}
        >
          <span>
            <strong>Canonical ID</strong> {canonicalPlayerId ?? '—'}
          </span>
          <span>
            <strong>ID source</strong> {canonicalPlayerIdSource ?? 'Unavailable'}
          </span>
          <span>
            <strong>Providers</strong>{' '}
            {player.provider_sources?.length ? player.provider_sources.join(', ') : '—'}
          </span>
          <span>
            <strong>Sync</strong> {formatLastSyncedAt(player.last_synced_at)}
          </span>
        </div>

        {(player.secondary_positions?.length ?? 0) > 0 ? (
          <div>
            <strong>Secondary positions</strong> {player.secondary_positions.join(', ')}
          </div>
        ) : null}
      </div>

      {!canonicalPlayerId ? (
        <div
          style={{
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            padding: '0.9rem',
          }}
        >
          {player.has_provider_identity
            ? 'This player is linked, but this row does not expose a canonical player ID yet, so a deterministic preview cannot be loaded.'
            : 'This player is local-only, so deterministic summary data is not available yet.'}
        </div>
      ) : isLoading ? (
        <div
          style={{
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            padding: '0.9rem',
          }}
        >
          Loading compact preview…
        </div>
      ) : error ? (
        <div
          role="alert"
          style={{
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            padding: '0.9rem',
          }}
        >
          {error}
        </div>
      ) : (
        <div
          style={{
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            padding: '0.9rem',
            display: 'grid',
            gap: '0.85rem',
          }}
        >
          <div>
            <strong>Deterministic season preview</strong>
            <div style={{ marginTop: '0.35rem', opacity: 0.82 }}>
              {contextLine || 'Season context unavailable'}
            </div>
          </div>

          {metricItems.length > 0 ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
                gap: '0.75rem',
              }}
            >
              {metricItems.map((item) => (
                <div
                  key={item.label}
                  style={{
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: '10px',
                    padding: '0.7rem',
                  }}
                >
                  <div style={{ fontSize: '0.82rem', opacity: 0.72 }}>{item.label}</div>
                  <div style={{ fontWeight: 700, marginTop: '0.2rem' }}>{item.value}</div>
                </div>
              ))}
            </div>
          ) : (
            <div>No compact season metrics are available for this player yet.</div>
          )}

          {onOpenReadPage ? (
            <div>
              <button
                type="button"
                onClick={onOpenReadPage}
                style={{
                  padding: '0.7rem 1rem',
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.12)',
                  background: 'transparent',
                  cursor: 'pointer',
                }}
              >
                Open Internal Read Page
              </button>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default CompactPlayerPreview;