import React from 'react';
import type { ClubPlayer } from '../../types/clubPlayers';
import type { PlayerSeasonSummary } from '../../types/playerdata';

interface CompactPlayerPreviewProps {
  player: ClubPlayer | null;
  summary?: PlayerSeasonSummary | null;
  isLoading?: boolean;
  error?: string | null;
  canonicalPlayerId?: number | null;
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

const buildContextLine = (summary?: PlayerSeasonSummary | null): string | null => {
  if (!summary) {
    return null;
  }

  // Only show competition, not provider or season
  const competition =
    getFirstPresentValue(summary, [
      ['context', 'competition_name'],
      ['context', 'competition_code'],
      ['competition_name'],
      ['competition_code'],
    ]) || null;

  return competition;
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
  onOpenReadPage = null,
  emptyMessage = 'Select a player to view their stats.',
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
      {!canonicalPlayerId ? (
        <div
          style={{
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            padding: '0.9rem',
            opacity: 0.72,
          }}
        >
          No stats data available for this player yet.
        </div>
      ) : isLoading ? (
        <div
          style={{
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            padding: '0.9rem',
          }}
        >
          Loading…
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
          {contextLine && (
            <div style={{ opacity: 0.82 }}>{contextLine}</div>
          )}

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
            <div>No season stats available for this player yet.</div>
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
                View full profile
              </button>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default CompactPlayerPreview;