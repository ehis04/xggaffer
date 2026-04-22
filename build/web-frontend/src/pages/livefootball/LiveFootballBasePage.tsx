import React, { useEffect, useState } from 'react';
import { getLiveFootballOverview } from '../../services/api/livefootballApi';
import type { LiveFootballOverview } from '../../types/livefootball';
import type { ApiEnvelope } from '../../common/types/response';
import { FreshnessBadge } from '../../common/components/FreshnessBadge';

import LiveFootballHeroHeader from '../../components/livefootball/home/LiveFootballHeroHeader';
import RotatingLeaguePreviewCard from '../../components/livefootball/home/RotatingLeaguePreviewCard';
import AllTimeStreaksPreview from '../../components/livefootball/home/AllTimeStreaksPreview';
import TrendSection from '../../components/livefootball/home/TrendSection';
import LeagueMatchesSection from '../../components/livefootball/home/LeagueMatchesSection';
import FirstVsLastLeagueSection from '../../components/livefootball/home/FirstVsLastLeagueSection';
import OverviewDataState from '../../components/livefootball/home/OverviewDataState';

import styles from './css/LiveFootballBasePage.module.css';

const LiveFootballBasePage: React.FC = () => {
  const [envelope, setEnvelope] = useState<ApiEnvelope<LiveFootballOverview> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadOverview = async (): Promise<void> => {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const result = await getLiveFootballOverview();

        if (!isMounted) {
          return;
        }

        setEnvelope(result);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        console.error('Failed to load live football overview', error);
        setErrorMessage('Could not load the Live Football homepage right now.');
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadOverview();

    return () => {
      isMounted = false;
    };
  }, []);

  const overview = envelope?.data ?? null;

  return (
    <main className={styles.page}>
      <LiveFootballHeroHeader generatedAt={overview?.generated_at ?? null} />

      {isLoading ? (
        <OverviewDataState
          title="Loading Live Football overview"
          description="Pulling the homepage data from the aggregated overview endpoint."
        />
      ) : null}

      {!isLoading && errorMessage ? (
        <OverviewDataState
          title="Live Football overview unavailable"
          description={errorMessage}
          variant="error"
        />
      ) : null}

      {!isLoading && !errorMessage && envelope && !overview ? (
        <OverviewDataState
          title="Live Football overview unavailable"
          description="Data is temporarily unavailable. Please try again shortly."
          variant="error"
        />
      ) : null}

      {!isLoading && !errorMessage && overview ? (
        <>
          <div style={{ padding: '0 1rem 0.5rem' }}>
            <FreshnessBadge freshness={envelope?.freshness} />
          </div>

          <RotatingLeaguePreviewCard cards={overview.league_snapshot} />

          <AllTimeStreaksPreview data={overview.all_time_streaks} />

          <TrendSection
            title="Top performing teams"
            subtitle="Global cross-league team form highlights."
            actionLabel="View clubs"
            actionTo="/livefootball/clubs"
            updatedAt={overview.top_performing_teams.updated_at}
            items={overview.top_performing_teams.items}
            variant="team"
            emptyMessage="No top performing team cards are available right now."
          />

          <TrendSection
            title="Top performing scorers"
            subtitle="Cross-league scoring leaders and hot streaks."
            actionLabel="View players"
            actionTo="/livefootball/players?trend=top-performing-scorers"
            updatedAt={overview.top_performing_scorers.updated_at}
            items={overview.top_performing_scorers.items}
            variant="player"
            emptyMessage="No top performing scorer cards are available right now."
          />

          <TrendSection
            title="Latest hat-tricks"
            subtitle="Recent hat-trick performances across the tracked leagues."
            actionLabel="View players"
            actionTo="/livefootball/players?trend=latest-hat-tricks"
            updatedAt={overview.latest_hat_tricks.updated_at}
            items={overview.latest_hat_tricks.items}
            variant="player"
            emptyMessage="No recent hat-trick cards are available right now."
          />

          <TrendSection
            title="Strikers with a lull"
            subtitle="Deterministic drought-style highlights across the tracked leagues."
            actionLabel="View players"
            actionTo="/livefootball/players?trend=strikers-with-a-lull"
            updatedAt={overview.strikers_with_a_lull.updated_at}
            items={overview.strikers_with_a_lull.items}
            variant="player"
            emptyMessage="No striker lull cards are available right now."
          />

          <LeagueMatchesSection
            title="Recent matches by league"
            subtitle="Five most recent league matches for each tracked competition."
            actionLabel="View matches"
            actionTo="/livefootball/matches"
            groups={overview.recent_matches_by_league}
            tab="recent"
            emptyMessage="No recent match groups are available right now."
          />

          <LeagueMatchesSection
            title="Upcoming matches by league"
            subtitle="The next five league matches for each tracked competition."
            actionLabel="View matches"
            actionTo="/livefootball/matches"
            groups={overview.upcoming_matches_by_league}
            tab="upcoming"
            emptyMessage="No upcoming match groups are available right now."
          />

          <FirstVsLastLeagueSection
            title="First vs last by league"
            subtitle="Paired comparison blocks for the top and bottom clubs in each league."
            actionLabel="View leagues"
            actionTo="/livefootball/leagues"
            items={overview.first_vs_last_by_league}
            emptyMessage="No first-versus-last league comparisons are available right now."
          />
        </>
      ) : null}
    </main>
  );
};

export default LiveFootballBasePage;