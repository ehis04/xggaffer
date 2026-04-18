import React from 'react';
import type { LiveFootballLeagueSnapshotRow } from '../../../types/livefootball';

interface LeaguePreviewMiniTableProps {
  title: string;
  rows: LiveFootballLeagueSnapshotRow[];
}

const LeaguePreviewMiniTable: React.FC<LeaguePreviewMiniTableProps> = ({
  title,
  rows,
}) => {
  return (
    <div
      style={{
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '14px',
        padding: '0.9rem',
        background: 'rgba(255, 255, 255, 0.02)',
        minWidth: 0,
      }}
    >
      <h3
        style={{
          margin: 0,
          marginBottom: '0.75rem',
          fontSize: '0.98rem',
        }}
      >
        {title}
      </h3>

      {rows.length === 0 ? (
        <div
          style={{
            color: 'rgba(255, 255, 255, 0.55)',
            fontSize: '0.9rem',
          }}
        >
          No rows available.
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gap: '0.55rem',
          }}
        >
          {rows.map((row) => (
            <div
              key={`${title}-${row.team.id ?? row.team.name}-${row.position ?? 'na'}`}
              style={{
                display: 'grid',
                gridTemplateColumns: '40px minmax(0, 1fr) 44px',
                gap: '0.65rem',
                alignItems: 'center',
              }}
            >
              <div
                style={{
                  fontSize: '0.85rem',
                  color: 'rgba(255, 255, 255, 0.6)',
                }}
              >
                #{row.position ?? '-'}
              </div>

              <div
                style={{
                  minWidth: 0,
                }}
              >
                <div
                  style={{
                    fontWeight: 600,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {row.team.short_name || row.team.name}
                </div>
                <div
                  style={{
                    fontSize: '0.82rem',
                    color: 'rgba(255, 255, 255, 0.58)',
                  }}
                >
                  GD {row.goal_difference ?? '-'}
                </div>
              </div>

              <div
                style={{
                  textAlign: 'right',
                  fontWeight: 700,
                }}
              >
                {row.points ?? '-'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LeaguePreviewMiniTable;