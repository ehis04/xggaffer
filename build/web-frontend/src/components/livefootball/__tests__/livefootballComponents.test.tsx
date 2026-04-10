import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import FixturesPanel from '../FixturesPanel';
import LeagueTable from '../LeagueTable';
import TopScorersPanel from '../TopScorersPanel';
import TrendSection from '../home/TrendSection';

const competition = {
  id: 1,
  provider: 'football-data',
  external_id: 'pl',
  code: 'PL',
  name: 'Premier League',
  area_name: 'England',
  emblem_url: '',
  current_season_label: '2024/2025',
} as const;

describe('livefootball presentational components', () => {
  it('renders the league table', () => {
    render(
      <LeagueTable
        table={{
          competition,
          season_label: '2024/2025',
          snapshot_label: 'Latest',
          matchday: 28,
          rows: [
            {
              position: 1,
              team: {
                id: 10,
                external_id: 'arsenal',
                name: 'Arsenal',
                short_name: 'Arsenal',
                tla: 'ARS',
                emblem_url: '',
              },
              played: 28,
              won: 19,
              drawn: 4,
              lost: 5,
              goals_for: 61,
              goals_against: 24,
              goal_difference: 37,
              points: 61,
              form: 'WWDWW',
            },
          ],
        }}
      />
    );

    expect(screen.getByText('League Table')).toBeInTheDocument();
    expect(screen.getByText(/Premier League/i)).toBeInTheDocument();
    expect(screen.getByText('Arsenal')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Pts' })).toBeInTheDocument();
    expect(screen.getByText('61')).toBeInTheDocument();
  });

  it('renders previous and upcoming fixtures', () => {
    render(
      <FixturesPanel
        fixtures={{
          competition,
          season_label: '2024/2025',
          previous: [
            {
              id: 101,
              external_match_id: 'm101',
              season_label: '2024/2025',
              status: 'FINISHED',
              kickoff_at: '2026-03-15T15:00:00Z',
              matchday: 29,
              home_team: {
                id: 10,
                external_id: 'arsenal',
                name: 'Arsenal',
                short_name: 'Arsenal',
                tla: 'ARS',
                emblem_url: '',
              },
              away_team: {
                id: 11,
                external_id: 'chelsea',
                name: 'Chelsea',
                short_name: 'Chelsea',
                tla: 'CHE',
                emblem_url: '',
              },
              home_score: 2,
              away_score: 1,
            },
          ],
          next: [
            {
              id: 102,
              external_match_id: 'm102',
              season_label: '2024/2025',
              status: 'SCHEDULED',
              kickoff_at: '2026-03-22T15:00:00Z',
              matchday: 30,
              home_team: {
                id: 12,
                external_id: 'spurs',
                name: 'Tottenham Hotspur',
                short_name: 'Spurs',
                tla: 'TOT',
                emblem_url: '',
              },
              away_team: {
                id: 10,
                external_id: 'arsenal',
                name: 'Arsenal',
                short_name: 'Arsenal',
                tla: 'ARS',
                emblem_url: '',
              },
              home_score: null,
              away_score: null,
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Previous fixtures')).toBeInTheDocument();
    expect(screen.getByText('Upcoming fixtures')).toBeInTheDocument();
    expect(screen.getByText('Arsenal v Chelsea')).toBeInTheDocument();
    expect(screen.getByText('Spurs v Arsenal')).toBeInTheDocument();
    expect(screen.getByText('2 - 1')).toBeInTheDocument();
    expect(screen.getByText('Scheduled')).toBeInTheDocument();
  });

  it('renders top scorers', () => {
    render(
      <TopScorersPanel
        scorers={{
          competition,
          season_label: '2024/2025',
          count: 2,
          items: [
            {
              rank: 1,
              external_player_id: 'haaland',
              player_name: 'Erling Haaland',
              goals: 21,
              penalties: 3,
              team: {
                id: 20,
                external_id: 'man-city',
                name: 'Manchester City',
                short_name: 'Man City',
                tla: 'MCI',
                emblem_url: '',
              },
              canonical_player: {
                id: 501,
                display_name: 'Erling Haaland',
                first_name: 'Erling',
                last_name: 'Haaland',
              },
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Top scorers')).toBeInTheDocument();
    expect(screen.getByText('Erling Haaland')).toBeInTheDocument();
    expect(screen.getByText('Man City')).toBeInTheDocument();
    expect(screen.getByText('21')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders top performing team cards with team, league, and form', () => {
    render(
      <MemoryRouter>
        <TrendSection
          title="Top performing teams"
          subtitle="Global cross-league team form highlights."
          actionLabel="View clubs"
          actionTo="/livefootball/clubs"
          updatedAt={null}
          variant="team"
          emptyMessage="No top performing team cards are available right now."
          items={[
            {
              rank: 1,
              team: {
                id: 10,
                name: 'Arsenal',
                short_name: 'Arsenal',
                crest_url: '',
              },
              competition: {
                id: 1,
                code: 'PL',
                name: 'Premier League',
                country: 'England',
                emblem_url: '',
              },
              summary: '2.33 points per game and 2.00 goals per game.',
              metric_label: 'PPG',
              metric_value: '2.33',
              form_label: 'W-W-W-D-W',
              cta: {
                label: 'View club',
                path: '/livefootball/clubs',
                query: { competition: 'PL', teamId: 10 },
              },
            },
          ]}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('Arsenal')).toBeInTheDocument();
    expect(screen.getByText('Premier League')).toBeInTheDocument();
    expect(screen.getByLabelText('Recent form W-W-W-D-W')).toBeInTheDocument();
    expect(screen.getAllByText('W')).toHaveLength(4);
    expect(screen.getByText('D')).toBeInTheDocument();
    expect(screen.getByText('2.33 points per game and 2.00 goals per game.')).toBeInTheDocument();
  });
});