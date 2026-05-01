import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sidebar } from '../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../components/Social/SocialUserButtons';
import { getLiveFootballOverview } from '../../services/api/livefootballApi';
import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import { queryKeys } from '../../common/query/queryKeys';
import { STALE_TIME_SHORT } from '../../common/query/queryClient';
import { usePageTiming } from '../../common/hooks/usePageTiming';

import LiveFootballHeroHeader from '../../components/livefootball/home/LiveFootballHeroHeader';
import RotatingLeaguePreviewCard from '../../components/livefootball/home/RotatingLeaguePreviewCard';
import AllTimeStreaksPreview from '../../components/livefootball/home/AllTimeStreaksPreview';
import TrendSection from '../../components/livefootball/home/TrendSection';
import LeagueMatchesSection from '../../components/livefootball/home/LeagueMatchesSection';
import FirstVsLastLeagueSection from '../../components/livefootball/home/FirstVsLastLeagueSection';
import OverviewDataState from '../../components/livefootball/home/OverviewDataState';

import styles from './css/LiveFootballBasePage.module.css';

const LiveFootballBasePage: React.FC = () => {
  const { markDataReceived } = usePageTiming('LiveFootballBasePage');

  const { data: envelope, isPending, isError } = useQuery({
    queryKey: queryKeys.livefootball.overview(),
    queryFn: getLiveFootballOverview,
    staleTime: STALE_TIME_SHORT,
  });

  useEffect(() => {
    if (envelope) markDataReceived();
  }, [envelope]);

  const overview = envelope?.data ?? null;

  return (
    <div className={styles['lfb-root']}>
      <div className={styles['lfb-sidebar-section']}>
        <Sidebar />
      </div>

      <div className={styles['lfb-main']}>


        <header className={styles['lfb-header']}>
          <div className={styles['lfb-header-left']}>Live Football</div>
          <div className={styles['lfb-header-mid']} />
          <div className={styles['lfb-header-right']}>
            <SocialUserButtons />
          </div>
        </header>

        <main className={styles['lfb-content']}>
          <LiveFootballHeroHeader generatedAt={overview?.generated_at ?? null} />

          {isPending && (
            <OverviewDataState
              title="Loading Live Football overview"
              description="Live Football Data is Loading."
            />
          )}

          {!isPending && isError && (
            <OverviewDataState
              title="Live Football overview unavailable"
              description="Could not load the Live Football homepage right now."
              variant="error"
            />
          )}

          {!isPending && !isError && envelope && !overview && (
            <OverviewDataState
              title="Live Football overview unavailable"
              description="Data is temporarily unavailable. Please try again shortly."
              variant="error"
            />
          )}

          {!isPending && !isError && overview && (
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
              />

              <TrendSection
                title="Top performing scorers"
                subtitle="Cross-league scoring leaders and hot streaks."
                actionLabel="View players"
                actionTo="/livefootball/players?trend=top-performing-scorers"
                updatedAt={overview.top_performing_scorers.updated_at}
                items={overview.top_performing_scorers.items}
                variant="player"
              />

              <TrendSection
                title="Latest hat-tricks"
                subtitle="Recent hat-trick performances across the tracked leagues."
                actionLabel="View players"
                actionTo="/livefootball/players?trend=latest-hat-tricks"
                updatedAt={overview.latest_hat_tricks.updated_at}
                items={overview.latest_hat_tricks.items}
                variant="player"
              />

              <TrendSection
                title="Strikers with a lull"
                subtitle="Deterministic drought-style highlights across the tracked leagues."
                actionLabel="View players"
                actionTo="/livefootball/players?trend=strikers-with-a-lull"
                updatedAt={overview.strikers_with_a_lull.updated_at}
                items={overview.strikers_with_a_lull.items}
                variant="player"
              />

              <LeagueMatchesSection
                title="Recent matches by league"
                subtitle="Five most recent league matches for each tracked competition."
                actionLabel="View matches"
                actionTo="/livefootball/matches"
                groups={overview.recent_matches_by_league}
                tab="recent"
              />

              <LeagueMatchesSection
                title="Upcoming matches by league"
                subtitle="The next five league matches for each tracked competition."
                actionLabel="View matches"
                actionTo="/livefootball/matches"
                groups={overview.upcoming_matches_by_league}
                tab="upcoming"
              />

              <FirstVsLastLeagueSection
                title="First vs last by league"
                subtitle="Paired comparison blocks for the top and bottom clubs in each league."
                actionLabel="View leagues"
                actionTo="/livefootball/leagues"
                items={overview.first_vs_last_by_league}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
};

export default LiveFootballBasePage;
