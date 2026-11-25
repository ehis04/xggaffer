import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import FixturesPanel from '../FixturesPanel';
import LeagueTable from '../LeagueTable';
import TopScorersPanel from '../TopScorersPanel';
import TrendSection from '../home/TrendSection';
import { predictMatch } from '../../../services/api/predictionsApi';

vi.mock('../../../services/api/predictionsApi', () => ({
  predictMatch: vi.fn(),
}));

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

const baseFixtures = {
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
      home_team: { id: 10, external_id: 'arsenal', name: 'Arsenal', short_name: 'Arsenal', tla: 'ARS', emblem_url: '' },
      away_team: { id: 11, external_id: 'chelsea', name: 'Chelsea', short_name: 'Chelsea', tla: 'CHE', emblem_url: '' },
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
      home_team: { id: 12, external_id: 'spurs', name: 'Tottenham Hotspur', short_name: 'Spurs', tla: 'TOT', emblem_url: '' },
      away_team: { id: 10, external_id: 'arsenal', name: 'Arsenal', short_name: 'Arsenal', tla: 'ARS', emblem_url: '' },
      home_score: null,
      away_score: null,
    },
  ],
};

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

  it('renders previous and upcoming fixtures', async () => {
    vi.mocked(predictMatch).mockResolvedValue({
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      league: 'EPL',
      season: '2024',
      prediction: 'Home',
      probabilities: { home: 0.5, draw: 0.25, away: 0.25 },
      top_factors: [],
      metrics: { accuracy: 0.53, brier_score: null },
      model_type: 'logistic',
      version: '1',
    });

    render(<FixturesPanel fixtures={baseFixtures} />);

    expect(screen.getByText('Previous fixtures')).toBeInTheDocument();
    expect(screen.getByText('Upcoming fixtures')).toBeInTheDocument();
    expect(screen.getByText('Arsenal v Chelsea')).toBeInTheDocument();
    expect(screen.getByText('Spurs v Arsenal')).toBeInTheDocument();
    expect(screen.getByText('2 - 1')).toBeInTheDocument();
    expect(screen.getByText('Scheduled')).toBeInTheDocument();
    await waitFor(() => expect(predictMatch).toHaveBeenCalled());
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
            },
            {
              rank: 2,
              external_player_id: 'salah',
              player_name: 'Mohamed Salah',
              goals: 18,
              penalties: 4,
              team: {
                id: 30,
                external_id: 'liverpool',
                name: 'Liverpool',
                short_name: 'Liverpool',
                tla: 'LIV',
                emblem_url: '',
              },
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Top scorers')).toBeInTheDocument();
    expect(screen.getByText('Erling Haaland')).toBeInTheDocument();
    expect(screen.getByText('Mohamed Salah')).toBeInTheDocument();
  });

  it('renders top performing team cards with team, league, and form', () => {
    render(
      <MemoryRouter>
        <TrendSection
          title="Top Performing Teams"
          subtitle="Current season form"
          actionLabel="View all"
          actionTo="/livefootball"
          emptyMessage="No data"
          variant="team"
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

describe('FixturesPanel prediction chips', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders probability chips after fixtures load', async () => {
    vi.mocked(predictMatch).mockResolvedValue({
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      league: 'EPL',
      season: '2024',
      prediction: 'Home',
      probabilities: { home: 0.61, draw: 0.23, away: 0.16 },
      top_factors: [],
      metrics: { accuracy: 0.53, brier_score: null },
      model_type: 'logistic',
      version: '1',
    });

    render(<FixturesPanel fixtures={baseFixtures} />);

    await waitFor(() => {
      expect(screen.getAllByText('61%').length).toBeGreaterThan(0);
    });
  });

  it('calls predictMatch with league derived from competition code', async () => {
    vi.mocked(predictMatch).mockResolvedValue({
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      league: 'EPL',
      season: '2024',
      prediction: 'Home',
      probabilities: { home: 0.5, draw: 0.25, away: 0.25 },
      top_factors: [],
      metrics: { accuracy: 0.53, brier_score: null },
      model_type: 'logistic',
      version: '1',
    });

    render(<FixturesPanel fixtures={baseFixtures} />);

    await waitFor(() => {
      expect(predictMatch).toHaveBeenCalledWith(
        expect.objectContaining({ league: 'EPL', season: '2024' })
      );
    });
  });

  it('skips predictMatch for unsupported competition codes', async () => {
    const uclFixtures = {
      ...baseFixtures,
      competition: { ...baseFixtures.competition, code: 'UCL' },
    };

    render(<FixturesPanel fixtures={uclFixtures} />);

    await waitFor(() => {
      expect(predictMatch).not.toHaveBeenCalled();
    });
  });

  it('parses season year correctly from season_label', async () => {
    vi.mocked(predictMatch).mockResolvedValue({
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      league: 'EPL',
      season: '2023',
      prediction: 'Home',
      probabilities: { home: 0.5, draw: 0.25, away: 0.25 },
      top_factors: [],
      metrics: { accuracy: 0.53, brier_score: null },
      model_type: 'logistic',
      version: '1',
    });

    const fixtures2023 = {
      ...baseFixtures,
      season_label: '2023/2024',
      previous: [{ ...baseFixtures.previous[0], season_label: '2023/2024' }],
      next: [{ ...baseFixtures.next[0], season_label: '2023/2024' }],
    };

    render(<FixturesPanel fixtures={fixtures2023} />);

    await waitFor(() => {
      expect(predictMatch).toHaveBeenCalledWith(
        expect.objectContaining({ season: '2023' })
      );
    });
  });

  it('shows dash when prediction fails', async () => {
    vi.mocked(predictMatch).mockRejectedValue(new Error('unavailable'));

    render(<FixturesPanel fixtures={baseFixtures} />);

    await waitFor(() => {
      expect(screen.getAllByText('—').length).toBeGreaterThan(0);
    });
  });

  it('does not throw when one prediction fails and another succeeds', async () => {
    vi.mocked(predictMatch)
      .mockResolvedValueOnce({
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        league: 'EPL',
        season: '2024',
        prediction: 'Home',
        probabilities: { home: 0.55, draw: 0.25, away: 0.20 },
        top_factors: [],
        metrics: { accuracy: 0.53, brier_score: null },
        model_type: 'logistic',
        version: '1',
      })
      .mockRejectedValueOnce(new Error('unavailable'));

    render(<FixturesPanel fixtures={baseFixtures} />);

    await waitFor(() => {
      expect(screen.getByText('Arsenal v Chelsea')).toBeInTheDocument();
      expect(screen.getByText('Spurs v Arsenal')).toBeInTheDocument();
    });
  });

  it('preserves existing fixture content after predictions load', async () => {
    vi.mocked(predictMatch).mockResolvedValue({
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      league: 'EPL',
      season: '2024',
      prediction: 'Home',
      probabilities: { home: 0.61, draw: 0.23, away: 0.16 },
      top_factors: [],
      metrics: { accuracy: 0.53, brier_score: null },
      model_type: 'logistic',
      version: '1',
    });

    render(<FixturesPanel fixtures={baseFixtures} />);

    await waitFor(() => {
      expect(screen.getByText('Arsenal v Chelsea')).toBeInTheDocument();
      expect(screen.getByText('Spurs v Arsenal')).toBeInTheDocument();
      expect(screen.getByText('2 - 1')).toBeInTheDocument();
      expect(screen.getByText('Finished')).toBeInTheDocument();
    });

    expect(predictMatch).toHaveBeenCalledTimes(2);
  });

  it('calls predictMatch once per fixture using home_team.name', async () => {
    vi.mocked(predictMatch).mockResolvedValue({
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      league: 'EPL',
      season: '2024',
      prediction: 'Home',
      probabilities: { home: 0.5, draw: 0.25, away: 0.25 },
      top_factors: [],
      metrics: { accuracy: 0.53, brier_score: null },
      model_type: 'logistic',
      version: '1',
    });

    render(<FixturesPanel fixtures={baseFixtures} />);

    await waitFor(() => {
      expect(predictMatch).toHaveBeenCalledTimes(2);
    });

    expect(predictMatch).toHaveBeenCalledWith(
      expect.objectContaining({ home_team: 'Arsenal', away_team: 'Chelsea' })
    );
    expect(predictMatch).toHaveBeenCalledWith(
      expect.objectContaining({ home_team: 'Tottenham Hotspur', away_team: 'Arsenal' })
    );
  });
});
