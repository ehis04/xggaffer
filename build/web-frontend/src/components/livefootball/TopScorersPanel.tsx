import React from 'react';
import type { CompetitionTopScorersResponse } from '../../types/livefootball';

const getPlayerLabel = (item: CompetitionTopScorersResponse['items'][number]): string => {
  const canonicalDisplayName = item.canonical_player?.display_name?.trim();
  if (canonicalDisplayName) {
    return canonicalDisplayName;
  }

  const canonicalFirst = item.canonical_player?.first_name?.trim() ?? '';
  const canonicalLast = item.canonical_player?.last_name?.trim() ?? '';
  const canonicalJoined = `${canonicalFirst} ${canonicalLast}`.trim();

  if (canonicalJoined) {
    return canonicalJoined;
  }

  const rawName = item.player_name?.trim();
  return rawName || 'Unknown player';
};

const getTeamLabel = (item: CompetitionTopScorersResponse['items'][number]): string => {
  const shortName = item.team?.short_name?.trim();
  if (shortName) {
    return shortName;
  }

  const tla = item.team?.tla?.trim();
  if (tla) {
    return tla;
  }

  const name = item.team?.name?.trim();
  return name || 'Unknown team';
};

export interface TopScorersPanelProps {
  scorers: CompetitionTopScorersResponse | null;
  isLoading?: boolean;
  error?: string | null;
  title?: string;
  emptyMessage?: string;
  className?: string;
  maxItems?: number;
  showPenalties?: boolean;
}

const TopScorersPanel: React.FC<TopScorersPanelProps> = ({
  scorers,
  isLoading = false,
  error = null,
  title = 'Top scorers',
  emptyMessage = 'No scorer data is available for this competition yet.',
  className,
  maxItems,
  showPenalties = true,
}) => {
  if (isLoading) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div>Loading scorers…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div role="alert">{error}</div>
      </section>
    );
  }

  if (!scorers || scorers.items.length === 0) {
    return (
      <section className={className}>
        <h2>{title}</h2>
        <div>{emptyMessage}</div>
      </section>
    );
  }

  const items =
    typeof maxItems === 'number' && maxItems > 0
      ? scorers.items.slice(0, maxItems)
      : scorers.items;

  return (
    <section className={className}>
      <div style={{ marginBottom: '1rem' }}>
        <h2>{title}</h2>
        <p>
          {scorers.competition.name}
          {scorers.competition.area_name ? ` · ${scorers.competition.area_name}` : ''}
          {scorers.season_label ? ` · ${scorers.season_label}` : ''}
        </p>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Player</th>
              <th scope="col">Team</th>
              <th scope="col">Goals</th>
              {showPenalties ? <th scope="col">Pens</th> : null}
            </tr>
          </thead>

          <tbody>
            {items.map((item) => (
              <tr
                key={`${item.rank}-${item.external_player_id || item.canonical_player?.id || item.player_name}`}
              >
                <td>{item.rank}</td>
                <td>
                  <div>
                    <strong>{getPlayerLabel(item)}</strong>
                  </div>
                  {item.player_name?.trim() &&
                  item.player_name.trim() !== getPlayerLabel(item) ? (
                    <div>
                      <small>{item.player_name}</small>
                    </div>
                  ) : null}
                </td>
                <td>{getTeamLabel(item)}</td>
                <td>
                  <strong>{item.goals}</strong>
                </td>
                {showPenalties ? <td>{item.penalties ?? '—'}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default TopScorersPanel;